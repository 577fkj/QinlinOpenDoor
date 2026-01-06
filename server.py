from flask import Flask, jsonify, request, render_template, send_from_directory
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from functools import wraps
from time import time
import qinlinAPI
import json
import os
import threading
import logging
import re
from apscheduler.schedulers.blocking import BlockingScheduler
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ================== 配置常量 ==================
HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', 5000)
DEBUG = os.getenv('DEBUG', False)
CONFIG_FILE = 'config/config.json'
CONFIG_DIR = 'config'

# ================== 数据结构 ==================

class ResponseCode(Enum):
    """响应状态码枚举"""
    SUCCESS = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    SERVER_ERROR = 500


@dataclass
class ApiResponse:
    """统一API响应结构"""
    code: int
    message: str
    data: Any = None

    def to_dict(self) -> Dict:
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data
        }


@dataclass
class UserConfig:
    """用户配置结构"""
    token: str
    device: Dict
    user_info: Dict
    auto_relogin_enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> 'UserConfig':
        return cls(
            token=data.get('token', ''),
            device=data.get('device', {}),
            user_info=data.get('user_info', {}),
            auto_relogin_enabled=data.get('auto_relogin_enabled', True)
        )

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AppConfig:
    """应用配置结构"""
    user: Dict[str, UserConfig] = field(default_factory=dict)
    access_token: str = 'your-secure-token-here'
    auto_relogin_retry: int = 2

    @classmethod
    def from_dict(cls, data: Dict) -> 'AppConfig':
        users = {}
        for phone, user_data in data.get('user', {}).items():
            users[phone] = UserConfig.from_dict(user_data)
        
        return cls(
            user=users,
            access_token=data.get('access_token', 'your-secure-token-here'),
            auto_relogin_retry=data.get('auto_relogin_retry', 2)
        )

    def to_dict(self) -> Dict:
        return {
            'user': {phone: user.to_dict() for phone, user in self.user.items()},
            'access_token': self.access_token,
            'auto_relogin_retry': self.auto_relogin_retry
        }


@dataclass
class User:
    """用户运行时数据结构"""
    index: int
    phone: str
    api: qinlinAPI.QinlinAPI
    user_info: Dict = field(default_factory=dict)
    community_info: List[Dict] = field(default_factory=list)
    all_door: Dict[int, List] = field(default_factory=dict)
    is_online: bool = False
    auto_relogin_enabled: bool = True

    def to_dict(self, include_api: bool = False) -> Dict:
        """转换为字典，可选择是否包含API对象"""
        result = {
            'index': self.index,
            'phone': self.phone,
            'user_info': self.user_info,
            'community_info': self.community_info,
            'all_door': self.all_door,
            'is_online': self.is_online,
            'auto_relogin_enabled': self.auto_relogin_enabled
        }
        if include_api:
            result['api'] = self.api
        return result


@dataclass
class SmsWaitingState:
    """短信验证码等待状态"""
    waiting: bool
    code: Optional[str]
    send_time: float
    received_time: Optional[float] = None


@dataclass
class CacheEntry:
    """缓存条目"""
    timestamp: float
    data: Any


# ================== 配置管理器 ==================

class ConfigManager: 
    """配置文件管理器"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = os.path.dirname(self.config_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)

    def load(self) -> AppConfig:
        """加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return AppConfig.from_dict(data)
        
        # 返回默认配置
        config = AppConfig()
        self.save(config)
        return config

    def save(self, config: AppConfig):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, indent=4, ensure_ascii=False)


# ================== 用户管理器 ==================

