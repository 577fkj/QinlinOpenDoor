import asyncio
import logging
from typing import List, Optional

from ..core.config import ConfigManager
from ..models.device import Device
from ..models.user import User, UserData, RunningUser
from ..qinlin.client import QinlinClient

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.users: List[RunningUser] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    @classmethod
    async def create(cls, config_manager: ConfigManager) -> 'UserService':
        service = cls(config_manager)
        await service.initialize()
        return service

    async def initialize(self):
        if self._initialized:
            return

        config = self.config_manager.config
        
        for phone, user_config in config.user.items():
            try:
                client = QinlinClient(user_config.decvice, user_config.token)
                self.users.append(RunningUser(
                    api=client,
                    phone=phone,
                    user=user_config,
                    is_online=True
                ))
                
            except Exception as e:
                logger.exception(f"Failed to initialize user {phone}: {e}")
        
        logger.info(f"Loaded {len(self.users)} users")

        logger.info("Checking all users login status on initialization")
        await self.check_all_users()

        self._initialized = True
    
    async def check_all_users(self):
        for user in self.users:
            try:
                if await user.api.check_login():
                    await self.update_user(user.phone)
                else:
                    user.is_online = False
            except Exception as e:
                user.is_online = False
                logger.exception(f"Failed to check login for {user.phone}: {e}")

    async def get(self, phone: Optional[str] = None) -> Optional[RunningUser]:
        async with self._lock:
            for user in self.users:
                if phone and user.phone == phone:
                    return user
        return None

    async def update_user(self, phone: str, token: str = None, device: Device = None) -> RunningUser:
        run_user_info = await self.get(phone)
        async with self._lock:
            if not run_user_info:
                run_user_info = RunningUser(
                    api=QinlinClient(device, token),
                    phone=phone,
                    user=User(
                        token=token,
                        decvice=device,
                        auto_relogin=True
                    ),
                    is_online=True
                )
                self.users.append(run_user_info)
            
            
            if token is not None:
                run_user_info.set_token(token)

            if run_user_info.user.token:
                try:
                    await run_user_info.update_user_info()
                    run_user_info.is_online = True
                except Exception as e:
                    logger.exception(f"Failed to update user info for {phone}: {e}")
                    run_user_info.is_online = False
            
            await self.config_manager.update_user(phone, run_user_info.user)
            await self.config_manager.save()
            return run_user_info

    async def update_auto_relogin(self, phone: str, enabled: bool) -> bool:
        user = await self.get(phone)
        if not user:
            return False
        
        async with self._lock:
            user.user.auto_relogin = enabled
            await self.config_manager.save()
        
        return True

    async def get_all_users_data(self) -> List:
        async with self._lock:
            result = []
            for user in self.users:
                user_dict = user.user.data.to_dict() if user.user.data else {}
                user_dict['phone'] = user.phone
                user_dict['is_online'] = user.is_online
                user_dict['auto_relogin'] = user.user.auto_relogin
                result.append(user_dict)
            return result
