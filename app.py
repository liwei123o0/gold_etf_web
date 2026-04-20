"""
Flask 主入口文件

前后端分离架构：
- 后端（backend/）：提供纯 JSON API，不处理 HTML
- 前端（static/ + templates/）：静态资源 + HTML 模板，通过 JS 调用 API
"""

import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required
from backend import data_bp, news_bp, backtest_bp, realtime_bp, signaltime_bp
from backend.routes.auth import bp as auth_bp
from backend.models.user import init_db


def create_app():
    """
    Flask 应用工厂函数。

    Returns
    -------
    Flask
        配置好的 Flask 应用实例
    """
    app = Flask(__name__)

    # Flask-Login 配置
    app.secret_key = os.environ.get('SECRET_KEY', 'gold-etf-secret-key-change-in-production')
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.session_protection = 'strong'
    login_manager.login_view = 'login_page'

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect, url_for
        return redirect(url_for('login_page'))

    @login_manager.user_loader
    def load_user(user_id):
        from backend.models.user import User
        return User.find_by_id(int(user_id))

    # 初始化数据库
    init_db()

    # 注册 API 蓝图（前后端分离：后端只返回 JSON）
    app.register_blueprint(data_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(realtime_bp)
    app.register_blueprint(signaltime_bp)

    @app.route('/')
    def index():
        """
        根路径重定向到 /stock
        """
        from flask import redirect, url_for
        return redirect(url_for('stock_page'))

    @app.route('/auth/login')
    def login_page():
        return render_template('auth/login.html')

    @app.route('/auth/register')
    def register_page():
        return render_template('auth/register.html')

    @app.route('/stock')
    @login_required
    def stock_page():
        """股票搜索+技术分析页（GET表单提交）"""
        return render_template('stock.html')

    @app.route('/stock/<code>')
    def stock_page_redirect(code):
        """旧路径兼容重定向：/stock/CODE -> /stock?symbol=CODE"""
        from flask import redirect
        return redirect(f'/stock?symbol={code}')

    return app


# WSGI 入口（适用于 gunicorn / uwsgi / 生产环境）
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