class UserManager: 
    """用户管理器"""
    
    def __init__(self, config: AppConfig):
        self.users: List[User] = []
        self.config = config
        self._load_users()

    def _load_users(self):
        """从配置加载用户"""
        idx = 0
        for phone, user_config in self.config.user.items():
            try:
                # 初始化设备和API
                device = qinlinAPI.Device.load_from_dict(user_config.device)
                ql_api = qinlinAPI.QinlinAPI(device)
                
                if user_config.token:
                    ql_api.token = user_config.token

                user_info = user_config.user_info
                community_info = []
                all_door = {}
                online = False

                # 尝试获取用户信息
                try:
                    user_info = ql_api.get_user_info()
                    community_info = ql_api.get_community_info()
                    
                    for community in community_info:
                        community_id = community['communityId']
                        all_door[community_id] = ql_api.get_all_door_info(community_id)

                    online = ql_api.check_login() > 0
                except Exception as e:
                    logging.exception(f"Failed to load user {phone}: {e}")

                # 更新配置中的用户信息
                user_config.user_info = user_info

                # 创建用户对象
                user = User(
                    index=idx,
                    phone=phone,
                    api=ql_api,
                    user_info=user_info,
                    community_info=community_info,
                    all_door=all_door,
                    is_online=online,
                    auto_relogin_enabled=user_config.auto_relogin_enabled
                )
                
                self.users.append(user)
                idx += 1

            except Exception as e:
                logging.exception(f"Failed to initialize user {phone}: {e}")

        logging.info(f"Loaded {len(self.users)} users")

    def get_user(self, idx: Optional[int] = None, phone: Optional[str] = None) -> Optional[User]:
        """获取用户"""
        for user in self.users:
            if phone and user.phone == phone:
                return user
            if idx is not None and user.index == idx:
                return user
        return None

    def get_user_api(self, idx: int, phone: Optional[str] = None) -> Optional[qinlinAPI.QinlinAPI]:
        """获取用户API"""
        user = self.get_user(idx, phone)
        return user.api if user else None

    def update_or_create_user(self, phone: str, token: str, device: Dict,
                              user_info: Dict, community_info: List[Dict],
                              all_door: Dict, user_api: qinlinAPI.QinlinAPI) -> User:
        """更新或创建用户"""
        user = self.get_user(phone=phone)
        
        if user:
            # 更新现有用户
            user.user_info = user_info
            user.community_info = community_info
            user.all_door = all_door
            user.is_online = True
            user.api = user_api
            idx = user.index
        else:
            # 创建新用户
            idx = self.users[-1].index + 1 if self.users else 0
            user = User(
                index=idx,
                phone=phone,
                api=user_api,
                user_info=user_info,
                community_info=community_info,
                all_door=all_door,
                is_online=True,
                auto_relogin_enabled=True
            )
            self.users.append(user)

        # 更新配置
        self.config.user[phone] = UserConfig(
            token=token,
            device=device,
            user_info=user_info,
            auto_relogin_enabled=user.auto_relogin_enabled
        )

        return user

    def get_all_users_data(self) -> List[Dict]:
        """获取所有用户数据（不包含API对象）"""
        return [user.to_dict(include_api=False) for user in self.users]


# ================== 缓存管理器 ==================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str, max_age: float) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._store:
                entry = self._store[key]
                if time() - entry.timestamp < max_age:
                    logging.debug(f"Cache hit: {key}")
                    return entry.data
                else:
                    del self._store[key]
        return None

    def set(self, key: str, data: Any):
        """设置缓存"""
        with self._lock:
            self._store[key] = CacheEntry(timestamp=time(), data=data)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._store.clear()
            logging.info("Cache cleared")

    def cleanup(self, max_age: float):
        """清理过期缓存"""
        with self._lock:
            current_time = time()
            expired_keys = [
                k for k, v in self._store.items()
                if current_time - v.timestamp > max_age
            ]
            for k in expired_keys:
                del self._store[k]
            if expired_keys:
                logging.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# ================== 短信管理器 ==================

