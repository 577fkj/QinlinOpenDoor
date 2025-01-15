from flask import Flask, jsonify, request, render_template, send_from_directory
import qinlinAPI
import json
import os
from functools import wraps
from time import time
import threading
from apscheduler.schedulers.blocking import BlockingScheduler

host = os.getenv('HOST', '0.0.0.0')
port = os.getenv('PORT', 5000)
debug = os.getenv('DEBUG', True)

CONFIG_FILE = 'config/config.json'

if not os.path.exists('config'):
    os.makedirs('config')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    data = {
        'user': {},
        'access_token': 'your-secure-token-here',  # 添加访问token
    }
    save_config(data)
    return data

def save_config(conf):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(conf, f, indent=4)

# 加载配置
config = load_config()

users = []
waiting_users = []

def load_users():
    idx = 0
    for key, value in config['user'].items():
        # 初始化设备和API
        device = qinlinAPI.Device.load_from_dict(value['device'])

        ql_api = qinlinAPI.QinlinAPI(device)
        if value.get('token'):
            ql_api.token = value['token']

        user_info = ql_api.get_user_info()
        community_info = ql_api.get_community_info()
        all_door = {}
        for community in community_info:
            community_id = community['communityId']
            all_door[community_id] = ql_api.get_all_door_info(community_id)

        config['user'][key]['user_info'] = user_info

        users.append({
            'index': idx,
            'phone': key,
            'user_info': user_info,
            'community_info': community_info,
            'all_door': all_door,
            'is_online': True,
            'api': ql_api
        })
        idx += 1

load_users()

save_config(config)

print(f'users = {users}')

app = Flask(__name__)

def update_user(idx, data):
    print(f"update_user: {idx}, {data}")
    for user in users:
        if user['phone'] == data['phone']:
            user['phone'] = data['phone']
            user['user_info'] = data['user_info']
            user['community_info'] = data['community_info']
            user['all_door'] = data['all_door']
            user['is_online'] = True
            user['api'] = data['api']

            config['user'][user['phone']]['user_info'] = data['user_info']
            config['user'][user['phone']]['token'] = data['token']
            config['user'][user['phone']]['device'] = data['device']
            break
    users.append({
        'index': idx,
        'phone': data['phone'],
        'user_info': data['user_info'],
        'community_info': data['community_info'],
        'all_door': data['all_door'],
        'is_online': True,
        'api': data['api']
    })

    config['user'][data['phone']] = {
        'token': data['token'],
        'device': data['device'],
        'user_info': data['user_info']
    }

def get_user_api(idx):
    for user in users:
        if user['index'] == idx:
            return user['api']
    return None

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
    
    if request.path.startswith('/token:'):
        token = request.path.split(':')[1]
    else:
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
    return render_template('index.html', token=config['access_token'])

@app.route('/token:<value>')
def index_with_token(value):
    return render_template('index.html', token=config['access_token'])

