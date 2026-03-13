from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from typing import Dict, List, Optional, Any
from enum import Enum


class ResponseCode(Enum):
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    SERVER_ERROR = 500

@dataclass_json
@dataclass
class ApiResponse:
    code: int = field(default=ResponseCode.SUCCESS.value, metadata=config(field_name='code'))
    message: str = field(default='Success', metadata=config(field_name='message'))
    data: Any = field(default=None, metadata=config(field_name='data'))
