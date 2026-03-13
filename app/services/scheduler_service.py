import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..services.user_service import UserService
from ..services.auth_service import AuthService

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, user_service: UserService, auth_service: AuthService):
        self.user_service = user_service
        self.auth_service = auth_service
        self.scheduler = AsyncIOScheduler()

    async def check_login_task(self):
        for user in self.user_service.users:
            try:
                if not user.is_online:
                    continue
                
                if await user.api.check_login():
                    await self.user_service.update_user(user.phone)
                else:
                    user.is_online = False
                    
                    if not user.user.auto_relogin:
                        logger.info(f"User {user.phone} login expired but auto-relogin disabled")
                        continue
                    
                    logger.warning(f"User {user.phone} login expired, starting auto-relogin")
                    asyncio.create_task(self.auth_service.auto_relogin(user))
                    
            except Exception as e:
                user.is_online = False
                logger.exception(f"Check login failed for {user.phone}: {e}")

    async def check_users_on_startup(self):
        logger.info("Checking user login status on startup")
        for user in self.user_service.users:
            if not user.is_online:
                if not user.user.auto_relogin:
                    logger.info(f"User {user.phone} is offline but auto-relogin disabled")
                    continue
                
                logger.warning(f"User {user.phone} is offline, starting auto-relogin")
                asyncio.create_task(self.auth_service.auto_relogin(user))
            else:
                logger.info(f"User {user.phone} is online")

    def start(self):
        self.scheduler.add_job(self.check_login_task, 'interval', seconds=60)
        self.scheduler.start()
