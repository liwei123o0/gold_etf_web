"""
股票代码处理工具模块

统一股票代码的前缀识别和规范化逻辑。
支持上海（sh）、深圳（sz）、北京（bj）三大交易所的代码自动识别。
"""

import re


def normalize_symbol(raw: str) -> str:
    """
    规范化股票代码：将纯数字代码自动添加交易所前缀

    识别规则：
        - 6xxxxx → 上海交易所（sh），包括沪市主板 600/601/603 和科创板 688
        - 000xxx/001xxx/002xxx/003xxx → 深圳交易所（sz），包括主板和中小板
        - 300xxx/301xxx → 深圳交易所（sz），创业板
        - 8xxxxx → 北京交易所（bj）
        - 已有前缀（sh/sz/bj）的代码直接返回
        - 空值或无效输入默认返回 sh518880

    参数：
        raw (str): 股票代码，可以是6位数字或带前缀的完整代码

    返回：
        str: 带交易所前缀的完整股票代码

    示例：
        >>> normalize_symbol('518880')
        'sh518880'
        >>> normalize_symbol('000300')
        'sz000300'
        >>> normalize_symbol('300001')
        'sz300001'
        >>> normalize_symbol('688001')
        'sh688001'
        >>> normalize_symbol('831010')
        'bj831010'
        >>> normalize_symbol('sh518880')
        'sh518880'
    """
    # 清理输入：去除空格、转小写
    raw = (raw or '').strip().lower()
    # 空值返回默认代码
    if not raw:
        return 'sh518880'

    # 已是完整代码（带交易所前缀），直接返回
    if raw.startswith(('sh', 'sz', 'bj')):
        return raw

    # 去掉可能的 cn_ 前缀（部分数据源使用此格式）
    if raw.startswith('cn_'):
        raw = raw[3:]

    # 6xxxxx → 上海交易所（沪市主板 600/601/603 + 科创板 688）
    if re.match(r'^6\d{5}$', raw):
        return 'sh' + raw

    # 000xxx → 深圳交易所（沪深300等指数）
    if re.match(r'^000\d{3}$', raw):
        return 'sz' + raw

    # 001xxx → 深圳交易所
    if re.match(r'^001\d{3}$', raw):
        return 'sz' + raw

    # 002xxx → 深圳交易所（中小板）
    if re.match(r'^002\d{3}$', raw):
        return 'sz' + raw

    # 003xxx → 深圳交易所
    if re.match(r'^003\d{3}$', raw):
        return 'sz' + raw

    # 300xxx → 深圳交易所（创业板）
    if re.match(r'^300\d{3}$', raw):
        return 'sz' + raw

    # 301xxx → 深圳交易所（创业板注册制）
    if re.match(r'^301\d{3}$', raw):
        return 'sz' + raw

    # 8xxxxx → 北京交易所
    if re.match(r'^8\d{5}$', raw):
        return 'bj' + raw

    # 无法识别的代码，默认归入上海交易所
    return 'sh' + raw


def strip_prefix(symbol: str) -> str:
    """
    去除股票代码的交易所前缀，只保留6位数字代码

    参数：
        symbol (str): 带前缀的股票代码，如 'sh518880'

    返回：
        str: 6位数字股票代码

    示例：
        >>> strip_prefix('sh518880')
        '518880'
        >>> strip_prefix('sz000300')
        '000300'
        >>> strip_prefix('bj831010')
        '831010'
        >>> strip_prefix('518880')
        '518880'
    """
    # 清理输入：去除空格、转小写
    symbol = (symbol or '').strip().lower()

    # 依次去除已知前缀
    if symbol.startswith('sh'):
        return symbol[2:]
    if symbol.startswith('sz'):
        return symbol[2:]
    if symbol.startswith('bj'):
        return symbol[2:]
    if symbol.startswith('cn_'):
        return symbol[3:]

    # 无前缀，直接返回
    return symbol


def validate_stock_code(code: str) -> bool:
    """
    验证股票代码是否为有效的6位数字格式

    参数：
        code (str): 待验证的股票代码

    返回：
        bool: 如果是有效的6位数字返回 True，否则返回 False
    """
    code = (code or '').strip()
    return bool(re.match(r'^\d{6}$', code))


def get_exchange(symbol: str) -> str:
    """
    获取股票所属交易所代码

    根据股票代码的前缀或数字特征判断所属交易所。

    参数：
        symbol (str): 股票代码，可以是带前缀的完整代码或纯数字代码

    返回：
        str: 交易所代码，'sh'（上海）、'sz'（深圳）或 'bj'（北京）
    """
    # 清理输入
    symbol = (symbol or '').strip().lower()

    # 优先根据前缀判断
    if symbol.startswith('sh'):
        return 'sh'
    if symbol.startswith('bj'):
        return 'bj'
    if symbol.startswith('sz'):
        return 'sz'

    # 无前缀时根据数字特征判断
    # 6xxxxx → 上海
    if re.match(r'^6\d{5}$', symbol):
        return 'sh'
    # 8xxxxx → 北京
    if re.match(r'^8\d{5}$', symbol):
        return 'bj'
    # 其他默认为深圳
    return 'sz'


def format_symbol_for_display(symbol: str) -> str:
    """
    格式化股票代码用于前端显示（去除交易所前缀）

    参数：
        symbol (str): 股票代码，如 'sh518880'

    返回：
        str: 6位数字股票代码，如 '518880'
    """
    return strip_prefix(symbol)
