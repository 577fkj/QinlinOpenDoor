import random
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config

VENDORS = ['Xiaomi', 'Huawei', 'Oppo', 'Vivo', 'Samsung', 'Meizu', 'OnePlus', 'Sony', 'Google']
CHANNELS = ['xiaomi', 'vivo']

def random_openid():
    return ''.join([random.choice('0123456789abcdef') for _ in range(16)])

def random_vendor() -> str:
    return random.choice(VENDORS)

def random_channel() -> str:
    return random.choice(CHANNELS)

@dataclass_json
@dataclass
class Device:
    vendor: str = field(default_factory=random_vendor, metadata=config(field_name='Qvendor'))
    open_id: str = field(default_factory=random_openid, metadata=config(field_name='Openid'))
    app_version_code: str = field(default='3113', metadata=config(field_name='Qversioncode'))
    app_version_name: str = field(default='4.9.3', metadata=config(field_name='Qversionname'))
    app_channel: str = field(default_factory=random_channel, metadata=config(field_name='Qchannel'))
    app_platform: str = field(default='0', metadata=config(field_name='Qplatform'))

