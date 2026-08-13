from app.service.mongo_db.shared_models.db_monitoring_controller_model import MonitorType
from app.modules.monitoring_controller.checkers.http_checker import HTTPChecker
from app.modules.monitoring_controller.checkers.api_checker import ApiChecker
from app.modules.monitoring_controller.checkers.ping_checker import PingChecker
from app.modules.monitoring_controller.checkers.heartbeat_checker import HeartbeatChecker
from app.modules.orion_login_manager.orion_token_manager import AccessTokenCookieManager

class CheckerFactory:
    def __init__(self, token_manager: AccessTokenCookieManager | None = None):
        self._checkers = {
            MonitorType.HTTP: HTTPChecker(),
            MonitorType.API: ApiChecker(token_manager=token_manager),
            MonitorType.PING: PingChecker(),
            MonitorType.HEARTBEAT: HeartbeatChecker(),
        }

    def get_checker(self, monitor_type: MonitorType):
        try:
            return self._checkers[monitor_type]
        except KeyError:
            raise ValueError(f"Unsupported monitor type: {monitor_type}")

    async def close(self):
        for checker in self._checkers.values():
            await checker.close()
        if token_manager := self._checkers[MonitorType.API].token_manager:
            await token_manager.close()