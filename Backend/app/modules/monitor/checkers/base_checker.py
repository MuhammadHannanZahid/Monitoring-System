from abc import ABC, abstractmethod

from app.shared.models.base_monitor import HealthCheckResponse
from app.shared.models.base_monitor import BaseMonitorModel


class BaseChecker(ABC):
    @abstractmethod
    async def check(self, monitor: BaseMonitorModel) -> HealthCheckResponse:
        pass

    async def close(self):
        pass
