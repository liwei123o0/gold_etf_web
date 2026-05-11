"""
认证 API 路由模块

提供用户认证相关的接口，包括注册、登录、登出、获取当前用户信息。
所有接口路径前缀为 /api/auth。
"""

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from backend.services.auth import AuthService

# 创建认证蓝图，URL 前缀为 /api/auth
bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
def register():
    """
    用户注册接口

    请求方式：POST
    请求路径：/api/auth/register

    请求参数（JSON Body）：
        username (str): 用户名，不能为空
        password (str): 密码，不能为空

    返回值（JSON）：
        成功：{"success": True, "user": {用户信息字典}}
        失败：{"success": False, "error": "错误信息"}，HTTP 400
    """
    # 从请求体获取 JSON 数据，若无则使用空字典
    data = request.get_json() or {}
    # 提取并清理用户名（去除首尾空格）
    username = data.get('username', '').strip()
    # 提取密码
    password = data.get('password', '')

    # 调用认证服务进行注册
    success, result = AuthService.register(username, password)
    if not success:
        # 注册失败，返回错误信息和 400 状态码
        return jsonify({'success': False, 'error': result}), 400

    # 注册成功，自动登录用户（记住登录状态）
    login_user(result, remember=True)
    return jsonify({'success': True, 'user': result.to_dict()})


@bp.route('/login', methods=['POST'])
def login():
    """
    用户登录接口

    请求方式：POST
    请求路径：/api/auth/login

    请求参数（JSON Body）：
        username (str): 用户名
        password (str): 密码

    返回值（JSON）：
        成功：{"success": True, "user": {用户信息字典}}
        失败：{"success": False, "error": "错误信息"}，HTTP 401
    """
    # 从请求体获取 JSON 数据
    data = request.get_json() or {}
    # 提取并清理用户名
    username = data.get('username', '').strip()
    # 提取密码
    password = data.get('password', '')

    # 调用认证服务进行身份验证
    success, result = AuthService.authenticate(username, password)
    if not success:
        # 认证失败，返回错误信息和 401 状态码
        return jsonify({'success': False, 'error': result}), 401

    # 认证成功，登录用户（记住登录状态）
    login_user(result, remember=True)
    return jsonify({'success': True, 'user': result.to_dict()})


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    用户登出接口

    请求方式：POST
    请求路径：/api/auth/logout

    请求参数：无

    返回值（JSON）：
        {"success": True}

    注意：需要用户已登录（@login_required 装饰器保护）
    """
    # 调用 Flask-Login 的登出方法，清除用户会话
    logout_user()
    return jsonify({'success': True})


@bp.route('/me', methods=['GET'])
def me():
    """
    获取当前登录用户信息接口

    请求方式：GET
    请求路径：/api/auth/me

    请求参数：无

    返回值（JSON）：
        已登录：{"success": True, "user": {用户信息字典}}
        未登录：{"success": True, "user": None}

    注意：此接口不需要登录即可访问，未登录时 user 为 null
    """
    # 检查用户是否已通过认证
    if current_user.is_authenticated:
        # 已登录，返回用户信息
        return jsonify({'success': True, 'user': current_user.to_dict()})
    # 未登录，返回 user 为 None
    return jsonify({'success': True, 'user': None})
