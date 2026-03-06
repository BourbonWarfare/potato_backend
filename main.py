import bw.server  # noqa: F401
from bw.server import run, production
from bw.environment import ENVIRONMENT


def main():
    if ENVIRONMENT.deploy_asgi():
        production()
    else:
        run()


if __name__ == '__main__':
    main()
