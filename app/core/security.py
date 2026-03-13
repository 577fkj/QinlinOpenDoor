import hashlib
import random
import math
from datetime import datetime
from Crypto.Cipher import AES, DES3
from Crypto.Util.Padding import pad

APPID = 'gbDjIZQSOpCMX49P'
APP_SECRET = 'OKFoQ9MmNXQtcyXROo4PnaFkfDPTHuDg'
API_KEY = 'qiAnlPinP'
PHONE_AES_KEY = bytes.fromhex('FBC213C4C7BEEBD2AA4EDBF0F681C41B')

BLUETOOTH_DES_KEY = '55AA5A5AA5'
BLUETOOTH_HEADER = '30'
BLUETOOTH_KEY = 'FA34DD0001'


class Crypto:
    @staticmethod
    def md5(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest().upper()

    @staticmethod
    def encrypt_phone(phone: str) -> str:
        cipher = AES.new(PHONE_AES_KEY, AES.MODE_ECB)
        return cipher.encrypt(pad(phone.encode(), 16)).hex().upper()

    @staticmethod
    def generate_nonce(size: int = 5) -> str:
        return str(random.randint(10 ** (size - 1), 10 ** size - 1))

    @staticmethod
    def get_sign(data: dict, key_suffix: str) -> str:
        data_str = '&'.join(f'{k}={v}' for k, v in sorted(data.items()))
        return Crypto.md5(f'{data_str}&{key_suffix}')

    @staticmethod
    def get_sms_sign(mobile: str, timestamp: int, nonce: str) -> str:
        data = {
            'appid': APPID,
            'mobile': mobile,
            'nonce': nonce,
            'timestamp': str(timestamp),
            'version': 'v2'
        }
        return Crypto.get_sign(data, f'appsecret={APP_SECRET}')

    @staticmethod
    def get_api_sign(data: dict) -> str:
        return Crypto.get_sign(data, f'key={API_KEY}')

    @staticmethod
    def pad_string(text: str, block_size: int, padding: str = '0') -> str:
        if len(text) % block_size == 0:
            return text
        return (block_size - len(text) % block_size) * padding + text

    @staticmethod
    def des3_encrypt(key: str, plaintext: str) -> bytes:
        key_bytes = bytes.fromhex(key)
        plaintext_bytes = bytes.fromhex(plaintext)
        
        length = 8 - (len(plaintext_bytes) % 8)
        plaintext_bytes += bytes([length]) * length
        
        cipher = DES3.new(key_bytes, DES3.MODE_ECB)
        return cipher.encrypt(plaintext_bytes)

    @staticmethod
    def des3_decrypt(key: str, ciphertext: bytes) -> bytes:
        key_bytes = bytes.fromhex(key)
        cipher = DES3.new(key_bytes, DES3.MODE_ECB)
        return cipher.decrypt(ciphertext)

    @staticmethod
    def xor_checksum(data: bytes) -> int:
        result = 0
        for b in data:
            result ^= b
        return result

    @staticmethod
    def get_bluetooth_open_door_data(mac: str, timestamp: int) -> bytes:
        date = datetime.fromtimestamp(timestamp / 1000)
        year = Crypto.pad_string(str(date.year)[2:], 2)
        month = Crypto.pad_string(str(date.month), 2)
        day = Crypto.pad_string(str(date.day), 2)
        hour = Crypto.pad_string(str(date.hour), 2)
        minute = Crypto.pad_string(str(date.minute), 2)
        
        date_str = f'{year}{month}{day}{hour}{minute}'
        data = f'{date_str}{mac[6:]}'
        key = f'{mac}{date_str}{BLUETOOTH_DES_KEY}'
        
        encrypted = Crypto.des3_encrypt(key, data).hex()[:16]
        data = f'{BLUETOOTH_HEADER}{encrypted}{date_str}{BLUETOOTH_KEY}'
        data += hex(Crypto.xor_checksum(bytes.fromhex(data)))[2:]
        
        return bytes.fromhex(data)

    @staticmethod
    def get_rounded_minute(dt: datetime, round_up: bool = False) -> datetime:
        if round_up:
            rounded_minute = math.ceil(dt.minute / 10) * 10
        else:
            rounded_minute = math.floor(dt.minute / 10) * 10
        return dt.replace(minute=rounded_minute, second=0, microsecond=0)

    @staticmethod
    def get_door_password(mac: str, community_id: int, timestamp: datetime) -> str:
        rounded_time = Crypto.get_rounded_minute(timestamp, round_up=False)
        key_str = mac + str(rounded_time) + str(community_id)
        key = Crypto.md5(key_str)
        digits = ''.join(c for c in key if c.isdigit())
        return digits[-4:]
