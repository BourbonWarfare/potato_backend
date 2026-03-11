import aiohttp


class Cron:
    @staticmethod
    def cron_str() -> str:
        """
        Returns a cron-encoded string defining when this job will be run next
        """
        raise NotImplementedError()

    def run(self) -> None:
        pass

    async def async_run(self) -> None:
        pass

    async def request(self, session: aiohttp.ClientSession) -> None:
        pass
