"""
邮件通知工具模块

提供发送邮件的功能，用于自动交易信号通知、系统告警等场景。
支持 SMTP 协议，可配置发件人、收件人、主题和正文。
"""
import smtplib
import socket
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        use_tls: bool = True
    ):
        """
        初始化邮件通知器
        
        Args:
            smtp_server: SMTP 服务器地址（如 smtp.qq.com）
            smtp_port: SMTP 服务器端口（如 587 或 465）
            sender_email: 发件人邮箱地址
            sender_password: 发件人邮箱密码或授权码
            use_tls: 是否使用 TLS 加密
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.use_tls = use_tls
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
        cc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件正文
            is_html: 是否为 HTML 格式
            cc_emails: 抄送人邮箱列表（可选）
            
        Returns:
            bool: 发送成功返回 True，失败返回 False
        """
        try:
            # 创建邮件对象
            if is_html:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = self.sender_email
                msg['To'] = ', '.join(to_emails)
                
                if cc_emails:
                    msg['Cc'] = ', '.join(cc_emails)
                
                # 添加 HTML 正文
                html_part = MIMEText(body, 'html', 'utf-8')
                msg.attach(html_part)
            else:
                msg = MIMEText(body, 'plain', 'utf-8')
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = self.sender_email
                msg['To'] = ', '.join(to_emails)
                
                if cc_emails:
                    msg['Cc'] = ', '.join(cc_emails)
            
            # 连接 SMTP 服务器并发送邮件
            logger.info(f"[Email] 正在连接 SMTP 服务器: {self.smtp_server}:{self.smtp_port}")
            
            if self.use_tls:
                logger.debug(f"[Email] 使用 TLS 加密连接")
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                # server.set_debuglevel(1)  # 启用调试模式（已注释）
                server.ehlo()
                logger.debug(f"[Email] 开始 TLS 加密")
                server.starttls()
                server.ehlo()
            else:
                logger.debug(f"[Email] 使用 SSL 加密连接")
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
                # server.set_debuglevel(1)  # 启用调试模式（已注释）
            
            logger.info(f"[Email] SMTP 连接成功，正在登录: {self.sender_email}")
            server.login(self.sender_email, self.sender_password)
            logger.info(f"[Email] ✅ 登录成功")
            
            # 组合所有收件人
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            
            logger.info(f"[Email] 正在发送邮件到 {len(all_recipients)} 个收件人...")
            server.sendmail(self.sender_email, all_recipients, msg.as_string())
            server.quit()
            
            logger.info(f"[Email] ✅ 邮件发送成功: 主题={subject}, 收件人={to_emails}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"[Email] ❌ SMTP 认证失败: {e}")
            logger.error(f"[Email] 可能原因: 授权码错误或已过期")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"[Email] ❌ SMTP 连接失败: {e}")
            logger.error(f"[Email] 可能原因: 服务器地址/端口错误或 SMTP 服务未开启")
            return False
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"[Email] ❌ 收件人被拒绝: {e}")
            logger.error(f"[Email] 可能原因: 收件人地址无效或被标记为垃圾邮件")
            return False
        except socket.timeout as e:
            logger.error(f"[Email] ❌ 连接超时: {e}")
            logger.error(f"[Email] 可能原因: 网络问题或防火墙阻止")
            return False
        except Exception as e:
            logger.error(f"[Email] ❌ 邮件发送失败: {type(e).__name__}: {e}", exc_info=True)
            return False
    
    def send_trade_notification(
        self,
        to_emails: List[str],
        user_id: int,
        symbol: str,
        action: str,
        shares: int,
        price: float,
        strategy: str,
        task_name: str = None,
        reason: str = None
    ) -> bool:
        """
        发送交易通知邮件
        
        Args:
            to_emails: 收件人邮箱列表
            user_id: 用户ID
            symbol: 股票代码
            action: 交易动作（买入/卖出）
            shares: 交易数量
            price: 交易价格
            strategy: 策略类型
            task_name: 任务名称
            reason: 交易原因（如止损、止盈等）
            
        Returns:
            bool: 发送成功返回 True
        """
        task_name = task_name or symbol
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建邮件主题
        action_emoji = "📈" if action == "买入" else "📉"
        subject = f"{action_emoji} 自动交易通知 - {task_name} {action}"
        
        # 构建 HTML 邮件正文
        reason_text = f"<p><strong>交易原因：</strong>{reason}</p>" if reason else ""
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">{action_emoji} 自动交易执行通知</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 20px; border: 1px solid #e0e0e0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold; width: 120px;">任务名称：</td>
                        <td style="padding: 10px 0;">{task_name}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">股票代码：</td>
                        <td style="padding: 10px 0;">{symbol}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">交易动作：</td>
                        <td style="padding: 10px 0; color: {'#28a745' if action == '买入' else '#dc3545'}; 
                                    font-weight: bold;">{action}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">交易数量：</td>
                        <td style="padding: 10px 0;">{shares} 股</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">交易价格：</td>
                        <td style="padding: 10px 0;">¥{price:.4f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">交易金额：</td>
                        <td style="padding: 10px 0;">¥{shares * price:.2f}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">策略类型：</td>
                        <td style="padding: 10px 0;">{strategy}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #e0e0e0;">
                        <td style="padding: 10px 0; font-weight: bold;">用户ID：</td>
                        <td style="padding: 10px 0;">{user_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">执行时间：</td>
                        <td style="padding: 10px 0;">{timestamp}</td>
                    </tr>
                </table>
                
                {reason_text}
                
                <div style="margin-top: 20px; padding: 15px; background: #fff3cd; 
                            border-left: 4px solid #ffc107; border-radius: 4px;">
                    <p style="margin: 0; color: #856404;">
                        <strong>⚠️ 提示：</strong>此为模拟交易通知，不涉及真实资金操作。
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; padding: 15px; color: #999; font-size: 12px;">
                <p>此邮件由自动交易系统发送，请勿回复</p>
            </div>
        </div>
        """
        
        return self.send_email(to_emails, subject, html_body, is_html=True)
    
    def send_alert_notification(
        self,
        to_emails: List[str],
        title: str,
        message: str,
        level: str = "warning"
    ) -> bool:
        """
        发送告警通知邮件
        
        Args:
            to_emails: 收件人邮箱列表
            title: 告警标题
            message: 告警内容
            level: 告警级别（info/warning/error/critical）
            
        Returns:
            bool: 发送成功返回 True
        """
        # 根据级别设置颜色和图标
        level_config = {
            "info": {"color": "#17a2b8", "icon": "ℹ️"},
            "warning": {"color": "#ffc107", "icon": "⚠️"},
            "error": {"color": "#dc3545", "icon": "❌"},
            "critical": {"color": "#721c24", "icon": "🔥"}
        }
        
        config = level_config.get(level, level_config["warning"])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        subject = f"{config['icon']} 系统告警 - {title}"
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: {config['color']}; color: white; 
                        padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">{config['icon']} 系统告警通知</h2>
            </div>
            
            <div style="background: #f9f9f9; padding: 20px; border: 1px solid #e0e0e0;">
                <h3 style="color: {config['color']}; margin-top: 0;">{title}</h3>
                <p style="line-height: 1.6;">{message}</p>
                <p style="color: #999; font-size: 12px;">告警时间：{timestamp}</p>
            </div>
            
            <div style="text-align: center; padding: 15px; color: #999; font-size: 12px;">
                <p>此邮件由自动交易系统发送，请勿回复</p>
            </div>
        </div>
        """
        
        return self.send_email(to_emails, subject, html_body, is_html=True)


# 全局邮件通知器实例（懒加载）
_notifier_instance: Optional[EmailNotifier] = None


def get_email_notifier() -> Optional[EmailNotifier]:
    """
    获取全局邮件通知器实例
    
    Returns:
        EmailNotifier 实例或 None（如果未配置）
    """
    global _notifier_instance
    
    if _notifier_instance is not None:
        logger.debug("[Email] 使用已初始化的邮件通知器实例")
        return _notifier_instance
    
    # 从环境变量读取配置
    import os
    smtp_server = os.getenv('EMAIL_SMTP_SERVER')
    smtp_port = os.getenv('EMAIL_SMTP_PORT')
    sender_email = os.getenv('EMAIL_SENDER')
    sender_password = os.getenv('EMAIL_PASSWORD')
    
    logger.info(f"[Email] 正在初始化邮件通知器...")
    logger.debug(f"[Email] EMAIL_SMTP_SERVER: {smtp_server or '(未设置)'}")
    logger.debug(f"[Email] EMAIL_SMTP_PORT: {smtp_port or '(未设置)'}")
    logger.debug(f"[Email] EMAIL_SENDER: {sender_email or '(未设置)'}")
    logger.debug(f"[Email] EMAIL_PASSWORD: {'*' * 8 + sender_password[-4:] if sender_password and len(sender_password) > 4 else '(未设置)'}")
    logger.debug(f"[Email] EMAIL_USE_TLS: {os.getenv('EMAIL_USE_TLS', 'true')}")
    
    if not all([smtp_server, smtp_port, sender_email, sender_password]):
        missing = []
        if not smtp_server: missing.append('EMAIL_SMTP_SERVER')
        if not smtp_port: missing.append('EMAIL_SMTP_PORT')
        if not sender_email: missing.append('EMAIL_SENDER')
        if not sender_password: missing.append('EMAIL_PASSWORD')
        logger.warning(f"[Email] ⚠️ 邮件配置不完整，缺少: {', '.join(missing)}")
        logger.warning(f"[Email] 邮件通知功能未启用")
        return None
    
    try:
        use_tls = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
        logger.info(f"[Email] 创建 EmailNotifier 实例: {smtp_server}:{smtp_port}, TLS={use_tls}")
        
        _notifier_instance = EmailNotifier(
            smtp_server=smtp_server,
            smtp_port=int(smtp_port),
            sender_email=sender_email,
            sender_password=sender_password,
            use_tls=use_tls
        )
        logger.info(f"[Email] ✅ 邮件通知器初始化成功")
        return _notifier_instance
    except Exception as e:
        logger.error(f"[Email] ❌ 邮件通知器初始化失败: {type(e).__name__}: {e}", exc_info=True)
        return None


def send_trade_email(
    to_emails: List[str],
    user_id: int,
    symbol: str,
    action: str,
    shares: int,
    price: float,
    strategy: str,
    task_name: str = None,
    reason: str = None
) -> bool:
    """
    便捷函数：发送交易通知邮件
    
    Args:
        to_emails: 收件人邮箱列表
        user_id: 用户ID
        symbol: 股票代码
        action: 交易动作
        shares: 交易数量
        price: 交易价格
        strategy: 策略类型
        task_name: 任务名称
        reason: 交易原因
        
    Returns:
        bool: 发送成功返回 True
    """
    notifier = get_email_notifier()
    if notifier is None:
        return False
    
    return notifier.send_trade_notification(
        to_emails, user_id, symbol, action, shares, price, strategy, task_name, reason
    )


def send_alert_email(
    to_emails: List[str],
    title: str,
    message: str,
    level: str = "warning"
) -> bool:
    """
    便捷函数：发送告警通知邮件
    
    Args:
        to_emails: 收件人邮箱列表
        title: 告警标题
        message: 告警内容
        level: 告警级别
        
    Returns:
        bool: 发送成功返回 True
    """
    notifier = get_email_notifier()
    if notifier is None:
        return False
    
    return notifier.send_alert_notification(to_emails, title, message, level)
