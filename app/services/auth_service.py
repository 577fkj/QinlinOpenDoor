import asyncio
import logging

from ..services.user_service import UserService
from ..services.sms_service import SmsService
from ..models.user import RunningUser

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_service: UserService, sms_service: SmsService, max_retry: int = 2):
        self.user_service = user_service
        self.sms_service = sms_service
        self.max_retry = max_retry

    async def auto_relogin(self, user: RunningUser) -> bool:
        try:
            phone = user.phone
            logger.info(f"Starting auto-relogin for user {phone}")
            
            for attempt in range(self.max_retry):
                try:
                    logger.info(f"Auto-relogin attempt {attempt + 1}/{self.max_retry} for {phone}")
                    
                    await user.api.send_sms_code(phone)
                    logger.info(f"SMS code sent to {phone}")
                    
                    await self.sms_service.set_waiting(phone)
                    code = await self.sms_service.wait_for_code(phone, timeout=180)
                    
                    if not code:
                        logger.warning(f"No SMS code received for {phone}, attempt {attempt + 1}")
                        continue
                    
                    logger.info(f"Attempting login with code for {phone}")
                    login_response = await user.api.login(phone, code)
                    token = login_response.session_id
                    
                    if not token:
                        logger.error(f"Login failed for {phone}: no sessionId")
                        continue
                    
                    self.user_service.update_user(phone, token)
                    logger.info(f"Auto-relogin successful for {phone}")
                    
                    await self.sms_service.clear_state(phone)
                    
                    return True
                    
                except Exception as e:
                    logger.exception(f"Auto-relogin attempt {attempt + 1} failed for {phone}: {e}")
                    continue
            
            logger.error(f"Auto-relogin failed for {phone} after {self.max_retry} attempts")
            await self.sms_service.stop_waiting(phone)
            return False
            
        except Exception as e:
            logger.exception(f"Critical error in auto_relogin: {e}")
            return False
