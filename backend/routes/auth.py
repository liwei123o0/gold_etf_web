"""
认证 API 路由

提供 /api/auth/* 接口：注册、登录、登出、当前用户
"""

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from backend.services.auth import AuthService

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    注册新用户
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    success, result = AuthService.register(username, password)
    if not success:
        return jsonify({'success': False, 'error': result}), 400

    login_user(result, remember=True)
    return jsonify({'success': True, 'user': result.to_dict()})


@bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    用户登录
    """
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    success, result = AuthService.authenticate(username, password)
    if not success:
        return jsonify({'success': False, 'error': result}), 401

    login_user(result, remember=True)
    return jsonify({'success': True, 'user': result.to_dict()})


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    POST /api/auth/logout
    用户登出
    """
    logout_user()
    return jsonify({'success': True})


@bp.route('/me', methods=['GET'])
def me():
    """
    GET /api/auth/me
    返回当前登录用户信息，未登录返回 null
    """
    if current_user.is_authenticated:
        return jsonify({'success': True, 'user': current_user.to_dict()})
    return jsonify({'success': True, 'user': None})
