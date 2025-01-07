import hashlib
import json
import random
import time
import httpx
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from httpx import Request, Response, URL

global_headers = {
    'User-Agent': 'Dart/2.18 (dart:io)'
}

appid = 'gbDjIZQSOpCMX49P'
appSecret = 'OKFoQ9MmNXQtcyXROo4PnaFkfDPTHuDg'
apiKey = 'qiAnlPinP'

phone_aes_key = bytes.fromhex('FBC213C4C7BEEBD2AA4EDBF0F681C41B')

verdors = ['Xiaomi', 'Huawei', 'Oppo', 'Vivo', 'Samsung', 'Meizu', 'OnePlus', 'Sony', 'Google', 'Nokia', 'LG', 'HTC', 'Lenovo', 'ZTE', 'Coolpad', 'Asus', 'Sharp', 'TCL', 'Gionee', 'Motorola', 'LeEco', 'Letv', 'Smartisan', 'ZUK', 'Nubia', 'Hisense', 'Qiku', '360']
channels = ['xiaomi', 'vivo']

def random_vendor():
    return random.choice(verdors)

def random_openid():
    return ''.join([random.choice('0123456789abcdef') for _ in range(16)])

def random_channel():
    return random.choice(channels)

class Device:
    def __init__(self, vendor: str, openId: str, appVersionCode: str, appVersionName: str, appChannel: str,
                 appPlatform: str):
        """
        设备信息
        :param vendor: 设备厂家
        :param openId: 设备标识符
        :param appVersionCode: 软件版本号
        :param appVersionName: 软件版本名
        :param appChannel: 软件渠道
        :param appPlatform:
        """
        self.vendor = vendor
        self.openId = openId
        self.appVersionCode = appVersionCode
        self.appVersionName = appVersionName
        self.appChannel = appChannel
        self.appPlatform = appPlatform

    @staticmethod
    def get_default():
        """
        获取默认设备信息
        :return: 默认设备信息
        """
        return Device(
            vendor=random_vendor(),
            openId=random_openid(),
            appVersionCode='3113',
            appVersionName='4.9.3',
            appChannel=random_channel(),
            appPlatform='0'
        )
    
    @staticmethod
    def load_from_dict(data: dict[str, str]) -> 'Device':
        """
        从字典加载设备信息
        :param data: 字典
        :return: 设备信息
        """
        return Device(
            vendor=data['Qvendor'],
            openId=data['Openid'],
            appVersionCode=data['Qversioncode'],
            appVersionName=data['Qversionname'],
            appChannel=data['Qchannel'],
            appPlatform=data['Qplatform']
        )

    def to_dict(self) -> dict[str, str]:
        """
        转换为字典
        :return:
        """
        return {
            'Qvendor': self.vendor,
            'Openid': self.openId,
            'Qversioncode': self.appVersionCode,
            'Qversionname': self.appVersionName,
            'Qchannel': self.appChannel,
            'Qplatform': self.appPlatform
        }

    def to_headers_dict(self) -> dict[str, str]:
        """
        转换为请求头字典
        :return:
        """
        return {
            'Openid': self.openId,
            'Qversioncode': self.appVersionCode,
            'Qchannel': self.appChannel,
            'Qplatform': self.appPlatform,
            'Qvendor': self.vendor,
        }


def get_timestamp() -> int:
    """
    获取时间戳(毫秒)
    :return: 时间戳
    """
    return int(time.time() * 1000)

