import re
import json
import logging
from datetime import datetime
from functools import wraps
from quart import Blueprint, request, jsonify, render_template, send_from_directory

from ..models.response import ApiResponse, ResponseCode
from ..models.device import Device
from ..models.user import UserData
from ..qinlin.client import QinlinClient
from ..core.security import Crypto
from ..core.config import GeoFence
from .dependencies import get_app_state

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


def create_response(code: int, message: str, data=None):
    response = ApiResponse(code=code, message=message, data=data)
    return jsonify(response.to_dict()), code if code >= 400 else 200


@api_bp.route('/get_amap_key', methods=['GET'])
async def get_amap_key():
    """获取高德地图Key（优先环境变量，其次配置文件）"""
    import os
    key = os.environ.get('AMAP_KEY', '')
    if not key:
        state = get_app_state()
        key = state.config_manager.config.amap_key or ''
    return create_response(ResponseCode.SUCCESS.value, "success", key)


@api_bp.route('/get_all_users', methods=['GET'])
async def get_all_users():
    state = get_app_state()
    data = await state.user_service.get_all_users_data()
    return create_response(ResponseCode.SUCCESS.value, "success", data)


@api_bp.route('/update_auto_relogin', methods=['POST'])
async def update_auto_relogin():
    data = await request.get_json()
    phone = data.get('phone')
    enabled = data.get('enabled')
    
    if phone is None or enabled is None:
        return create_response(ResponseCode.BAD_REQUEST.value, "Missing parameters")
    
    state = get_app_state()
    success = await state.user_service.update_auto_relogin(phone, enabled)
    
    if not success:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    return create_response(ResponseCode.SUCCESS.value, "success")


@api_bp.route('/open_door', methods=['GET'])
async def open_door():
    phone = request.args.get("phone")
    door_id = request.args.get("door_id")
    community_id = request.args.get("community_id")
    
    if not all([door_id, community_id, phone]):
        return create_response(
            ResponseCode.BAD_REQUEST.value,
            "Please provide door_id, community_id and user_id"
        )
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")

    result = await user.api.open_door(int(community_id), int(door_id))
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/send_sms_code', methods=['GET'])
async def send_sms_code():
    phone = request.args.get("phone")
    
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    
    if not user:
        device = Device()
        
        user = await state.user_service.update_user(
            phone=phone,
            token='',
            device=device
        )
    result = {}
    try:
        result['success'] = await user.api.send_sms_code(phone)
        result['message'] = "SMS code sent successfully" if result['success'] else "Failed to send SMS code"
        await state.sms_service.set_waiting(phone)
    except Exception as e:
        logger.exception(f"Error sending SMS code to {phone}: {e}")
        result['success'] = False
        result['message'] = f"Error sending SMS code: {str(e)}"
    
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/get_sms_code', methods=['GET'])
async def get_sms_code():
    phone = request.args.get("phone")
    
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    code = await state.sms_service.get_code(user.phone)
    if code:
        await state.sms_service.clear_state(user.phone)
    
    return create_response(ResponseCode.SUCCESS.value, "success", {
        "code": code,
        "login_success": user.is_online
    })


@api_bp.route('/login', methods=['GET'])
async def login():
    code = request.args.get("code")
    phone = request.args.get("phone")
    
    if not all([phone, code, phone]):
        return create_response(
            ResponseCode.BAD_REQUEST.value,
            "Please provide phone, code and phone"
        )
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    try:
        await state.user_service.update_user(phone=phone, token='')
        
        login_response = await user.api.login(phone, code)
        token = login_response.session_id
        
        if not token:
            return create_response(ResponseCode.SERVER_ERROR.value, "Login failed")
        
        await state.user_service.update_user(
            phone=phone,
            token=token
        )
        return create_response(ResponseCode.SUCCESS.value, "success", True)
        
    except Exception as e:
        logger.exception(f"Login error: {e}")
        return create_response(ResponseCode.SERVER_ERROR.value, str(e))


@api_bp.route('/get_user_info', methods=['GET'])
async def get_user_info():
    phone = request.args.get('phone')
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    return create_response(ResponseCode.SUCCESS.value, "success", user.user.data.to_dict())


@api_bp.route('/get_community_info', methods=['GET'])
async def get_community_info():
    phone = request.args.get('phone')
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    return create_response(ResponseCode.SUCCESS.value, "success", [c.to_dict() for c in user.user.data.communities])


@api_bp.route('/get_all_door_info', methods=['GET'])
async def get_all_door_info():
    phone = request.args.get('phone')
    community_id = request.args.get('community_id')
    
    if not all([community_id, phone]):
        return create_response(
            ResponseCode.BAD_REQUEST.value,
            "Please provide community_id and phone"
        )
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    return create_response(ResponseCode.SUCCESS.value, "success", [d.to_dict() for d in user.user.data.get_community_by_id(int(community_id)).doors])

