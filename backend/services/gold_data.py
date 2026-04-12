"""
黄金 ETF 数据服务

提供黄金 ETF 实时数据获取、技术指标计算、信号分析等业务逻辑。
数据来源：新浪财经 K 线接口（主），腾讯财经（备）。
支持 SQLite 数据缓存，减少重复请求。
"""

import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, date as date_type
from typing import Dict, Any, List, Tuple, Optional

from backend.utils.indicators import calculate_indicators
from backend.models.kline import KlineModel

# 默认 ETF 代码：华夏黄金 ETF（518880）
DEFAULT_SYMBOL = "sh518880"
DEFAULT_DATALEN = 90

# 常用股票/ETF 名称映射（纯数字代码 -> 显示名称）
STOCK_NAMES = {
    "sh518880": "华夏黄金ETF",
    "sz000300": "沪深300",
    "sh000001": "上证指数",
    "sz000001": "平安银行",
    "sh600519": "贵州茅台",
    "sz000858": "五粮液",
    "sz300750": "宁德时代",
    "sh600036": "招商银行",
    "sh601318": "中国平安",
    "sh600276": "恒瑞医药",
    "sh601888": "中国中免",
    "sh600887": "伊利股份",
    "sz000333": "美的集团",
    "sz002594": "比亚迪",
    "sh688041": "海光信息",
    "sh688111": "金山办公",
}

# 各股票的简单描述（用于ETF介绍动态切换）
STOCK_DESCRIPTIONS = {
    "sh518880": {
        "title": "什么是黄金ETF？",
        "items": [
            {
                "heading": "💰 黄金ETF是什么？",
                "body": "黄金ETF(Exchange Traded Fund)是一种在交易所上市交易的开放式基金，以黄金为基础资产，追踪黄金价格波动。投资者可以像买卖股票一样交易黄金ETF。"
            },
            {
                "heading": "📈 518880 华夏黄金ETF",
                "body": "国内规模最大的黄金ETF之一，主要投资于上海黄金交易所的黄金现货合约，为投资者提供便捷的黄金投资渠道。"
            },
            {
                "heading": "⚠️ 投资风险",
                "body": "黄金ETF受金价波动影响，还包括市场风险、流动性风险等。本系统仅供参考，不构成投资建议，投资需谨慎。"
            },
        ]
    },
    "sz000300": {
        "title": "沪深300指数简介",
        "items": [
            {
                "heading": "📊 沪深300是什么？",
                "body": "沪深300指数由沪深两市中市值大、流动性好的300只股票组成，综合反映中国A股市场上市股票价格的整体表现，是A股市场最具代表性的宽基指数。"
            },
            {
                "heading": "📈 000300 沪深300",
                "body": "沪深300指数成分股覆盖多个行业，权重股以金融、消费、信息技术为主，是机构投资者业绩基准的首选指数。"
            },
            {
                "heading": "⚠️ 投资风险提示",
                "body": "指数基金投资仍受市场系统性风险影响。本系统仅供参考，不构成投资建议，投资需谨慎。"
            },
        ]
    },
}

# 通用股票描述模板
GENERIC_STOCK_DESC = {
    "title": "技术分析简介",
    "items": [
        {
            "heading": "📊 技术分析说明",
            "body": "本系统通过移动平均线(MA)、MACD、KDJ、RSI、布林带等技术指标，对股票的历史价格走势进行综合技术分析，为投资决策提供参考。"
        },
        {
            "heading": "⚠️ 投资风险提示",
            "body": "技术分析仅供参考，不构成投资建议。股票投资受多种因素影响，包括但不限于公司业绩、宏观经济环境、政策因素等。投资有风险，入市需谨慎。"
        },
    ]
}


def _fetch_from_sina(symbol: str, datalen: int) -> Optional[pd.DataFrame]:
    """从新浪财经获取K线数据"""
    url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    params = {"symbol": symbol, "scale": "240", "ma": "no", "datalen": str(datalen)}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = json.loads(r.text)
        if not data or not isinstance(data, list):
            return None
        df = pd.DataFrame(data)
        df.columns = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
        for col in ['开盘', '最高', '最低', '收盘']:
            df[col] = pd.to_numeric(df[col])
        df['成交量'] = pd.to_numeric(df['成交量'])
        df = df.sort_values('日期').reset_index(drop=True)
        return df
    except Exception:
        return None