class SmsManager:
    """短信验证码管理器"""
    
    def __init__(self):
        self._waiting_states: Dict[str, SmsWaitingState] = {}
        self._lock = threading.Lock()

    def set_waiting(self, phone: str):
        """设置等待验证码状态"""
        with self._lock:
            self._waiting_states[phone] = SmsWaitingState(
                waiting=True,
                code=None,
                send_time=time()
            )

    def set_code(self, phone: str, code: str) -> bool:
        """设置验证码"""
        with self._lock:
            if phone in self._waiting_states and self._waiting_states[phone].waiting:
                self._waiting_states[phone].code = code
                self._waiting_states[phone].received_time = time()
                return True
        return False

    def get_code(self, phone: str) -> Optional[str]:
        """获取验证码"""
        with self._lock:
            if phone in self._waiting_states:
                return self._waiting_states[phone].code
        return None

    def wait_for_code(self, phone: str, timeout: float = 60) -> Optional[str]:
        """等待验证码"""
        start_time = time()
        while time() - start_time < timeout: 
            code = self.get_code(phone)
            if code:
                return code
            threading.Event().wait(1)
        return None

    def clear_state(self, phone: str):
        """清除等待状态"""
        with self._lock:
            if phone in self._waiting_states:
                del self._waiting_states[phone]

    def stop_waiting(self, phone: str):
        """停止等待"""
        with self._lock:
            if phone in self._waiting_states:
                self._waiting_states[phone].waiting = False


# ================== 自动重登录管理器 ==================

class AutoReloginManager: 
    """自动重登录管理器"""
    
    def __init__(self, user_manager: UserManager, sms_manager: SmsManager,
                 config_manager: ConfigManager, cache_manager: CacheManager, max_retry: int):
        self.user_manager = user_manager
        self.sms_manager = sms_manager
        self.config_manager = config_manager
        self.cache_manager = cache_manager
        self.max_retry = max_retry

    def relogin(self, user: User) -> bool:
        """执行自动重登录"""
        try:
            phone = user.phone
            user_api = user.api
            
            logging.info(f"Starting auto-relogin for user {phone}")
            
            for attempt in range(self.max_retry):
                try:
                    logging.info(f"Auto-relogin attempt {attempt + 1}/{self.max_retry} for {phone}")
                    
                    # 发送验证码
                    user_api.send_sms_code(phone)
                    logging.info(f"SMS code sent to {phone}")
                    
                    # 设置等待状态
                    self.sms_manager.set_waiting(phone)
                    
                    # 等待验证码
                    code = self.sms_manager.wait_for_code(phone, timeout=60)
                    
                    if not code:
                        logging.warning(f"No SMS code received within 60s for {phone}, attempt {attempt + 1}")
                        continue
                    
                    # 尝试登录
                    logging.info(f"Attempting login with received code for {phone}")
                    data = user_api.login(phone, code)
                    token = data.get('sessionId')
                    
                    if not token:
                        logging.error(f"Login failed for {phone}: no sessionId returned")
                        continue
                    
                    # 登录成功，更新用户信息
                    user_api.token = token
                    user_info = user_api.get_user_info()
                    community_info = user_api.get_community_info()
                    all_door = {}
                    
                    for community in community_info:
                        community_id = community['communityId']
                        all_door[community_id] = user_api.get_all_door_info(community_id)
                    
                    self.user_manager.update_or_create_user(
                        phone=phone,
                        token=token,
                        device=user_api.device.to_dict(),
                        user_info=user_info,
                        community_info=community_info,
                        all_door=all_door,
                        user_api=user_api
                    )
                    
                    self.config_manager.save(self.user_manager.config)
                    user.is_online = True
                    
                    logging.info(f"Auto-relogin successful for {phone}")
                    
                    # 清理缓存和等待状态
                    self.cache_manager.clear()
                    self.sms_manager.clear_state(phone)
                    
                    return True
                    
                except Exception as e: 
                    logging.exception(f"Auto-relogin attempt {attempt + 1} failed for {phone}: {e}")
                    continue
            
            # 所有重试都失败
            logging.error(f"Auto-relogin failed for {phone} after {self.max_retry} attempts")
            self.sms_manager.stop_waiting(phone)
            
            return False
            
        except Exception as e:
            logging.exception(f"Critical error in auto_relogin: {e}")
            return False


# ================== 定时任务管理器 ==================

