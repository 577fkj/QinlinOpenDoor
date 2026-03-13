import asyncio
from time import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class SmsWaitingState:
    waiting: bool
    code: Optional[str]
    send_time: float
    received_time: Optional[float] = None


class SmsService:
    def __init__(self):
        self._states = {}
        self._lock = asyncio.Lock()

    async def set_waiting(self, phone: str):
        async with self._lock:
            self._states[phone] = SmsWaitingState(
                waiting=True,
                code=None,
                send_time=time()
            )

    async def set_code(self, phone: str, code: str) -> bool:
        async with self._lock:
            if phone in self._states and self._states[phone].waiting:
                self._states[phone].code = code
                self._states[phone].received_time = time()
                return True
        return False

    async def get_code(self, phone: str) -> Optional[str]:
        async with self._lock:
            if phone in self._states:
                return self._states[phone].code
        return None

    async def wait_for_code(self, phone: str, timeout: float = 180) -> Optional[str]:
        start_time = time()
        while time() - start_time < timeout:
            code = await self.get_code(phone)
            if code:
                return code
            await asyncio.sleep(1)
        return None

    async def clear_state(self, phone: str):
        async with self._lock:
            self._states.pop(phone, None)

    async def stop_waiting(self, phone: str):
        async with self._lock:
            if phone in self._states:
                self._states[phone].waiting = False