def _fetch_from_tencent(symbol: str, datalen: int) -> Optional[pd.DataFrame]:
    """从腾讯财经获取K线数据（备用）"""
    # 腾讯接口: 6位数字代码
    code_num = symbol[2:] if symbol.startswith(('sh', 'sz')) else symbol
    market = 1 if symbol.startswith('sh') else 0
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={symbol},day,,,{datalen},qfq"
    try:
        r = requests.get(url, timeout=10)
        text = r.text.strip()
        if not text:
            return None
        data = json.loads(text.replace('var kline_dayqfq=', ''))
        if 'data' not in data or not data['data']:
            return None
        stock_data = data['data'].get(symbol, data['data'].get(code_num, {}))
        qfqday = stock_data.get('qfqday', stock_data.get('day', []))
        if not qfqday:
            return None
        # 取最新的datalen条
        qfqday = qfqday[-datalen:]
        df = pd.DataFrame(qfqday, columns=['日期', '开盘', '收盘', '最高', '最低', '成交量'])
        for col in ['开盘', '最高', '最低', '收盘']:
            df[col] = pd.to_numeric(df[col])
        df['成交量'] = pd.to_numeric(df['成交量'])
        return df
    except Exception:
        return None


def _parse_date_param(value: Optional[str]) -> Optional[date_type]:
    """
    解析日期参数，支持 YYYYMMDD 和 YYYY-MM-DD 格式。

    Parameters
    ----------
    value : str or None

    Returns
    -------
    date_type or None
    """
    if not value:
        return None
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, '%Y%m%d').date()
    return datetime.strptime(s, '%Y-%m-%d').date()