class SchedulerManager:
    """定时任务管理器"""
    
    def __init__(self, user_manager: UserManager, relogin_manager: AutoReloginManager):
        self.user_manager = user_manager
        self.relogin_manager = relogin_manager

    def check_login_task(self):
        """检查用户登录状态"""
        for user in self.user_manager.users:
            try:
                if not user.is_online:
                    continue
                
                if user.api.check_login() > 0:
                    user.is_online = True
                else:
                    user.is_online = False
                    
                    # 检查是否启用自动重登
                    if not user.auto_relogin_enabled:
                        logging.info(f"User {user.phone} login expired but auto-relogin is disabled")
                        continue
                    
                    logging.warning(f"User {user.phone} login expired, starting auto-relogin")
                    # 在新线程中执行自动重登
                    threading.Thread(
                        target=self.relogin_manager.relogin,
                        args=(user,),
                        daemon=True
                    ).start()
                    
            except Exception as e:
                user.is_online = False
                logging.exception(f"Check login failed for {user.phone}: {e}")

    def check_users_on_startup(self):
        """启动时检查用户登录状态"""
        logging.info("Checking user login status on startup")
        for user in self.user_manager.users:
            if not user.is_online:
                if not user.auto_relogin_enabled:
                    logging.info(f"User {user.phone} is offline but auto-relogin is disabled")
                    continue
                
                logging.warning(f"User {user.phone} is offline on startup, starting auto-relogin")
                try:
                    threading.Thread(
                        target=self.relogin_manager.relogin,
                        args=(user,),
                        daemon=True
                    ).start()
                except Exception as e:
                    logging.exception(f"Failed to start auto-relogin thread for {user.phone}: {e}")
            else:
                logging.info(f"User {user.phone} is online")

    def start_scheduler(self):
        """启动定时任务"""
        scheduler = BlockingScheduler()
        scheduler.add_job(self.check_login_task, 'interval', seconds=60)
        scheduler.start()


# ================== Flask应用 ==================

