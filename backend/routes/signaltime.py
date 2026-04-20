"""
实时信号接口

接收实时价格，结合缓存的日线指标，重新计算交易信号。
"""

from flask import Blueprint, jsonify, request

bp = Blueprint('signaltime', __name__)

DEFAULT_SYMBOL = "sh518880"


def normalize_symbol(raw: str) -> str:
    """将用户输入的股票代码规范化为带前缀的形式"""
    raw = (raw or '').strip()
    if not raw:
        return DEFAULT_SYMBOL
    if raw.startswith(('sh', 'sz', 'bj')):
        return raw
    if len(raw) >= 4:
        if raw.startswith(('000', '001', '002', '003')):
            return 'sz' + raw
        return 'sh' + raw
    return 'sh' + raw


def _calc_trade_signal_from_latest(latest) -> str:
    """根据指标打分计算综合交易信号"""
    score = 0
    close = latest.get('收盘', 0)
    ma5 = latest.get('MA5', 0)
    ma10 = latest.get('MA10', 0)
    macd_hist = latest.get('MACD_HIST', 0)
    rsi = latest.get('RSI', 0)
    j = latest.get('J', 0)

    if close > ma5 and ma5 > ma10:
        score += 1
    elif close < ma5 and ma5 < ma10:
        score -= 1

    if macd_hist > 0:
        score += 1
    elif macd_hist < 0:
        score -= 1

    if rsi > 70:
        score -= 1
    elif rsi < 30:
        score += 1

    if j > 80:
        score -= 1
    elif j < 20:
        score += 1

    if score >= 2:
        return "买入"
    elif score <= -2:
        return "卖出"
    else:
        return "观望"


def _calc_change_pct(realtime_price: float, prev_close: float) -> float:
    """计算涨跌幅"""
    if not prev_close:
        return 0.0
    return (realtime_price - prev_close) / prev_close * 100


@bp.route('/api/signaltime', methods=['POST'])
def api_signaltime():
    """
    接收实时价格，结合日线指标计算实时交易信号。

    Request Body (JSON):
    {
        "symbol": "sh518880",
        "realtime_price": 10.025,
        "prev_close": 10.029   // 可选，不传则从日线数据取
    }

    Returns:
        实时交易信号 + 信号明细 + 指标卡片数据
    """
    body = request.get_json()
    if not body:
        return jsonify({'error': '请求体不能为空'}), 400

    symbol = normalize_symbol(body.get('symbol', DEFAULT_SYMBOL))
    realtime_price = body.get('realtime_price')
    prev_close_override = body.get('prev_close')

    if not realtime_price or realtime_price <= 0:
        return jsonify({'error': 'realtime_price 无效'}), 400

    # 拿日线数据（含指标）
    try:
        from backend.services.gold_data import get_full_data
        df = get_full_data(symbol=symbol, datalen=90)
    except Exception as e:
        return jsonify({'error': f'获取数据失败: {str(e)}'}), 500

    if len(df) < 2:
        return jsonify({'error': '数据不足'}), 400

    # 取最新一行作为基础
    latest = df.iloc[-1].copy()

    # 替换为实时价格
    realtime_close = float(realtime_price)

    # 计算实时涨跌幅
    if prev_close_override:
        prev_close = float(prev_close_override)
    else:
        # 取昨天收盘价（前一行收盘）
        prev_close = float(df.iloc[-2]['收盘']) if len(df) >= 2 else float(latest['收盘'])

    change_pct = _calc_change_pct(realtime_close, prev_close)

    # 替换
    latest['收盘'] = realtime_close
    latest['涨跌幅'] = change_pct

    # 生成信号（用实时价格重新算）
    from backend.services.gold_data import generate_signals
    signals = generate_signals(latest, df)

    # 计算实时交易信号
    trade_signal = _calc_trade_signal_from_latest(latest)

    # 安全取值
    def safe(val, default=0.0):
        import pandas as pd
        if pd.isna(val):
            return default
        return float(val)

    # 计算 MACD_HIST 历史均值
    macd_hist_window = 20
    macd_hist_mean = df['MACD_HIST'].iloc[-macd_hist_window:].mean() if len(df) >= macd_hist_window else df['MACD_HIST'].mean()

    # 生成网格信号（用实时价格）
    from backend.services.gold_data import get_grid_signal
    grid_signals = {
        'MA5':  get_grid_signal(latest, ma_key='MA5'),
        'MA10': get_grid_signal(latest, ma_key='MA10'),
        'MA20': get_grid_signal(latest, ma_key='MA20'),
        'MA60': get_grid_signal(latest, ma_key='MA60'),
        'MACD': get_grid_signal(latest, macd_ma_key='MACD', macd_hist_window=macd_hist_window,
                                macd_hist_mean=macd_hist_mean),
        'MACD_SIGNAL': get_grid_signal(latest, macd_ma_key='MACD_SIGNAL', macd_hist_window=macd_hist_window,
                                       macd_hist_mean=macd_hist_mean),
    }
    grid_signal = get_grid_signal(latest, ma_key='MA20')

    return jsonify({
        'code': 0,
        'msg': 'success',
        'symbol': symbol,
        'realtime_price': realtime_close,
        'prev_close': prev_close,
        'change_pct': round(change_pct, 2),
        'trade_signal': trade_signal,
        'signals': signals,
        'grid_signals': grid_signals,
        'grid_signal': grid_signal,
        'latest': {
            '收盘': realtime_close,
            '涨跌幅': round(change_pct, 2),
            'MA5': safe(latest['MA5']),
            'MA10': safe(latest['MA10']),
            'MA20': safe(latest['MA20']),
            'MA60': safe(latest['MA60']),
            'RSI': safe(latest['RSI']),
            'J': safe(latest['J']),
            'MACD': safe(latest['MACD']),
            'MACD_SIGNAL': safe(latest['MACD_SIGNAL']),
            'MACD_HIST': safe(latest['MACD_HIST']),
            'BB_UPPER': safe(latest.get('BB_UPPER', 0)),
            'BB_MID': safe(latest.get('BB_MID', 0)),
            'BB_LOWER': safe(latest.get('BB_LOWER', 0)),
            'ATR': safe(latest.get('ATR', 0)),
        }
    })