def fetch_etf_kline(symbol: str = DEFAULT_SYMBOL, datalen: int = DEFAULT_DATALEN,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
    """
    从新浪财经获取K线数据，失败后尝试腾讯财经作为备选。
    支持 SQLite 缓存：当天数据按需刷新，历史数据永久缓存。

    Parameters
    ----------
    symbol : str
        ETF/股票代码，如 sh518880、sz000300
    datalen : int
        拉取历史数据天数（无日期范围时使用），默认 90 天
    start_date : str, optional
        开始日期（YYYYMMDD 或 YYYY-MM-DD）
    end_date : str, optional
        结束日期（YYYYMMDD 或 YYYY-MM-DD）

    Returns
    -------
    pd.DataFrame
        列名：'日期','开盘','最高','最低','收盘','成交量'，按日期升序排列
    """
    req_start = _parse_date_param(start_date)
    req_end = _parse_date_param(end_date)
    today = datetime.now().date()

    # 确定实际需要查询的网络数据范围
    if req_start and req_end:
        # 用户指定了日期范围：始终从网络获取（可能包含当天）
        fetch_start = req_start
        fetch_end = req_end
        merge_target_start = req_start
        merge_target_end = req_end
        use_cache_fallback = False
    else:
        # 无日期范围 → 使用缓存策略
        use_cache_fallback = True
        db_latest = KlineModel.get_latest_date(symbol)
        db_latest_date = datetime.strptime(db_latest, '%Y-%m-%d').date() if db_latest else None

        if db_latest_date:
            # 数据库有数据
            cache_days = (today - db_latest_date).days
            if db_latest_date == today:
                # 当天数据已有，直接用缓存（+ 可能有的历史）
                cached = KlineModel.get_cached_data(symbol)
                if len(cached) >= datalen:
                    return cached.tail(datalen).reset_index(drop=True)
                # 不足90天，补历史
                fetch_end = today
                fetch_start = today - timedelta(days=datalen - 1)
                merge_target_start = fetch_start
                merge_target_end = fetch_end
            else:
                # 最新数据不是今天 → 补今天的数据
                fetch_start = db_latest_date + timedelta(days=1)
                fetch_end = today
                merge_target_start = None   # 保留全部缓存
                merge_target_end = fetch_end
        else:
            # 数据库为空，直接拉取
            fetch_start = today - timedelta(days=datalen - 1)
            fetch_end = today
            merge_target_start = None
            merge_target_end = None

    # 计算需要拉取的天数（多拉一些避免漏数据）
    fetch_datalen = max(1, (fetch_end - fetch_start).days + 1)

    # 从网络获取
    df_new = _fetch_from_network(symbol, fetch_datalen)
    KlineModel.save_data(symbol, df_new)

    # 合并返回
    if use_cache_fallback and merge_target_start is None:
        # 全量返回数据库数据
        full = KlineModel.get_cached_data(symbol)
        return full.tail(datalen).reset_index(drop=True)
    else:
        # 返回请求范围
        start_str = (merge_target_start or req_start).strftime('%Y-%m-%d') if (merge_target_start or req_start) else None
        end_str = (merge_target_end or req_end).strftime('%Y-%m-%d') if (merge_target_end or req_end) else None
        result = KlineModel.get_cached_data(symbol, start_str, end_str)
        return result.reset_index(drop=True)


def _fetch_from_network(symbol: str, datalen: int) -> Optional[pd.DataFrame]:
    """从网络获取K线数据（新浪优先，腾讯备选）"""
    last_error = None
    for attempt in range(3):
        df = _fetch_from_sina(symbol, datalen)
        if df is not None and len(df) > 0:
            return df
        last_error = f"新浪财经第{attempt+1}次获取失败"
        time.sleep(0.5)
    for attempt in range(3):
        df = _fetch_from_tencent(symbol, datalen)
        if df is not None and len(df) > 0:
            return df
        last_error = f"腾讯财经第{attempt+1}次获取失败"
        time.sleep(0.5)
    raise ValueError(f"无法获取 {symbol} 的数据，请检查代码是否正确。{last_error}")


def get_full_data(symbol: str = DEFAULT_SYMBOL, datalen: int = DEFAULT_DATALEN,
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> pd.DataFrame:
    """
    获取完整的 ETF 数据（含所有技术指标）。

    Parameters
    ----------
    symbol : str
        ETF 代码
    datalen : int
        数据天数（无日期范围时使用）
    start_date : str, optional
        开始日期（YYYYMMDD 或 YYYY-MM-DD）
    end_date : str, optional
        结束日期（YYYYMMDD 或 YYYY-MM-DD）

    Returns
    -------
    pd.DataFrame
        添加了技术指标列的 DataFrame
    """
    df = fetch_etf_kline(symbol, datalen, start_date=start_date, end_date=end_date)
    df = calculate_indicators(df)
    return df


def generate_signals(latest: pd.Series) -> List[Tuple[str, str, str]]:
    """
    基于最新行情数据生成综合技术分析信号。

    Parameters
    ----------
    latest : pd.Series
        DataFrame 最新一行（一条行情数据）

    Returns
    -------
    List[Tuple[str, str, str]]
        每项为 (信号名称, 信号状态, 描述)，例如：
        ("均线多头", "✅ 看涨", "短期均线多头排列，价格强势")
    """
    signals = []

    # ---------- 均线信号 ----------
    if latest['收盘'] > latest['MA5'] and latest['MA5'] > latest['MA10']:
        signals.append(("均线多头", "✅ 看涨", "短期均线多头排列，价格强势"))
    elif latest['收盘'] < latest['MA5'] and latest['MA5'] < latest['MA10']:
        signals.append(("均线空头", "⚠️ 看跌", "短期均线空头排列，价格弱势"))
    else:
        signals.append(("均线混乱", "➡️ 观望", "均线方向不明，建议等待"))

    # ---------- MACD 信号 ----------
    if latest['MACD'] > 0 and latest['MACD'] > latest['MACD_SIGNAL']:
        signals.append(("MACD强势", "✅ 看涨", "MACD零轴上方，金叉运行中"))
    elif latest['MACD'] < 0 and latest['MACD'] < latest['MACD_SIGNAL']:
        signals.append(("MACD弱势", "⚠️ 看跌", "MACD零轴下方，死叉运行中"))
    elif latest['MACD_HIST'] > 0 and latest['MACD'] < 0:
        signals.append(("MACD反弹", "📈 谨慎看涨", "底部金叉信号，可能反弹"))
    else:
        signals.append(("MACD调整", "➡️ 观望", "MACD在零轴附近震荡"))

    # ---------- KDJ 信号 ----------
    if latest['J'] > 80:
        signals.append(("KDJ超买", "⚠️ 谨慎", "J值超买，短期可能回调"))
    elif latest['J'] < 20:
        signals.append(("KDJ超卖", "📈 关注", "J值超卖，可能出现反弹"))
    else:
        signals.append(("KDJ中性", "➡️ 正常", "KDJ在合理区间"))

    # ---------- RSI 信号 ----------
    if latest['RSI'] > 70:
        signals.append(("RSI超买", "⚠️ 谨慎", "RSI超过70，市场可能过热"))
    elif latest['RSI'] < 30:
        signals.append(("RSI超卖", "📈 关注", "RSI低于30，可能超跌反弹"))
    elif latest['RSI'] > 50:
        signals.append(("RSI偏强", "✅ 偏多", "RSI在50以上，多方占优"))
    else:
        signals.append(("RSI偏弱", "⚠️ 偏空", "RSI在50以下，空方占优"))

    # ---------- 资金信号 ----------
    if latest['累计净流入'] > 0:
        signals.append(("资金流入", "✅ 利好", "近期资金净流入，机构看多"))
    else:
        signals.append(("资金流出", "⚠️ 谨慎", "近期资金净流出，主力撤退"))

    return signals


def build_api_response(df: pd.DataFrame, symbol: str = DEFAULT_SYMBOL,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    将 DataFrame 转换为 API JSON 响应结构。

    Parameters
    ----------
    df : pd.DataFrame
        已计算指标的数据
    symbol : str
        当前股票代码（用于查找名称）

    Returns
    -------
    Dict
        符合前端 /api/data 接口规范的字典
    """
    latest = df.iloc[-1]
    signals = generate_signals(latest)

    # 辅助函数：安全取值
    def safe(val, default=0.0):
        if pd.isna(val):
            return default
        return float(val)

    return {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol_name': STOCK_NAMES.get(symbol, symbol.upper()),
        'start_date': start_date,
        'end_date': end_date,
        # 图表数据
        'dates': df['日期'].tolist(),
        'kdata': df[['开盘', '收盘', '最低', '最高']].values.tolist(),
        'volume': df['成交量'].tolist(),
        'MA5': df['MA5'].fillna(0).tolist(),
        'MA10': df['MA10'].fillna(0).tolist(),
        'MA20': df['MA20'].fillna(0).tolist(),
        'BB_UPPER': df['BB_UPPER'].fillna(0).tolist(),
        'BB_LOWER': df['BB_LOWER'].fillna(0).tolist(),
        'MACD': df['MACD'].fillna(0).tolist(),
        'MACD_SIGNAL': df['MACD_SIGNAL'].fillna(0).tolist(),
        'MACD_HIST': df['MACD_HIST'].fillna(0).tolist(),
        'K': df['K'].fillna(0).tolist(),
        'D': df['D'].fillna(0).tolist(),
        'J': df['J'].fillna(0).tolist(),
        'RSI': df['RSI'].fillna(0).tolist(),
        '资金净流入': df['资金净流入'].fillna(0).tolist(),
        '累计净流入': df['累计净流入'].fillna(0).tolist(),
        # 最新指标卡片
        'latest': {
            '收盘': safe(latest['收盘']),
            '涨跌幅': safe(latest['涨跌幅']),
            'MA5': safe(latest['MA5']),
            'MA10': safe(latest['MA10']),
            'MA20': safe(latest['MA20']),
            'RSI': safe(latest['RSI']),
            'J': safe(latest['J']),
            'MACD': safe(latest['MACD']),
            'MACD_SIGNAL': safe(latest['MACD_SIGNAL']),
            'MACD_HIST': safe(latest['MACD_HIST']),
            '累计净流入': safe(latest['累计净流入']),
        },
        # 分析信号
        'signals': signals,
    }
