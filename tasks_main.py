from bw.log import setup_config
from bw.tasks.runner import Runner


def main():
    setup_config('tasks')
    Runner().run()


if __name__ == '__main__':
    main()