class QinlinCrypto:
    @staticmethod
    def get_encrypt_phone(phone: str) -> str:
        """
        获取加密的手机号
        :param phone: 手机号
        :return: 加密的手机号
        """
        aes = AES.new(phone_aes_key, AES.MODE_ECB)
        return aes.encrypt(pad(phone.encode(), 16)).hex().upper()

    @staticmethod
    def md5(s: str) -> str:
        """
        MD5 加密
        :param s: 字符串
        :return: MD5 加密结果
        """
        return hashlib.md5(s.encode()).hexdigest().upper()

    @staticmethod
    def get_nonce(size=5) -> str:
        """
        获取随机数
        :param size: 随机数长度
        :return: 随机数
        """
        return str(random.randint(10000, 99999))[0:size]

    @staticmethod
    def get_sign(data: dict[str, str], key: str) -> str:
        """
        获取签名
        :param data: 请求数据
        :param key: key
        :return: 签名
        """
        data_str = '&'.join([f'{k}={v}' for k, v in sorted(data.items())])
        sign = QinlinCrypto.md5(f'{data_str}&{key}')
        return sign

    @staticmethod
    def get_send_sms_sign(mobile: str, timestamp: int, nonce: str) -> str:
        """
        获取发送验证码的签名
        :param mobile: 手机号
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 签名
        """
        data = {
            'appid': appid,
            'mobile': mobile,
            'nonce': nonce,
            'timestamp': str(timestamp),
            'version': 'v2'
        }
        return QinlinCrypto.get_sign(data, f'appsecret={appSecret}')

    @staticmethod
    def get_api_sign(data: dict[str, str]) -> str:
        """
        获取 API 签名
        :param data: 请求数据
        :return: 签名
        """
        return QinlinCrypto.get_sign(data, f'key={apiKey}')

    @staticmethod
    def round_to_nearest_10_minutes(input_time: datetime) -> datetime:
        """
        将传入的时间向下取整到最近的10分钟。

        :param input_time: 输入的时间（datetime对象）
        :return: 向下取整到10分钟的时间（datetime对象）
        """
        rounded_minute = (input_time.minute // 10) * 10
        rounded_time = input_time.replace(minute=rounded_minute, second=0, microsecond=0)
        return rounded_time

    @staticmethod
    def get_open_door_password(mac: str, community_id: int,
                               timestamp: int = round_to_nearest_10_minutes(datetime.now())) -> str:
        """
        获取开门密码
        :param mac: MAC 地址
        :param community_id: 社区 ID
        :param timestamp: 时间戳
        :return: 开门密码
        """
        s = mac + str(timestamp) + str(community_id)
        key = QinlinCrypto.md5(s)
        key = "".join([c for c in key if c.isdigit()])
        return key[-4:]


class MobileAPI3Transport(httpx.BaseTransport):
    def __init__(self, qinling_api, **kwargs):
        self._wrapper = httpx.HTTPTransport(**kwargs)
        self._qinling_api = qinling_api

    def handle_request(self, request):
        url = request.url
        headers = request.headers

        ctype = headers.get('Content-Type')
        data = {}
        match ctype:
            case None:
                data = dict(url.params)
            case 'application/json':
                data = json.loads(request.content)
            case 'application/x-www-form-urlencoded':
                content = request.content.decode()
                for item in content.split('&'):
                    k, v = item.split('=')
                    data[k] = v
            case _:
                raise Exception(f"Unsupported Content-Type: {headers.get('Content-Type')}")

        timestamp = get_timestamp()
        nonce = QinlinCrypto.get_nonce()
        version = self._qinling_api.device.appVersionName
        data['timestamp'] = timestamp
        data['version'] = version
        data['nonce'] = nonce
        data['sign'] = QinlinCrypto.get_api_sign({
            'token': self._qinling_api.token,
            **data
        })

        match ctype:
            case None:
                data['sessionId'] = self._qinling_api.token
                url = URL(
                    url,
                    params=data
                )
                data = None
                headers['Content-Type'] = 'application/json'
            case 'application/json':
                data = json.dumps(data).encode()
            case 'application/x-www-form-urlencoded':
                data = '&'.join([f'{k}={v}' for k, v in data.items()]).encode()
            case _:
                raise Exception(f"Unsupported Content-Type: {headers.get('Content-Type')}")

        if data:
            headers['Content-Length'] = str(len(data))
        else:
            headers['Content-Length'] = '0'

        if ctype is not None:
            url = URL(
                url,
                params={
                    'sessionId': self._qinling_api.token
                }
            )

        new_request = Request(
            method=request.method,
            url=url,
            headers=headers,
            content=data
        )

        response = self._wrapper.handle_request(new_request)

        if response.status_code != 200:
            raise Exception(f"Error({response.status_code}): {response.read().decode(errors='ignore')}")

        data = response.read()
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return response

        if data.get('code') != 0:
            raise Exception(f"Error({data.get('code')}): {data.get('message')}")

        new_data = json.dumps(data['data']).encode()

        headers = response.headers
        headers['Content-Length'] = str(len(new_data))

        new_response = Response(
            status_code=response.status_code,
            headers=headers,
            content=new_data
        )

        return new_response

    def close(self):
        self._wrapper.close()


class QinlinAPI:
    token = ''

    def __init__(self, device: Device):
        self.device = device

        self.mobileApi3 = httpx.Client(
            base_url='https://mobileapi3.qinlinkeji.com',
            http2=True,
            transport=MobileAPI3Transport(self),
        )
        self.http2Client = httpx.Client(http2=True)
        headers = {
            **global_headers,
            **self.device.to_headers_dict(),
        }
        self.mobileApi3.headers.update(headers)

    def send_sms_code(self, mobile):
        """
        发送验证码
        :param mobile: 手机号
        :return: 发送结果
        """
        url = 'https://gateway2.qinlinkeji.com/member/sms/sendSecurityCode'

        nonce = QinlinCrypto.get_nonce(4)
        timestamp = get_timestamp()
        headers = {
            **global_headers,
            'Appid': appid,
            **self.device.to_headers_dict(),
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json; charset=utf-8',
            'Nonce': nonce,
            'Timestamp': str(timestamp),
            'Version': 'v2',
            'Sign': QinlinCrypto.get_send_sms_sign(mobile, timestamp, nonce)
        }
        data = {
            'mobile': mobile
        }
        response = self.http2Client.post(url, headers=headers, json=data)
        return response.json()

    def login(self, mobile, sms_code):
        """
        登录
        :param mobile: 手机号
        :param sms_code: 验证码
        :return: 登录结果
        """
        url = '/api/app/v1/login'

        data = {
            'mobile': QinlinCrypto.get_encrypt_phone(mobile),
            'smsCode': sms_code,
            'appChannel': 1
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def get_user_info(self):
        """
        获取用户信息
        :return: 用户信息
        """
        url = '/api/app/v1/personal/info'

        data = {
            "method": "personalInfo"
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def check_login(self):
        """
        检查登录状态
        :return: 登录状态
        """
        url = '/api/app/v1/checkLogin'

        data = {
            "method": "checkLogin"
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def logout(self):
        """
        退出登录
        :return: 退出登录结果
        """
        url = '/api/app/v1/logout'

        data = {
            "method": "logout"
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def get_community_info(self):
        """
        获取社区信息
        :return: 社区信息
        """
        url = '/api/app/user/v2/communityInfo'

        data = {
            "method": "communityInfo"
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def get_user_community_expiry_status(self, communityId: int):
        """
        获取用户社区到期状态
        :param communityId: 社区ID
        :return: 用户社区到期信息
        """
        url = '/api/app/user/v2/getUserCommunityExpiryStatus'

        data = {
            "communityId": communityId,
        }
        response = self.mobileApi3.post(url, json=data)
        return response.json()

    def get_all_door_info(self, communityId: int):
        """
        获取全部门信息
        :param communityId: 社区ID
        :return: 用户门禁缓存
        """
        url = '/api/app/user/v2/queryAllUserDoorByCache'

        data = {
            "communityId": communityId,
        }
        response = self.mobileApi3.post(url, data=data)
        return response.json()

    def get_user_door_info(self, communityId: int):
        """
        获取常用门信息
        :param communityId: 社区ID
        :return: 用户门禁缓存
        """
        url = '/api/app/user/v2/queryUserDoorByCacheNew'

        data = {
            "communityId": communityId,
        }
        response = self.mobileApi3.post(url, data=data)
        return response.json()

    def open_door(self, communityId: int, doorId: int):
        """
        开门
        :param communityId: 社区ID
        :param doorId: 门ID
        :return: 开门结果
        """
        url = '/api/open/doorcontrol/v2/open'

        data = {
            'appChannel': 1,
            "doorControlId": doorId,
            "communityId": communityId
        }
        response = self.mobileApi3.post(url, params=data)
        return response.json()

    def get_support_password_devices(self):
        """
        获取支持密码的设备
        :return: 支持密码的设备
        """
        url = 'https://qapp2.qinlinkeji.com/app/v1/userConfig/getConfig'

        response = self.http2Client.get(url)
        return response.json()['data']['supportPasswords']