@api_bp.route('/get_support_password_devices', methods=['GET'])
async def get_support_password_devices():
    state = get_app_state()
    cache_key = 'support_password_devices'
    
    cached = await state.cache_manager.get(cache_key, 3600 * 6)
    if cached is not None:
        return create_response(ResponseCode.SUCCESS.value, "success", cached)
    
    result = await QinlinClient.get_support_password_devices()
    await state.cache_manager.set(cache_key, result)
    
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/check_login', methods=['GET'])
async def check_login():
    phone = request.args.get('phone')
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    result = await user.api.check_login()
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/logout', methods=['GET'])
async def logout():
    phone = request.args.get('phone')
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    user = await state.user_service.get(phone)
    if not user:
        return create_response(ResponseCode.NOT_FOUND.value, "User not found")
    
    result = await user.api.logout()
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/get_favorites', methods=['GET'])
async def get_favorites():
    """获取用户的收藏门禁列表"""
    phone = request.args.get('phone')
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    state = get_app_state()
    favorites = state.config_manager.config.favorites.get(phone, [])
    return create_response(ResponseCode.SUCCESS.value, "success", favorites)


@api_bp.route('/save_favorites', methods=['POST'])
async def save_favorites():
    """保存用户的收藏门禁列表"""
    data = await request.get_json()
    phone = data.get('phone')
    favorites = data.get('favorites')
    
    if phone is None or favorites is None:
        return create_response(ResponseCode.BAD_REQUEST.value, "Missing parameters")
    
    if not isinstance(favorites, list):
        return create_response(ResponseCode.BAD_REQUEST.value, "favorites must be a list")
    
    state = get_app_state()
    state.config_manager.config.favorites[phone] = favorites
    await state.config_manager.save()
    
    return create_response(ResponseCode.SUCCESS.value, "success")


@api_bp.route('/get_door_paddword', methods=['GET'])
async def get_door_password():
    mac = request.args.get('mac')
    community_id = request.args.get('community_id')
    
    if not all([mac, community_id]):
        return create_response(
            ResponseCode.BAD_REQUEST.value,
            "Please provide mac and community_id"
        )
    
    password = Crypto.get_door_password(mac, int(community_id), datetime.now())
    return create_response(ResponseCode.SUCCESS.value, "success", {
        "password": password
    })


@api_bp.route('/receive_sms', methods=['POST', 'GET'])
async def receive_sms():
    if request.method == 'POST':
        data = await request.get_json(force=True, silent=True)
        if not data:
            return create_response(ResponseCode.BAD_REQUEST.value, "Please provide JSON data")
        phone = data.get('phone')
        content = data.get('content')
    else:
        phone = request.args.get('phone')
        content = request.args.get('content')
    
    if not phone:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide phone")
    
    if not content:
        return create_response(ResponseCode.BAD_REQUEST.value, "Please provide content")
    
    logger.info(f"Received SMS for phone: {phone}, content: {content}")
    
    match = re.search(r'验证码是[：:]\s*(\d{6})', content)
    if not match:
        return create_response(
            ResponseCode.BAD_REQUEST.value,
            "Cannot extract verification code"
        )
    
    code = match.group(1)
    logger.info(f"Extracted SMS code: {code} for phone: {phone}")
    
    state = get_app_state()
    sms_set = await state.sms_service.set_code(phone, code)
    
    if sms_set:
        return create_response(ResponseCode.SUCCESS.value, "success", {
            "phone": phone,
            "code": code,
            "message": "Verification code received"
        })
    else:
        return create_response(
            ResponseCode.NOT_FOUND.value,
            f"No user waiting for verification code"
        )


@api_bp.route('/get_geofences', methods=['GET'])
async def get_geofences():
    """获取所有电子围栏"""
    state = get_app_state()
    geofences = state.config_manager.config.geofences
    result = {}
    for phone, communities in geofences.items():
        result[phone] = {cid: fence.to_dict() for cid, fence in communities.items()}
    return create_response(ResponseCode.SUCCESS.value, "success", result)


@api_bp.route('/save_geofence', methods=['POST'])
async def save_geofence():
    """保存电子围栏"""
    data = await request.get_json()
    phone = data.get('phone')
    community_id = data.get('community_id')
    name = data.get('name', '')
    points = data.get('points')

    if not phone or not community_id or not isinstance(points, list):
        return create_response(ResponseCode.BAD_REQUEST.value, "Missing phone, community_id or points")

    state = get_app_state()
    fence = GeoFence(name=name, points=points)
    if phone not in state.config_manager.config.geofences:
        state.config_manager.config.geofences[phone] = {}
    state.config_manager.config.geofences[phone][str(community_id)] = fence
    await state.config_manager.save()

    return create_response(ResponseCode.SUCCESS.value, "success")


@api_bp.route('/delete_geofence', methods=['POST'])
async def delete_geofence():
    """删除电子围栏"""
    data = await request.get_json()
    phone = data.get('phone')
    community_id = data.get('community_id')

    if not phone or not community_id:
        return create_response(ResponseCode.BAD_REQUEST.value, "Missing phone or community_id")

    state = get_app_state()
    community_id = str(community_id)
    if phone in state.config_manager.config.geofences:
        if community_id in state.config_manager.config.geofences[phone]:
            del state.config_manager.config.geofences[phone][community_id]
            if not state.config_manager.config.geofences[phone]:
                del state.config_manager.config.geofences[phone]
            await state.config_manager.save()

    return create_response(ResponseCode.SUCCESS.value, "success")
