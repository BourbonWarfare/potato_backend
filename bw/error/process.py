from bw.error.base import BwServerError
from uuid import UUID


class ProcessError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured while managing a process: {reason}')


class SpecificProcessError(ProcessError):
    def __init__(
        self,
        message: str,
        *,
        process_id: int | None = None,
        process_namespace: str | None = None,
        process_name: str | None = None,
        process_uuid: UUID | None = None,
    ):
        if process_id:
            super().__init__(f'Process with ID "{process_id}" {message}')
        elif process_namespace and process_name:
            super().__init__(f'Process with namespace "{process_namespace}" called "{process_name}" {message}')
        elif process_uuid:
            super().__init__(f'Process with UUID "{process_uuid}" {message}')
        else:
            super().__init__(message)


class NoProcessWithUuid(ProcessError):
    def __init__(self, uuid: UUID):
        super().__init__(f'No process with UUID "{uuid}" exists')


class NoProcessWithNameAndNamespace(ProcessError):
    def __init__(self, namespace: str, name: str):
        super().__init__(f'No process in namespace "{namespace}" called "{name}" exists')


class ProcessHasNoPid(SpecificProcessError):
    def __init__(
        self,
        *,
        process_id: int | None = None,
        process_namespace: str | None = None,
        process_name: str | None = None,
        process_uuid: UUID | None = None,
    ):
        super().__init__(
            'has a `null` PID',
            process_id=process_id,
            process_namespace=process_namespace,
            process_name=process_name,
            process_uuid=process_uuid,
        )


class DeletingProcessWithAliveChild(SpecificProcessError):
    def __init__(
        self,
        *,
        process_id: int | None = None,
        process_namespace: str | None = None,
        process_name: str | None = None,
        process_uuid: UUID | None = None,
    ):
        super().__init__(
            'is being deleted while it still has active children',
            process_id=process_id,
            process_namespace=process_namespace,
            process_name=process_name,
            process_uuid=process_uuid,
        )
