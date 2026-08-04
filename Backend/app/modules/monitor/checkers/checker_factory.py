from app.shared.enums import MonitorType
from app.modules.monitor.checkers.http_checker import HTTPChecker
from app.modules.monitor.checkers.api_checker import ApiChecker

class CheckerFactory:
    def __init__(self):
        self._checkers = {MonitorType.HTTP: HTTPChecker(), MonitorType.API: ApiChecker()}

    def get_checker(self, monitor_type: MonitorType):
        try:
            return self._checkers[monitor_type]
        except KeyError:
            raise ValueError(f"Unsupported monitor type: {monitor_type}")

    async def close(self):
        for checker in self._checkers.values():
            await checker.close()