from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from typing import Dict, List, Optional


@dataclass_json
@dataclass
class LoginResponse:
    flag: int = field(metadata=config(field_name='flag'))
    session_id: str = field(metadata=config(field_name='sessionId'))


@dataclass_json
@dataclass
class UserInfo:
    user_id: int = field(default=0, metadata=config(field_name='id'))
    mobile: str = ''
    nick_name: str = field(default=None, metadata=config(field_name='nickName'))
    user_name: str = field(default='', metadata=config(field_name='userName'))
    real_name: str = field(default='', metadata=config(field_name='realName'))
    has_face: int = field(default=0, metadata=config(field_name='hasFaceKey'))
    avatar: str = field(default=None, metadata=config(field_name='portraitUrl'))


@dataclass_json
@dataclass
class CommunityInfo:
    # 地址信息
    province_name: str = field(default='', metadata=config(field_name='provinceName'))
    city_name: str = field(default='', metadata=config(field_name='cityName'))
    district_name: str = field(default='', metadata=config(field_name='districtName'))

    # 社区信息
    community_id: int = field(default=0, metadata=config(field_name='communityId'))
    community_code: str = field(default='', metadata=config(field_name='communityCode'))
    community_name: str = field(default='', metadata=config(field_name='communityName'))

    # 房屋信息
    building_name: Optional[str] = field(default=None, metadata=config(field_name='buildingName'))
    house_id: Optional[str] = field(default=None, metadata=config(field_name='houseId'))
    house_no: Optional[str] = field(default=None, metadata=config(field_name='houseNo'))

    # 其他信息
    expiry_date: Optional[str] = field(default=None, metadata=config(field_name='expiryDate'))


@dataclass_json
@dataclass
class DoorInfo:
    device_model: str = field(default='', metadata=config(field_name='deviceModel'))
    door_id: int = field(default=0, metadata=config(field_name='doorControlId'))
    door_name: str = field(default='', metadata=config(field_name='doorControlName'))
    door_custom_name: str = field(default='', metadata=config(field_name='customDoorControlName'))
    mac: Optional[str] = field(default=None, metadata=config(field_name='macAddress'))
    online_status: str = field(default='', metadata=config(field_name='online'))