class QinlinApp:
    """亲邻应用主类"""
    
    def __init__(self):
        # 初始化各个管理器
        self.config_manager = ConfigManager(CONFIG_FILE)
        self.config = self.config_manager.load()
        self.user_manager = UserManager(self.config)
        self.cache_manager = CacheManager()
        self.sms_manager = SmsManager()
        self.relogin_manager = AutoReloginManager(
            self.user_manager,
            self.sms_manager,
            self.config_manager,
            self.cache_manager,
            self.config.auto_relogin_retry
        )
        self.scheduler_manager = SchedulerManager(self.user_manager, self.relogin_manager)
        
        # 初始化Flask应用
        self.app = Flask(__name__)
        self._register_routes()
        self._register_error_handlers()

    def _create_response(self, code: int, message: str, data: Any = None) -> tuple:
        """创建响应"""
        response = ApiResponse(code=code, message=message, data=data)
        return jsonify(response.to_dict()), code if code >= 400 else 200

    def _cache_response(self, timeout: int = 5):
        """缓存装饰器"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                cache_key = f"{f.__name__}:{str(request.args)}"
                
                # 检查缓存
                cached_data = self.cache_manager.get(cache_key, timeout)
                if cached_data is not None:
                    return cached_data
                
                # 执行原函数
                result = f(*args, **kwargs)
                
                # 存储缓存
                self.cache_manager.set(cache_key, result)
                self.cache_manager.cleanup(timeout)
                
                return result
            return decorated_function
        return decorator

    def _check_access_token(self):
        """检查访问令牌"""
        # 排除静态资源
        if request.path.startswith('/static'):
            return None
        
        token = None
        if request.path.startswith('/token:'):
            token = request.path.split(':')[1]
        else:
            token = request.args.get('token')
        
        if not token or token != self.config.access_token:
            return self._create_response(ResponseCode.UNAUTHORIZED.value, "未授权访问")
        
        return None

    def _register_error_handlers(self):
        """注册错误处理器"""
        @self.app.errorhandler(Exception)
        def server_error(error):
            logging.exception(error)
            return self._create_response(ResponseCode.SERVER_ERROR.value, str(error))

    def _register_routes(self):
        """注册路由"""
        
        # 注册中间件
        self.app.before_request(self._check_access_token)
        
        # ========== 页面路由 ==========
        
        @self.app.route('/')
        def index():
            return render_template('index.html', token=self.config.access_token)

        @self.app.route('/token:<value>')
        def index_with_token(value):
            return render_template('index.html', token=self.config.access_token)

        @self.app.route('/manifest.json')
        def send_manifest():
            with open('static/manifest.json', 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            manifest['start_url'] = f"/token:{self.config.access_token}"
            return jsonify(manifest)
        
        @self.app.route('/sw.js')
        def send_service_worker():
            with open('static/js/sw.js', 'r', encoding='utf-8') as f:
                sw_content = f.read()
            sw_content = re.sub(r'{{token}}', self.config.access_token, sw_content)
            response = self.app.response_class(
                response=sw_content,
                status=200,
                mimetype='application/javascript'
            )
            return response

        @self.app.route('/static/<path:path>')
        def send_static(path):
            return send_from_directory('static', path)

        # ========== API路由 ==========
        
        @self.app.route('/get_all_users', methods=['GET'])
        def get_all_users():
            data = self.user_manager.get_all_users_data()
            return self._create_response(ResponseCode.SUCCESS.value, "success", data)

        @self.app.route('/open_door', methods=['GET'])
        def open_door():
            user_id = request.args.get("user_id")
            door_id = request.args.get("door_id")
            community_id = request.args.get("community_id")
            
            if not all([door_id, community_id, user_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide door_id and community_id and user_id"
                )
            
            user_api = self.user_manager.get_user_api(int(user_id))
            if not user_api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = user_api.open_door(int(community_id), int(door_id))
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/send_sms_code', methods=['GET'])
        def send_sms_code():
            user_id = request.args.get("user_id", -1)
            phone = request.args.get("phone")
            
            if not phone:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")

            user = self.user_manager.get_user(int(user_id), phone)
            
            if not user:
                # 创建新用户
                device = qinlinAPI.Device.get_default()
                user_api = qinlinAPI.QinlinAPI(device)
                user_id = self.user_manager.users[-1].index + 1 if self.user_manager.users else 0
                
                user = self.user_manager.update_or_create_user(
                    phone=phone,
                    token='',
                    device=device.to_dict(),
                    user_info={},
                    community_info=[],
                    all_door={},
                    user_api=user_api
                )
            else:
                user_api = user.api
                user_id = user.index

            result = user_api.send_sms_code(phone)
            return self._create_response(ResponseCode.SUCCESS.value, "success", {
                "index": user_id,
                "data": result
            })

        @self.app.route('/login', methods=['GET'])
        def login():
            phone = request.args.get("phone")
            code = request.args.get("code")
            user_id = request.args.get("user_id")
            
            if not all([phone, code, user_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide phone and code and user_id"
                )
            
            user = self.user_manager.get_user(int(user_id), phone)
            if not user:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            user_api = user.api
            data = user_api.login(phone, code)
            token = data.get('sessionId')
            
            if not token: 
                return self._create_response(ResponseCode.SERVER_ERROR.value, "Login failed")
            
            user_api.token = token
            user_info = user_api.get_user_info()
            community_info = user_api.get_community_info()
            all_door = {}
            
            for community in community_info: 
                community_id = community['communityId']
                all_door[community_id] = user_api.get_all_door_info(community_id)
            
            self.user_manager.update_or_create_user(
                phone=phone,
                token=token,
                device=user_api.device.to_dict(),
                user_info=user_info,
                community_info=community_info,
                all_door=all_door,
                user_api=user_api
            )
            
            self.config_manager.save(self.user_manager.config)
            self.cache_manager.clear()
            
            return self._create_response(ResponseCode.SUCCESS.value, "success", data)

        @self.app.route('/get_user_info', methods=['GET'])
        def get_user_info():
            user_id = request.args.get('user_id')
            if not user_id:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide user_id")
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.get_user_info()
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_community_info', methods=['GET'])
        def get_community_info():
            user_id = request.args.get('user_id')
            if not user_id:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide user_id")
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.get_community_info()
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_all_door_info', methods=['GET'])
        def get_all_door_info():
            user_id = request.args.get('user_id')
            community_id = request.args.get('community_id')
            
            if not all([community_id, user_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide community_id and user_id"
                )
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.get_all_door_info(int(community_id))
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_user_door_info', methods=['GET'])
        def get_user_door_info():
            user_id = request.args.get('user_id')
            community_id = request.args.get('community_id')
            
            if not all([community_id, user_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide community_id and user_id"
                )
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.get_user_door_info(int(community_id))
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_user_community_expiry_status', methods=['GET'])
        def get_user_community_expiry_status():
            user_id = request.args.get('user_id')
            community_id = request.args.get('community_id')
            
            if not all([community_id, user_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide community_id and user_id"
                )
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api: 
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.get_user_community_expiry_status(int(community_id))
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_support_password_devices', methods=['GET'])
        @self._cache_response(3600 * 6)  # 缓存6小时
        def get_support_password_devices():
            result = qinlinAPI.QinlinAPI.get_support_password_devices()
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/check_login', methods=['GET'])
        def check_login():
            user_id = request.args.get('user_id')
            if not user_id:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide user_id")
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.check_login()
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/logout', methods=['GET'])
        def logout():
            user_id = request.args.get('user_id')
            if not user_id:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide user_id")
            
            api = self.user_manager.get_user_api(int(user_id))
            if not api:
                return self._create_response(ResponseCode.NOT_FOUND.value, "User not found")
            
            result = api.logout()
            return self._create_response(ResponseCode.SUCCESS.value, "success", result)

        @self.app.route('/get_door_paddword', methods=['GET'])
        def get_door_password():
            mac = request.args.get('mac')
            community_id = request.args.get('community_id')
            
            if not all([mac, community_id]):
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Please provide mac and community_id"
                )
            
            password = qinlinAPI.QinlinCrypto.get_open_door_password(mac, int(community_id))
            return self._create_response(ResponseCode.SUCCESS.value, "success", {
                "password": password
            })

        @self.app.route('/receive_sms', methods=['POST', 'GET'])
        def receive_sms():
            """接收短信验证码"""
            if request.method == 'POST':
                data = request.get_json(force=True, silent=True)
                if not data:
                    return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide JSON data")
                phone = data.get('phone')
                content = data.get('content')
            else:
                phone = request.args.get('phone')
                content = request.args.get('content')
            
            if not phone: 
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone parameter")
            
            if not content:
                return self._create_response(ResponseCode.BAD_REQUEST.value, "Please provide content parameter")
            
            logging.info(f"Received SMS for phone: {phone}, content: {content}")
            
            # 提取验证码
            match = re.search(r'验证码是[：:]\s*(\d{6})', content)
            if not match:
                return self._create_response(
                    ResponseCode.BAD_REQUEST.value,
                    "Cannot extract verification code from SMS content"
                )
            
            code = match.group(1)
            logging.info(f"Received SMS code: {code} for phone: {phone}")
            
            # 设置验证码
            if self.sms_manager.set_code(phone, code):
                return self._create_response(ResponseCode.SUCCESS.value, "success", {
                    "phone": phone,
                    "code": code,
                    "message": "Verification code received and will be used for auto-login"
                })
            else:
                return self._create_response(
                    ResponseCode.NOT_FOUND.value,
                    f"No user with phone {phone} is waiting for verification code"
                )

    def run(self):
        """运行应用"""
        logging.info(f'Access token: {self.config.access_token}')
        
        # 启动时检查用户登录状态
        self.scheduler_manager.check_users_on_startup()
        
        # 启动定时任务
        threading.Thread(target=self.scheduler_manager.start_scheduler, daemon=True).start()
        
        # 运行Flask应用
        self.app.run(host=HOST, port=PORT, debug=DEBUG)


# ================== 主程序入口 ==================

if __name__ == "__main__":
    app = QinlinApp()
    app.run()