#!/usr/bin/env python3
"""
每日技术信号提醒脚本

Usage:
    python3 scripts/daily_signal.py                 # 分析+发布
    python3 scripts/daily_signal.py --dry-run      # 仅分析，不发布
    python3 scripts/daily_signal.py --symbol sz000300  # 指定标的

定时任务示例（每天 09:35 收盘后分析）：
    35 9 * * 1-5 cd /home/lw/gold_etf_web && ~/akshare_env/bin/python scripts/daily_signal.py >> logs/daily_signal.log 2>&1
"""

import sys
import os
import argparse
from datetime import datetime

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.signal import (
    get_signal_summary,
    format_signal_text,
    get_trading_signal,
    DEFAULT_SYMBOL,
)
from backend.services.publisher import publish_signal_article


def main():
    parser = argparse.ArgumentParser(description="每日技术信号分析")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="股票代码，默认 sh518880")
    parser.add_argument("--dry-run", action="store_true", help="仅分析不发布")
    parser.add_argument("--datalen", type=int, default=60, help="数据天数，默认60")
    args = parser.parse_args()

    symbol = args.symbol
    print(f"\n{'='*60}")
    print(f"📊 每日技术信号分析")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   标的: {symbol.upper()}")
    print(f"   模式: {'仅分析（dry-run）' if args.dry_run else '分析+发布'}")
    print(f"{'='*60}\n")

    try:
        # 1. 获取信号摘要
        print("🔍 正在获取数据并计算指标...")
        summary = get_signal_summary(symbol=symbol, datalen=args.datalen)
        trade_signal = get_trading_signal(summary)
        signals_text = format_signal_text(summary)

        print(f"\n📈 {summary.name}（{symbol.upper()}）")
        print("-" * 40)
        print(signals_text)
        print()
        print(f"🎯 综合交易信号: **{trade_signal}**")
        print()

        # 2. 发布到微信公众号
        if args.dry_run:
            print("⏭️  Dry-run 模式，跳过发布")
        else:
            print("📤 正在发布到微信公众号草稿箱...")
            result = publish_signal_article(
                signals_text=signals_text,
                trade_signal=trade_signal,
                symbol=symbol,
                symbol_name=summary.name,
            )

            if result["success"]:
                print(f"✅ 发布成功！Media ID: {result.get('media_id', 'N/A')}")
            else:
                print(f"❌ 发布失败: {result.get('error', '未知错误')}")
                # 即使发布失败也打印内容，供手动发布
                print("\n📋 手动发布内容：")
                print("-" * 40)
                from backend.services.publisher import build_signal_markdown
                md = build_signal_markdown(signals_text, trade_signal, symbol, summary.name)
                print(md)

        print(f"\n{'='*60}")
        print(f"✅ 分析完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
