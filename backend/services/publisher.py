"""
微信公众号发布服务

将技术信号分析内容发布到微信公众号草稿箱。
依赖：npx wenyan CLI
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# 从 memory 中获取的微信配置
WECHAT_APP_ID = "wxb445d745c6038a3c"
WECHAT_APP_SECRET = "4e8e62cd319b58b323dee59d6ef1e4b3"

# 微信公众号封面图（可选）
DEFAULT_COVER = ""


def _run_wenyan(content: str, title: str, cover: str = DEFAULT_COVER) -> dict:
    """
    调用 wenyan CLI 发布到微信公众号草稿箱。

    Returns
    -------
    dict
        {"success": bool, "media_id": str or None, "error": str or None}
    """
    import tempfile, os

    # 写入临时 markdown 文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        env = os.environ.copy()
        env["WECHAT_APP_ID"] = WECHAT_APP_ID
        env["WECHAT_APP_SECRET"] = WECHAT_APP_SECRET

        cmd = [
            "npx", "wenyan", "publish",
            "-f", tmp_path,
            "-t", "lapis",   # 草稿箱
        ]
        if cover:
            cmd += ["--cover", cover]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # 解析 media_id（wenyan 成功时会返回 media_id）
        # 格式类似: Draft saved. Media ID: xxxxx
        media_id = None
        if "media_id" in stdout.lower() or "media_id" in stderr.lower():
            for line in (stdout + "\n" + stderr).split("\n"):
                if "media_id" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        media_id = parts[-1].strip()
                        break

        if result.returncode == 0:
            return {"success": True, "media_id": media_id, "output": stdout}
        else:
            return {"success": False, "media_id": None, "error": stderr or stdout}
    finally:
        Path(tmp_path).unlink()


def build_signal_markdown(signals_text: str, trade_signal: str,
                          symbol: str, symbol_name: str,
                          date: Optional[str] = None) -> str:
    """
    构建微信公众号文章内容的 markdown。

    Parameters
    ----------
    signals_text : str
        格式化后的信号文本（纯文本，带emoji）
    trade_signal : str
        简化交易信号（买入/卖出/观望）
    symbol : str
        股票代码
    symbol_name : str
        股票名称
    date : str, optional
        日期，默认今天
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # 封面图URL（可选，可替换为自己的图床地址）
    cover_url = ""

    # 根据交易信号选择表情
    signal_emoji = {"买入": "🟢", "卖出": "🔴", "观望": "➡️"}.get(trade_signal, "➡️")

    markdown = f"""---
title: 📊 {date} {symbol_name} 技术信号日报
cover: {cover_url}
author: Python工作圈
---

## 📈 每日技术信号

**{symbol_name}（{symbol.upper()}）**

{signals_text}

---

## 🎯 今日交易信号

{signal_emoji} **{trade_signal}**

> 以上信号仅供参考，不构成投资建议。股市有风险，投资需谨慎。

---

*📅 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*📊 数据来源：新浪财经*
"""
    return markdown.strip()


def publish_signal_article(signals_text: str, trade_signal: str,
                           symbol: str, symbol_name: str) -> dict:
    """
    将信号内容发布到微信公众号草稿箱。

    Returns
    -------
    dict
        {"success": bool, "media_id": str or None, "error": str or None}
    """
    markdown = build_signal_markdown(signals_text, trade_signal, symbol, symbol_name)
    return _run_wenyan(markdown, f"{symbol_name} 技术信号日报")