@app.route('/manifest.json')
def send_manifest():
    with open('static/manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    manifest['start_url'] = f"/token:{config['access_token']}"
    return jsonify(manifest)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
    new_data = []
    for user in users:
        new_data.append({
            'index': user['index'],
            'phone': user['phone'],
            'user_info': user['user_info'],
            'community_info': user['community_info'],
            'is_online': user['is_online'],
            'all_door': user['all_door']
        })
    return response(200, "success", new_data)

@app.route('/open_door', methods=['GET'])
def open_door():
    user_id = request.args.get("user_id")
    door_id = request.args.get("door_id")
    community_id = request.args.get("community_id")
    if not door_id or not community_id or not user_id:
        return response(500, "Please provide door_id and community_id and user_id")
    user_api = get_user_api(int(user_id))
    if not user_api:
        return response(500, "User not found")
    return response(200, "success", user_api.open_door(int(community_id), int(door_id)))

@app.route('/send_sms_code', methods=['GET'])
def send_sms_code():
    user_id = request.args.get("user_id")
    phone = request.args.get("phone")
    if not user_id:
        user_id = -1
    if not phone:
        return response(500, "Please provide phone")
    user_api = get_user_api(int(user_id))
    if not user_api:
        device = qinlinAPI.Device.get_default()
        user_api = qinlinAPI.QinlinAPI(device)
        user_id = len(waiting_users)
        waiting_users.append({
            'index': user_id,
            'phone': phone,
            'api': user_api
        })
    return response(200, "success", {
        "index": user_id,
        "data": user_api.send_sms_code(phone)
    })

@app.route('/login', methods=['GET'])
def login():
    try:
        user_id = request.args.get("user_id")
        phone = request.args.get("phone")
        code = request.args.get("code")
        if not phone or not code or not user_id:
            return response(500, "Please provide phone and code")
        user_api = get_user_api(int(user_id))
        if not user_api:
            user_api = waiting_users[int(user_id)]['api']
            user_id = users[-1]['index'] + 1
        data = user_api.login(phone, code)
        token = data.get('sessionId')
        if not token:
            return response(500, "Login failed")
        user_api.token = token

        user_info = user_api.get_user_info()
        community_info = user_api.get_community_info()
        all_door = {}
        for community in community_info:
            community_id = community['communityId']
            all_door[community_id] = user_api.get_all_door_info(community_id)
        update_user(int(user_id), {
            'token': token,
            'phone': phone,
            'user_info': user_info,
            'community_info': community_info,
            'all_door': all_door,
            'api': user_api,
            'device': user_api.device.to_dict()
        })
        save_config(config)

        with cache_lock:
            cache_store.clear()
    except Exception as e:
        import logging
        logging.exception(e)

    return response(200, "success", data)

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    user_id = request.args.get('user_id')
    if not user_id:
        return response(500, "Please provide user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.get_user_info())

@app.route('/get_community_info', methods=['GET'])
def get_community_info():
    user_id = request.args.get('user_id')
    if not user_id:
        return response(500, "Please provide user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.get_community_info())

@app.route('/get_all_door_info', methods=['GET'])
def get_all_door_info():
    user_id = request.args.get('user_id')
    community_id = request.args.get('community_id')
    if not community_id or not user_id:
        return response(500, "Please provide community_id and user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.get_all_door_info(int(community_id)))

@app.route('/get_user_door_info', methods=['GET'])
def get_user_door_info():
    user_id = request.args.get('user_id')
    community_id = request.args.get('community_id')
    if not community_id or not user_id:
        return response(500, "Please provide community_id and user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.get_user_door_info(int(community_id)))

@app.route('/get_user_community_expiry_status', methods=['GET'])
def get_user_community_expiry_status():
    user_id = request.args.get('user_id')
    community_id = request.args.get('community_id')
    if not community_id or not user_id:
        return response(500, "Please provide community_id and user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.get_user_community_expiry_status(int(community_id)))

@app.route('/get_support_password_devices', methods=['GET'])
@cache_response(3600 * 6) # 缓存6小时
def get_support_password_devices():
    return response(200, "success", qinlinAPI.QinlinAPI.get_support_password_devices())

@app.route('/check_login', methods=['GET'])
def check_login():
    user_id = request.args.get('user_id')
    if not user_id:
        return response(500, "Please provide user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.check_login())

@app.route('/logout', methods=['GET'])
def logout():
    user_id = request.args.get('user_id')
    if not user_id:
        return response(500, "Please provide user_id")
    api = get_user_api(int(user_id))
    return response(200, "success", api.logout())

@app.route('/get_door_paddword', methods=['GET'])
def get_door_paddword():
    mac = request.args.get('mac')
    community_id = request.args.get('community_id')
    if not mac or not community_id:
        return response(500, "Please provide mac and community_id")
    return response(200, "success", {
        "password": qinlinAPI.QinlinCrypto.get_open_door_password(mac, int(community_id))
    })

def check_login_task():
    for user in users:
        user_api = user['api']
        try:
            if user_api.check_login() > 0:
                user['is_online'] = True
            else:
                user['is_online'] = False
        except Exception as e:
            user['is_online'] = False
            print(f"Check login failed: {e}")

def start_task():
    scheduler = BlockingScheduler()
    scheduler.add_job(check_login_task, 'interval', seconds=60)
    scheduler.start()

if __name__ == "__main__":
    print(f'token = {config["access_token"]}')

    threading.Thread(target=start_task).start()

    app.run(
        host=host,
        port=port,
        debug=debug
    )
