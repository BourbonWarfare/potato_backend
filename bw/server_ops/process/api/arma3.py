import logging
import psutil
from collections.abc import Sequence
from bw.models.process import Process
from bw.server_ops.process.status import Arma3ServerStatus, Arma3HeadlessClientStatus
from bw.server_ops.process.state import State as ProcessState
from bw.error import NoProcessWithNameAndNamespace
from bw.server_ops.process.process import ProcessStore
from bw.server_ops.arma.server import Server
from bw.state import State
from bw.web_event.arma_ops import ServerStartEvent, ServerStopEvent, ServerRestartEvent

NAMESPACE: str = 'arma3'
logger = logging.getLogger('bw.server_ops.process')


class Arma3Api:
    def create_processes_for_server(self, state: State, server: Server) -> tuple[Process, ...]:
        server_name = server.server_name()
        headless_clients = [f'{server_name}:hc_{idx}' for idx in range(0, server.headless_client_count())]
        server_process = ProcessStore().create_managed_process(state, NAMESPACE, server_name)
        headless_client_processes = []
        for headless_client in headless_clients:
            headless_client_processes.append(
                ProcessStore().create_managed_process_from_parent(state, NAMESPACE, headless_client, server_process)
            )
        return (server_process, *headless_client_processes)

    def prune_server_processes(self, state: State, server: Server, timeout: int = 15):
        try:
            processes = ProcessStore().get_process_and_children_by_namespace(state, NAMESPACE, server.server_name())
        except NoProcessWithNameAndNamespace as err:
            logger.warning(f'Trying to prune server processes for a non-registered server: {err}')
            raise

        headless_clients: tuple[Process, ...] = processes[1:]
        if len(headless_clients) <= server.headless_client_count():
            return

        to_delete = len(headless_clients) - server.headless_client_count()
        logger.info(f'Found {to_delete} (out of {len(headless_clients)} spawned) headless clients to kill')

        headless_clients_to_delete = headless_clients[-to_delete:]
        for idx, headless_client in enumerate(headless_clients_to_delete):
            logger.info(f'Killing headless client {idx + 1}/{len(headless_clients_to_delete)}')
            try:
                with ProcessStore().manage_process(
                    state, headless_client, state_on_success=ProcessState.DELETED
                ) as process_manager:
                    process_manager.update_state(ProcessState.DELETING)
                    subprocess = headless_client.into_process()
                    subprocess.kill()
                    subprocess.wait(timeout=timeout)

                    headless_client.parent = None
                    headless_client.pid = None
                    process_manager.update_status(subprocess.status())
            except TimeoutError:
                logger.warning('Failed to kill headless client due to timeout')

        for headless_client in [process for process in headless_clients_to_delete if process.state == ProcessState.DELETED]:
            ProcessStore().delete_process(state, headless_client)

        failed_deletions = [process for process in headless_clients_to_delete if process.state != ProcessState.DELETED]
        if failed_deletions:
            logger.warning(f'Failed to delete {len(failed_deletions)} headless clients from server!')

    def start_server(self, state: State, server: Server) -> Arma3ServerStatus:
        def start(processes: Sequence[Process]) -> Arma3ServerStatus:
            all_processes: list[psutil.Popen] = []
            try:
                logger.info('Starting server')
                with ProcessStore().manage_process(state, processes[0]) as process_manager:
                    process_manager.update_state(ProcessState.STARTING)
                    subprocess = psutil.Popen(server.server_launch_options())
                    processes[0].pid = subprocess.pid
                    process_manager.update_status(subprocess.status())
                    all_processes.append(subprocess)
            except OSError as err:
                logging.warning(f'Failed to start server {server.server_name()}: {err}')
                return Arma3ServerStatus(
                    running=False,
                    headless_clients=[Arma3HeadlessClientStatus(running=False)] * 3,
                )

            try:
                for idx, process in enumerate(processes[1:]):
                    logger.info(f'Starting headless client {idx + 1}/{server.headless_client_count()}')
                    with ProcessStore().manage_process(state, process) as process_manager:
                        process_manager.update_state(ProcessState.STARTING)
                        subprocess = psutil.Popen(server.headless_launch_options())

                        process.pid = subprocess.pid
                        process_manager.update_status(subprocess.status())
                        all_processes.append(subprocess)
            except OSError as err:
                logger.warning(f'Failed to start headless client {idx} (aborting): {err}')

            headless_client_statuses = [Arma3HeadlessClientStatus(running=process.is_running()) for process in all_processes[1:]]
            if len(headless_client_statuses) < server.headless_client_count():
                needed = server.headless_client_count() - len(headless_client_statuses)
                headless_client_statuses.extend([Arma3HeadlessClientStatus(running=False)] * needed)

            response = Arma3ServerStatus(
                running=all_processes[0].is_running(),
                headless_clients=headless_client_statuses,
            )
            return response

        try:
            self.prune_server_processes(state, server)
        except NoProcessWithNameAndNamespace:
            pass

        try:
            processes = ProcessStore().get_process_and_children_by_namespace(state, NAMESPACE, server.server_name())
        except NoProcessWithNameAndNamespace:
            processes = self.create_processes_for_server(state, server)

        response = start(processes)
        State.broker.publish(ServerStartEvent(server=server.server_name(), result=response))
        return response

    def stop_server(self, state: State, server: Server, timeout: int = 15) -> Arma3ServerStatus:
        logger.info(f'Stopping {server.server_name()} and its {server.headless_client_count()} headless clients')
        try:
            self.prune_server_processes(state, server)
        except NoProcessWithNameAndNamespace:
            pass

        try:
            processes = ProcessStore().get_process_and_children_by_namespace(state, NAMESPACE, server.server_name())
        except NoProcessWithNameAndNamespace:
            processes = self.create_processes_for_server(state, server)

        all_processes = [(process.into_process(), process) for process in processes if process.pid is not None]
        if not all_processes:
            return Arma3ServerStatus(
                running=False,
                headless_clients=[Arma3HeadlessClientStatus(running=False)] * server.headless_client_count(),
            )

        for idx, (subprocess, process) in enumerate(all_processes):
            logger.info(f'Stopping {idx + 1}/{len(all_processes)}')
            try:
                with ProcessStore().manage_process(state, process) as process_manager:
                    process_manager.update_state(ProcessState.STOPPING)
                    subprocess.kill()
                    subprocess.wait(timeout=timeout)
                    process.pid = None
                    process_manager.update_status(subprocess.status())
            except psutil.TimeoutExpired:
                logger.warning(f'Failed to stop process #{idx} as timeout has expired')

        headless_client_statuses = [Arma3HeadlessClientStatus(running=process.is_running()) for process, _ in all_processes[1:]]
        if len(headless_client_statuses) < server.headless_client_count():
            needed = server.headless_client_count() - len(headless_client_statuses)
            headless_client_statuses.extend([Arma3HeadlessClientStatus(running=False)] * needed)

        response = Arma3ServerStatus(
            running=all_processes[0][0].is_running(),
            headless_clients=headless_client_statuses,
        )

        State.broker.publish(ServerStopEvent(server=server.server_name(), result=response))
        return response

    def restart_server(self, state: State, server: Server) -> Arma3ServerStatus:
        logger.info(f'Restarting server {server.server_name()}')
        self.stop_server(state, server)
        response = self.start_server(state, server)
        State.broker.publish(ServerRestartEvent(server=server.server_name(), result=response))
        return response

    def server_status(self, state: State, server: Server) -> Arma3ServerStatus:
        logger.info(f'Getting server process information for {server.server_name()}')
        try:
            self.prune_server_processes(state, server)
        except NoProcessWithNameAndNamespace:
            pass

        processes = [
            process.into_process()
            for process in ProcessStore().get_process_and_children_by_namespace(state, NAMESPACE, server.server_name())
            if process.pid is not None
        ]

        headless_client_statuses = [Arma3HeadlessClientStatus(running=process.is_running()) for process in processes[1:]]
        if len(headless_client_statuses) < server.headless_client_count():
            needed = server.headless_client_count() - len(headless_client_statuses)
            headless_client_statuses.extend([Arma3HeadlessClientStatus(running=False)] * needed)

        return Arma3ServerStatus(running=processes[0].is_running(), headless_clients=headless_client_statuses)
