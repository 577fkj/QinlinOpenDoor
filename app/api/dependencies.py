from typing import Optional
from quart import request, current_app

from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..services.scheduler_service import SchedulerService
from ..services.sms_service import SmsService
from ..core.cache import CacheManager
from ..core.config import ConfigManager

class AppState:
    def __init__(self):
        self.user_service: UserService = None
        self.sms_service: SmsService = None
        self.auth_service: AuthService = None
        self.cache_manager: CacheManager = None
        self.config_manager: ConfigManager = None
        self.scheduler_service: SchedulerService = None
        self.access_token: str = ''


def get_app_state() -> AppState:
    return current_app.state

