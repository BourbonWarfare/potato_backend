import bw.server  # noqa: F401
from bw.environment import ENVIRONMENT
from bw.server import production, run


def main():
    if ENVIRONMENT.deploy_asgi():
        production()
    else:
        run()


if __name__ == '__main__':
    main()
