from contextlib import ContextDecorator
import sys
import logging

logger = logging.getLogger('bw.cron')


class StdoutLogger:
    def write(self, buffer: str):
        for line in buffer.rstrip().splitlines():
            logger.info(line)

    def flush(self):
        pass


class StderrLogger:
    def write(self, buffer: str):
        for line in buffer.rstrip().splitlines():
            logger.error(line)

    def flush(self):
        pass


class OutCapture(ContextDecorator):
    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        sys.stdout = StdoutLogger()
        sys.stderr = StderrLogger()

    def __exit__(self, *exc) -> bool:
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        return False
