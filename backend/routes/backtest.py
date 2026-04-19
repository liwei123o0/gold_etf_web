"""
模拟交易回测接口

提供 POST /api/backtest 接口，运行网格交易回测。
"""

from flask import Blueprint, jsonify, request
from backend.services.gold_data import get_full_data
from backend.services.backtest import run_grid_backtest

bp = Blueprint('backtest', __name__)

DEFAULT_SYMBOL = "sh518880"


@bp.route('/api/backtest', methods=['POST'])
def api_backtest():
    """
    运行网格交易回测。

    请求 JSON：
    {
        "symbol": "sh518880",
        "start_date": "2024-01-01",    # 可选
        "end_date": "2024-12-31",       # 可选
        "initial_capital": 100000.0,
        "grid_count": 10,               # 5/10/15/20
        "spread_type": "fixed",         # "fixed" 或 "atr"
        "base_ma_key": "MA20",         # MA5/MA10/MA20/MA60
    }

    响应：
    {
        "initial_capital": float,
        "final_equity": float,
        "total_return": float,
        "total_return_pct": float,
        "num_trades": int,
        "num_wins": int,
        "win_rate": float,
        "max_drawdown_pct": float,
        "equity_curve": [{"date": str, "equity": float}, ...],
        "trade_history": [{...}, ...],
        "params": {...},
        "reason"?: str  # 如果数据不足会返回
    }
    """
    body = request.get_json() or {}

    symbol = body.get('symbol', DEFAULT_SYMBOL)
    start_date = body.get('start_date')
    end_date = body.get('end_date')
    initial_capital = float(body.get('initial_capital', 100000.0))
    grid_count = int(body.get('grid_count', 10))
    spread_type = body.get('spread_type', 'fixed')
    base_ma_key = body.get('base_ma_key', 'MA20')

    # 参数校验
    if grid_count not in (5, 10, 15, 20):
        return jsonify({"error": "grid_count 必须是 5/10/15/20 之一"}), 400
    if spread_type not in ('fixed', 'atr'):
        return jsonify({"error": "spread_type 必须是 'fixed' 或 'atr'"}), 400
    if base_ma_key not in ('MA5', 'MA10', 'MA20', 'MA60'):
        return jsonify({"error": "base_ma_key 必须是 MA5/MA10/MA20/MA60 之一"}), 400
    if initial_capital < 1000:
        return jsonify({"error": "初始资金不能少于1000元"}), 400

    try:
        # 获取历史数据
        df = get_full_data(symbol, start_date=start_date, end_date=end_date)

        # 运行回测
        result = run_grid_backtest(
            df=df,
            initial_capital=initial_capital,
            grid_count=grid_count,
            spread_type=spread_type,
            base_ma_key=base_ma_key,
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"回测执行失败: {str(e)}"}), 500
