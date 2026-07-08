from bw.web_event import BaseEvent
from dataclasses import dataclass
from typing import Any


class CronEvent(BaseEvent, namespace='cron', abstract=True):
    pass


@dataclass
class CronRun(CronEvent, event='run'):
    cron: str

    def data(self) -> dict[str, Any]:
        return {'cron': self.cron}
