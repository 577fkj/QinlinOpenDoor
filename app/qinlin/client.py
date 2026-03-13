import httpx
from typing import Optional, List, Dict

from ..core.security import Crypto, APPID, APP_SECRET
from ..models.device import Device
from ..models.user import UserData, UserCommunityInfo as UserCommunityInfo
from ..models.api_models import (
    LoginResponse, UserInfo, CommunityInfo, DoorInfo
)
from .transport import ApiTransport, get_timestamp


class QinlinClient:
    def __init__(self, device: Device, token: str = ''):
        self.device = device
        self.token = token
        self._http_client = httpx.AsyncClient(http2=True)

        self._api_client = httpx.AsyncClient(
            base_url='https://mobileapi3.qinlinkeji.com',
            http2=True,
            transport=ApiTransport(self),
            headers={
                'User-Agent': 'Dart/2.18 (dart:io)',
                **self.device.to_dict()
            }
        )

    async def send_sms_code(self, mobile: str) -> bool:
        nonce = Crypto.generate_nonce(4)
        timestamp = get_timestamp()
        
        headers = {
            'User-Agent': 'Dart/2.18 (dart:io)',
            'Appid': APPID,
            **self.device.to_dict(),
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json; charset=utf-8',
            'Nonce': nonce,
            'Timestamp': str(timestamp),
            'Version': 'v2',
            'Sign': Crypto.get_sms_sign(mobile, timestamp, nonce)
        }
        
        response = await self._http_client.post(
            'https://gateway2.qinlinkeji.com/member/sms/sendSecurityCode',
            headers=headers,
            json={'mobile': mobile}
        )

        data = response.json()
        if data.get('success'):
            return True
        print(f"Failed to send SMS code: {data}")
        return False

    async def login(self, mobile: str, sms_code: str) -> LoginResponse:
        data = {
            'mobile': Crypto.encrypt_phone(mobile),
            'smsCode': sms_code,
            'appChannel': 1
        }
        
        response = await self._api_client.post('/api/app/v1/login', json=data)
        return LoginResponse.from_dict(response.json())

    async def get_user_info(self) -> UserInfo:
        response = await self._api_client.post(
            '/api/app/v1/personal/info',
            json={'method': 'personalInfo'}
        )
        return UserInfo.from_dict(response.json())

    async def check_login(self) -> bool:
        try:
            response = await self._api_client.post(
                '/api/app/v1/checkLogin',
                json={'method': 'checkLogin'}
            )
            return response.json() > 0
        except Exception:
            return False

    async def logout(self) -> Dict:
        response = await self._api_client.post(
            '/api/app/v1/logout',
            json={'method': 'logout'}
        )
        return response.json()

    async def get_community_info(self) -> List[CommunityInfo]:
        response = await self._api_client.post(
            '/api/app/user/v2/communityInfo',
            json={'method': 'communityInfo'}
        )
        data = response.json()
        return [CommunityInfo.from_dict(item) for item in data]

    async def get_all_door_info(self, community_id: int) -> List[DoorInfo]:
        response = await self._api_client.post(
            '/api/app/user/v2/queryAllUserDoorByCache',
            data={'communityId': community_id}
        )
        data = response.json()

        doors = []
        
        # 楼栋门
        buildingDoorList = data.get('buildingDoorList', [])
        for item in buildingDoorList:
            doors.append(DoorInfo.from_dict(item))
        
        # 自定义门
        customDoorList = data.get('customDoorList', [])
        for item in customDoorList:
            doors.append(DoorInfo.from_dict(item))
        
        # 小区门
        gateDoorList = data.get('gateDoorList', [])
        for item in gateDoorList:
            doors.append(DoorInfo.from_dict(item))

        return doors

    async def get_user_door_info(self, community_id: int) -> List[DoorInfo]:
        response = await self._api_client.post(
            '/api/app/user/v2/queryUserDoorByCacheNew',
            data={'communityId': community_id}
        )
        data = response.json()
        doors = []

        # 常用门
        commonlyUsedDoor = data.get('commonlyUsedDoor', {})
        doors.append(DoorInfo.from_dict(commonlyUsedDoor))

        # 更多常用门
        userDoorDTOS = data.get('userDoorDTOS', [])
        for item in userDoorDTOS:
            doors.append(DoorInfo.from_dict(item))

        return doors

    async def open_door(self, community_id: int, door_id: int) -> bool:
        params = {
            'appChannel': 1,
            'doorControlId': door_id,
            'communityId': community_id
        }
        
        response = await self._api_client.post(
            '/api/open/doorcontrol/v2/open',
            params=params
        )
        data = response.json()
        if data.get('openDoorState') == 1:
            return True
        print(f"Failed to open door: {data}")
        return False

    async def get_user_community_expiry_status(self, community_id: int) -> Dict:
        response = await self._api_client.post(
            '/api/app/user/v2/getUserCommunityExpiryStatus',
            json={'communityId': community_id}
        )
        return response.json()

    @staticmethod
    async def get_support_password_devices() -> List[str]:
        async with httpx.AsyncClient(http2=True) as client:
            response = await client.get(
                'https://qapp2.qinlinkeji.com/app/v1/userConfig/getConfig'
            )
            data = response.json()
            return data.get('data', {}).get('supportPasswords', [])

    async def fetch_user_info(self) -> UserData:
        """
        获取完整的用户数据
        """
        user_info = await self.get_user_info()
        communities_info = await self.get_community_info()
        
        communities = []
        for community in communities_info:
            door_list = await self.get_all_door_info(community.community_id)
            communities.append(UserCommunityInfo(
                info=community,
                doors=door_list
            ))
        
        user_data = UserData(
            info=user_info,
            communities=communities,
        )
        
        return user_data

