from bw import log
from bw.environment import ENVIRONMENT
from bw.monitor.runner import Runner


def main():
    log.setup_config('monitor')
    Runner(ENVIRONMENT.monitor_token()).run()


if __name__ == '__main__':
    main()
