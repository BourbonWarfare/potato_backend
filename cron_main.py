from bw.cron.runner import spawn
from bw.environment import ENVIRONMENT


def main():
    spawn(ENVIRONMENT.cron_token())


if __name__ == '__main__':
    main()
