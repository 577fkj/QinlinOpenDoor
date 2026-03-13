import os
import json
import re
import logging
from quart import Quart, Blueprint, render_template, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from .api.routes import api_bp
from .api.dependencies import AppState
from .core.config import ConfigManager
from .core.cache import CacheManager
from .services.user_service import UserService
from .services.sms_service import SmsService
from .services.auth_service import AuthService
from .services.scheduler_service import SchedulerService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def create_app() -> Quart:
    app = Quart(__name__, template_folder='../templates', static_folder='../static')
    
    # 配置反向代理支持
    app.asgi_app = ProxyFix(app.asgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    app.state = AppState()
    
    # 创建主 Blueprint，包含所有需要 token 的路由
    token_bp = Blueprint('token', __name__)
    
    @token_bp.route('', strict_slashes=False)
    @token_bp.route('/')
    @token_bp.route('/index.html')
    async def index():
        return await render_template('index.html', token=app.state.access_token)
    
    @token_bp.route('/manifest.json')
    async def send_manifest():
        with open('static/manifest.json', 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        manifest['start_url'] = f"/{app.state.access_token}/"
        return jsonify(manifest)
    
    @token_bp.route('/sw.js')
    async def send_service_worker():
        with open('static/js/sw.js', 'r', encoding='utf-8') as f:
            sw_content = f.read()
        sw_content = re.sub(r'{{token}}', app.state.access_token, sw_content)
        response = await app.make_response(sw_content)
        response.headers['Content-Type'] = 'application/javascript'
        return response

    # 静态文件路由
    @token_bp.route('/static/<path:path>')
    async def send_static(path):
        return await send_from_directory('static', path)
    
    # 注册 API Blueprint 到 token_bp
    token_bp.register_blueprint(api_bp, url_prefix='/api')

    @app.before_serving
    async def initialize():
        config_manager = await ConfigManager.create()
        cache_manager = CacheManager()
        
        config = config_manager.config
        
        user_service = await UserService.create(config_manager)
        sms_service = SmsService()
        auth_service = AuthService(user_service, sms_service, config.auto_relogin_retry)
        scheduler_service = SchedulerService(user_service, auth_service)
        
        app.state.config_manager = config_manager
        app.state.cache_manager = cache_manager
        app.state.user_service = user_service
        app.state.sms_service = sms_service
        app.state.auth_service = auth_service
        app.state.scheduler_service = scheduler_service
        app.state.access_token = config.access_token
        
        logger.info(f'Access token: {config.access_token}')
        
        # 挂载整个 token_bp 到 /<token> 路径
        app.register_blueprint(token_bp, url_prefix=f'/{app.state.access_token}')
        
        await scheduler_service.check_users_on_startup()
        scheduler_service.start()
    
    @app.errorhandler(Exception)
    async def handle_error(error):
        logger.exception(error)
        return jsonify({
            'code': 500,
            'message': str(error),
            'data': None
        }), 200
    
    return app
