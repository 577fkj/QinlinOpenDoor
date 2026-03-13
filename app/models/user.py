from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from typing import List, Optional, TYPE_CHECKING

from .device import Device
from .api_models import CommunityInfo, DoorInfo, UserInfo

if TYPE_CHECKING:
    from ..qinlin.client import QinlinClient

@dataclass_json
@dataclass
class UserCommunityInfo:
    info: CommunityInfo = field(default_factory=CommunityInfo, metadata=config(field_name='info'))
    doors: List[DoorInfo] = field(default_factory=list, metadata=config(field_name='doors'))

@dataclass_json
@dataclass
class UserData:
    info: Optional[UserInfo] = None
    communities: List[UserCommunityInfo] = field(default_factory=list, metadata=config(field_name='communities'))

    def get_community_by_id(self, community_id: int) -> Optional[UserCommunityInfo]:
        for community in self.communities:
            if community.info.community_id == community_id:
                return community
        return None


@dataclass_json
@dataclass
class User:
    token: str = field(default='', metadata=config(field_name='token'))
    decvice: Device = field(default_factory=Device, metadata=config(field_name='device'))
    data: UserData = field(default_factory=UserData, metadata=config(field_name='data'))
    auto_relogin: bool = field(default=True, metadata=config(field_name='auto_relogin'))

@dataclass
class RunningUser:
    api: 'QinlinClient'
    phone: str
    user: User
    is_online: bool = False

    def set_token(self, token: str):
        self.user.token = token
        self.api.token = token
    
    async def update_user_info(self):
        user_data = await self.api.fetch_user_info()
        self.user.data = user_data
        self.is_online = True

