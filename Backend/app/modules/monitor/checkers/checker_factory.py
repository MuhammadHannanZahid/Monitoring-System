from app.shared.enums import MonitorType

from app.modules.monitor.checkers.http_checker import HTTPChecker
from app.modules.monitor.checkers.api_checker import ApiChecker


class CheckerFactory:
    def __init__(self):
        self.http_checker = HTTPChecker()
        self.api_checker = ApiChecker()

    def get_checker(
        self,
        monitor_type: MonitorType,
    ):

        if monitor_type == MonitorType.HTTP:
            return self.http_checker

        if monitor_type == MonitorType.API:
            return self.api_checker

        raise ValueError(
            f"Unsupported monitor type: {monitor_type}"
        )

    async def close(self):
        await self.http_checker.close()
        await self.api_checker.close()