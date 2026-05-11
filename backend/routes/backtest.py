"""
网格交易回测接口路由模块

提供网格交易策略的回测功能，用户可指定参数运行历史数据回测。
接口路径：POST /api/backtest
"""

from flask import Blueprint, jsonify, request
from backend.services.gold_data import get_full_data
from backend.services.backtest import run_grid_backtest

# 创建回测蓝图
bp = Blueprint('backtest', __name__)

# 默认股票代码：上证黄金ETF（518880）
DEFAULT_SYMBOL = "sh518880"


@bp.route('/api/backtest', methods=['POST'])
def api_backtest():
    """
    运行网格交易回测接口

    请求方式：POST
    请求路径：/api/backtest

    请求参数（JSON Body）：
        symbol (str, 可选): 股票代码，默认 "sh518880"
        start_date (str, 可选): 开始日期，如 "2024-01-01"
        end_date (str, 可选): 结束日期，如 "2024-12-31"
        initial_capital (float, 可选): 初始资金，默认 100000.0
        grid_count (int, 可选): 网格数量，可选值 5/10/15/20，默认 10
        spread_type (str, 可选): 网格间距类型，"fixed"（固定）或 "atr"（动态），默认 "fixed"
        base_ma_key (str, 可选): 基准均线，可选值 MA5/MA10/MA20/MA60，默认 "MA20"

    返回值（JSON）：
        - initial_capital (float): 初始资金
        - final_equity (float): 最终权益
        - total_return (float): 总收益金额
        - total_return_pct (float): 总收益率（%）
        - num_trades (int): 交易次数
        - num_wins (int): 盈利次数
        - win_rate (float): 胜率（%）
        - max_drawdown_pct (float): 最大回撤（%）
        - equity_curve (list): 权益曲线，[{"date": str, "equity": float}, ...]
        - trade_history (list): 交易历史记录
        - params (dict): 回测参数
        - reason (str, 可选): 数据不足时的提示信息

    错误返回：
        HTTP 400: 参数校验失败
        HTTP 500: 回测执行异常
    """
    # 从请求体获取 JSON 数据
    body = request.get_json() or {}

    # 提取请求参数，设置默认值
    symbol = body.get('symbol', DEFAULT_SYMBOL)
    start_date = body.get('start_date')
    end_date = body.get('end_date')
    initial_capital = float(body.get('initial_capital', 100000.0))
    grid_count = int(body.get('grid_count', 10))
    spread_type = body.get('spread_type', 'fixed')
    base_ma_key = body.get('base_ma_key', 'MA20')

    # 参数校验：网格数量必须是合法值
    if grid_count not in (5, 10, 15, 20):
        return jsonify({"error": "grid_count 必须是 5/10/15/20 之一"}), 400
    # 参数校验：间距类型必须是固定或动态
    if spread_type not in ('fixed', 'atr'):
        return jsonify({"error": "spread_type 必须是 'fixed' 或 'atr'"}), 400
    # 参数校验：基准均线必须是合法值
    if base_ma_key not in ('MA5', 'MA10', 'MA20', 'MA60'):
        return jsonify({"error": "base_ma_key 必须是 MA5/MA10/MA20/MA60 之一"}), 400
    # 参数校验：初始资金不能低于 1000 元
    if initial_capital < 1000:
        return jsonify({"error": "初始资金不能少于1000元"}), 400

    try:
        # 获取指定股票的历史数据
        df = get_full_data(symbol, start_date=start_date, end_date=end_date)

        # 运行网格交易回测
        result = run_grid_backtest(
            df=df,
            initial_capital=initial_capital,
            grid_count=grid_count,
            spread_type=spread_type,
            base_ma_key=base_ma_key,
        )

        return jsonify(result)

    except Exception as e:
        # 回测执行异常，返回 500 错误
        return jsonify({"error": f"回测执行失败: {str(e)}"}), 500
