from flask import Flask, jsonify, request, render_template, send_from_directory
import qinlinAPI
import json
import os
from functools import wraps
from time import time
import threading

host = os.getenv('HOST', '0.0.0.0')
port = os.getenv('PORT', 5000)
debug = os.getenv('DEBUG', False)

CONFIG_FILE = 'config/config.json'

if not os.path.exists('config'):
    os.makedirs('config')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    data = {
        'device': {
            **qinlinAPI.Device.get_default().to_dict()
        },
        'token': None,
        'access_token': 'your-secure-token-here',  # 添加访问token
        'exclude_routes': ['/static']  # 排除静态资源
    }
    save_config(data)
    return data

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# 加载配置
config = load_config()

# 初始化设备和API
device = qinlinAPI.Device.load_from_dict(config['device'])

api = qinlinAPI.QinlinAPI(device)
if config.get('token'):
    api.token = config['token']

app = Flask(__name__)

def response(code=200, message='', data=None):
    """
    自定义返回结果的封装函数
    :param code: 状态码，默认为 200
    :param message: 提示信息，默认为空字符串
    :param data: 返回数据，默认为 None
    :return: Response 对象
    """
    response_data = {
        'code': code,
        'message': message,
        'data': data
    }
    return jsonify(response_data)

# 缓存存储
cache_store = {}
cache_lock = threading.Lock()

def cache_response(timeout=5):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{f.__name__}:{str(request.args)}"
            
            with cache_lock:
                # 检查缓存
                if cache_key in cache_store:
                    cached_time, cached_data = cache_store[cache_key]
                    if time() - cached_time < timeout:
                        print(f"Cache hit: {cache_key}")
                        return cached_data
                
                # 执行原函数
                result = f(*args, **kwargs)
                
                # 存储缓存
                cache_store[cache_key] = (time(), result)
                
                # 清理过期缓存
                current_time = time()
                expired_keys = [k for k, v in cache_store.items() 
                              if current_time - v[0] > timeout]
                for k in expired_keys:
                    del cache_store[k]
                    
                return result
        return decorated_function
    return decorator

@app.before_request
def check_access_token():
    # 排除静态资源
    if request.path.startswith('/static'):
        return None
        
    # 验证URL参数token
    token = request.args.get('token')
    if not token or token != config.get('access_token'):
        return response(401, "未授权访问")
    
    return None

@app.errorhandler(Exception)
def server_error(error):
    return response(500, str(error))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/open_door', methods=['GET'])
def open_door():
    door_id = request.args.get("door_id")
    community_id = request.args.get("community_id")
    if not door_id or not community_id:
        return response(500, "Please provide door_id and community_id")
    return response(200, "success", api.open_door(community_id, door_id))

@app.route('/send_sms_code', methods=['GET'])
def send_sms_code():
    phone = request.args.get("phone")
    return response(200, "success", api.send_sms_code(phone))

@app.route('/login', methods=['GET'])
def login():
    phone = request.args.get("phone")
    code = request.args.get("code")
    if not phone or not code:
        return response(500, "Please provide phone and code")
    data = api.login(phone, code)
    token = data.get('sessionId')
    api.token = token
    
    # 保存token到配置文件
    config['token'] = token
    save_config(config)

    with cache_lock:
        cache_store.clear()
    
    return response(200, "success", data)

@app.route('/get_user_info', methods=['GET'])
@cache_response(5)  # 5秒缓存
def get_user_info():
    return response(200, "success", api.get_user_info())

@app.route('/get_community_info', methods=['GET'])
@cache_response(10)  # 10秒缓存
def get_community_info():
    return response(200, "success", api.get_community_info())

@app.route('/get_all_door_info', methods=['GET'])
@cache_response(5)
def get_all_door_info():
    community_id = request.args.get('community_id')
    if not community_id:
        return response(500, "Please provide community_id")
    return response(200, "success", api.get_all_door_info(community_id))

@app.route('/get_user_door_info', methods=['GET'])
@cache_response(5)
def get_user_door_info():
    community_id = request.args.get('community_id')
    if not community_id:
        return response(500, "Please provide community_id")
    return response(200, "success", api.get_user_door_info(community_id))

@app.route('/get_user_community_expiry_status', methods=['GET'])
def get_user_community_expiry_status():
    community_id = request.args.get('community_id')
    if not community_id:
        return response(500, "Please provide community_id")
    return response(200, "success", api.get_user_community_expiry_status(community_id))

@app.route('/get_support_password_devices', methods=['GET'])
@cache_response(3600)
def get_support_password_devices():
    return response(200, "success", api.get_support_password_devices())

@app.route('/check_login', methods=['GET'])
@cache_response(5)
def check_login():
    return response(200, "success", api.check_login())

@app.route('/logout', methods=['GET'])
def logout():
    with cache_lock:
        cache_store.clear()
    return response(200, "success", api.logout())

@app.route('/get_door_paddword', methods=['GET'])
def get_door_paddword():
    mac = request.args.get('mac')
    community_id = request.args.get('community_id')
    if not mac or not community_id:
        return response(500, "Please provide mac and community_id")
    return response(200, "success", {
        "password": qinlinAPI.QinlinCrypto.get_open_door_password(mac, community_id)
    })

if __name__ == "__main__":
    print(f'token = {config["access_token"]}')
    app.run(
        host=host,
        port=port,
        debug=debug
    )
