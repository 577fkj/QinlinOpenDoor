import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from typing import Dict
import asyncio
import aiofiles
from typing import Optional

from ..models.user import User


@dataclass_json
@dataclass
class AppConfig:
    user: Dict[str, User] = field(default_factory=dict)
    access_token: str = 'your-secure-token-here'
    auto_relogin_retry: int = 2
    favorites: Dict[str, list] = field(default_factory=dict)  # 收藏的门禁，格式: {phone: [doorId1, doorId2, ...]}


class ConfigManager:

    def __init__(self, config_path: str = 'config/config.json'):
        self._config_path = Path(config_path)
        self.config: AppConfig = AppConfig()
        self._initialized = False
        self._lock = asyncio.Lock()
        self._last_saved_config: Optional[AppConfig] = None

        self._ensure_config_dir()
    
    @classmethod
    async def create(cls, config_path: str = 'config/config.json') -> 'ConfigManager':
        manager = cls(config_path)
        await manager._load()
        return manager
    
    async def initialize(self):
        if self._initialized:
            return
        
        self._initialized = True

    async def _load(self):
        if self._config_path.exists():
            try:
                async with aiofiles.open(self._config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.config = AppConfig.from_json(content)
                    self._last_saved_config = self.config.to_json()
            except Exception as e:
                print(f"Failed to load config: {e}")
                exit(1)
        else:
            await self.save()  # Save default config if file doesn't exist

    def _ensure_config_dir(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
    

    async def update_user(self, phone: str, user: User):
        async with self._lock:
            self.config.user[phone] = user

    async def save(self):
        if self._last_saved_config == self.config.to_json():
            return
        
        async with self._lock:
            tmp_path = self._config_path.with_suffix(self._config_path.suffix + '.tmp')
            bak_path = self._config_path.with_suffix(self._config_path.suffix + '.bak')
            try:
                async with aiofiles.open(tmp_path, 'w', encoding='utf-8') as f:
                    await f.write(self.config.to_json(indent=4, ensure_ascii=False))
                
                if self._config_path.exists():
                    os.replace(self._config_path, bak_path)
                os.replace(tmp_path, self._config_path)
                
                self._last_saved_config = self.config.to_json()
            except Exception as e:
                print(f"Failed to save config: {e}")
                if tmp_path.exists():
                    os.remove(tmp_path)