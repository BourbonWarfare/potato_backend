from bw.environment import ENVIRONMENT
from bw.monitor.runner import Runner


def main():
    Runner(ENVIRONMENT.monitor_token()).run()


if __name__ == '__main__':
    main()
