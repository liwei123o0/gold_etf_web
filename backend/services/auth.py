"""
认证服务
封装用户注册、登录验证等业务逻辑
"""

from backend.models.user import User


class AuthService:
    """认证服务"""

    @staticmethod
    def register(username, password):
        """
        注册新用户

        Parameters
        ----------
        username : str
            用户名
        password : str
            密码

        Returns
        -------
        tuple
            (success: bool, user_or_error: User or str)
        """
        if not username or not password:
            return False, '用户名和密码不能为空'

        if len(username) < 3 or len(username) > 32:
            return False, '用户名长度需在3-32个字符之间'

        if len(password) < 6:
            return False, '密码长度不能少于6个字符'

        user = User.create(username, password)
        if user is None:
            return False, '用户名已存在'

        return True, user

    @staticmethod
    def authenticate(username, password):
        """
        验证用户登录

        Parameters
        ----------
        username : str
            用户名
        password : str
            密码

        Returns
        -------
        tuple
            (success: bool, user_or_error: User or str)
        """
        if not username or not password:
            return False, '用户名和密码不能为空'

        user = User.find_by_username(username)
        if user is None:
            return False, '用户名或密码错误'

        if not user.verify_password(password):
            return False, '用户名或密码错误'

        return True, user
