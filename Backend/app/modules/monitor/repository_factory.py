from app.shared.enums import MonitorType
from app.modules.HTTP_monitor.repository import HTTP_monitorRepository
from app.modules.API_monitor.repository import API_monitorRepository


class MonitorRepositoryFactory:

    def __init__(
        self,
        http_repository: HTTP_monitorRepository,
        api_repository: API_monitorRepository,
    ):
        self._repositories = {
            MonitorType.HTTP: http_repository,
            MonitorType.API: api_repository,
        }

    def get_repository(self, monitor_type: MonitorType):

        try:
            return self._repositories[monitor_type]

        except KeyError:
            raise ValueError(
                f"Unsupported monitor type: {monitor_type}"
            )