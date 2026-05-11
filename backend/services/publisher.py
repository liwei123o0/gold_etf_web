"""
微信公众号发布服务模块

本模块提供将技术信号分析内容发布到微信公众号草稿箱的功能。
主要功能包括：
1. 构建 Markdown 格式的技术信号文章内容
2. 调用 wenyan CLI 工具将文章发布到微信公众号草稿箱

依赖要求：
- npx wenyan CLI 工具
- 微信公众号开发者账号（需配置 App ID 和 App Secret）

使用示例：
    from services.publisher import publish_signal_article
    
    result = publish_signal_article(
        signals_text="技术信号内容...",
        trade_signal="买入",
        symbol="518880",
        symbol_name="黄金ETF"
    )
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# 微信公众号开发者配置信息
# 注意：实际生产环境中应从环境变量或配置文件中获取，避免硬编码
WECHAT_APP_ID = "wxb445d745c6038a3c"
WECHAT_APP_SECRET = "4e8e62cd319b58b323dee59d6ef1e4b3"

# 微信公众号文章默认封面图 URL（可选配置）
DEFAULT_COVER = ""


def _run_wenyan(content: str, title: str, cover: str = DEFAULT_COVER) -> dict:
    """
    调用 wenyan CLI 工具发布文章到微信公众号草稿箱。

    该函数是内部辅助函数，负责执行 wenyan 命令行工具，
    将 Markdown 格式的文章内容发布到微信公众号草稿箱。

    参数
    ----
    content : str
        Markdown 格式的文章内容，包含标题、正文等完整内容。
    title : str
        文章标题，用于日志记录和错误提示。
    cover : str, 可选
        文章封面图的 URL 地址，默认为空字符串（不设置封面）。

    返回值
    ------
    dict
        包含发布结果的字典，格式如下：
        - success (bool): 发布是否成功
        - media_id (str | None): 成功时返回微信素材 ID，失败时为 None
        - output (str): 成功时的命令输出信息（仅成功时存在）
        - error (str | None): 失败时的错误信息（仅失败时存在）

    异常
    ----
    该函数内部捕获所有异常，通过返回值字典传递错误信息，
    不会向外抛出异常。

    注意
    ----
    - 函数会创建临时 Markdown 文件，执行完成后自动清理
    - 命令执行超时时间为 60 秒
    - 需要确保系统已安装 Node.js 和 npx 工具
    """
    import tempfile, os

    # 创建临时 Markdown 文件用于存储文章内容
    # 使用 delete=False 以便在命令执行期间文件不被删除
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(content)
        tmp_path = f.name

    try:
        # 构建环境变量，传递微信公众号认证信息
        env = os.environ.copy()
        env["WECHAT_APP_ID"] = WECHAT_APP_ID
        env["WECHAT_APP_SECRET"] = WECHAT_APP_SECRET

        # 构建 wenyan 命令行参数
        cmd = [
            "npx", "wenyan", "publish",  # 调用 wenyan 发布命令
            "-f", tmp_path,              # 指定输入文件路径
            "-t", "lapis",               # 发布目标：草稿箱（lapis）
        ]
        # 如果提供了封面图 URL，添加封面参数
        if cover:
            cmd += ["--cover", cover]

        # 执行 wenyan 命令，捕获输出
        # timeout=60 设置 60 秒超时限制
        result = subprocess.run(
            cmd,
            capture_output=True,  # 捕获标准输出和标准错误
            text=True,            # 以文本模式返回输出
            env=env,              # 传递环境变量
            timeout=60,           # 超时时间
        )

        # 获取命令执行的标准输出和标准错误
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # 解析返回结果中的 media_id
        # wenyan 成功时会返回类似 "Draft saved. Media ID: xxxxx" 的信息
        media_id = None
        if "media_id" in stdout.lower() or "media_id" in stderr.lower():
            # 遍历输出行，查找包含 media_id 的行
            for line in (stdout + "\n" + stderr).split("\n"):
                if "media_id" in line.lower():
                    # 提取 media_id 值（取冒号后的内容）
                    parts = line.split(":")
                    if len(parts) >= 2:
                        media_id = parts[-1].strip()
                        break

        # 根据命令返回码判断执行结果
        if result.returncode == 0:
            # 返回码为 0 表示执行成功
            return {"success": True, "media_id": media_id, "output": stdout}
        else:
            # 返回码非 0 表示执行失败，返回错误信息
            return {"success": False, "media_id": None, "error": stderr or stdout}
    finally:
        # 清理临时文件，确保不留垃圾文件
        Path(tmp_path).unlink()


def build_signal_markdown(signals_text: str, trade_signal: str,
                          symbol: str, symbol_name: str,
                          date: Optional[str] = None) -> str:
    """
    构建微信公众号技术信号文章的 Markdown 内容。

    根据提供的技术信号数据和交易信号，生成符合微信公众号格式的
    Markdown 文章内容，包含标题、信号详情、交易建议等。

    参数
    ----
    signals_text : str
        格式化后的技术信号文本内容。
        通常包含多个技术指标的信号描述，支持 emoji 表情符号。
        例如："RSI(14): 65.2 ↗ 超买区间\\nMACD: 金叉 ↑"
    trade_signal : str
        简化的交易信号建议，取值范围：买入、卖出、观望。
        用于生成醒目的交易建议区块。
    symbol : str
        股票/ETF 代码，如 "518880"、"159934" 等。
        文章中会显示为大写格式。
    symbol_name : str
        股票/ETF 名称，如 "黄金ETF"、"白银ETF" 等。
        用于文章标题和正文显示。
    date : str, 可选
        信号日期，格式为 "YYYY-MM-DD"。
        如果不提供，默认使用当前日期。

    返回值
    ------
    str
        完整的 Markdown 格式文章内容，包含：
        - YAML 前置信息（标题、封面、作者）
        - 技术信号详情区块
        - 交易信号建议区块
        - 免责声明
        - 生成时间和数据来源信息

    示例
    ----
    >>> markdown = build_signal_markdown(
    ...     signals_text="RSI: 65.2 ↗",
    ...     trade_signal="买入",
    ...     symbol="518880",
    ...     symbol_name="黄金ETF",
    ...     date="2024-01-15"
    ... )
    """
    # 如果未提供日期，使用当前日期
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    # 封面图 URL（可替换为自己的图床地址）
    cover_url = ""

    # 根据交易信号类型选择对应的 emoji 图标
    # 买入使用绿色圆点，卖出使用红色圆点，观望使用蓝色箭头
    signal_emoji = {"买入": "🟢", "卖出": "🔴", "观望": "➡️"}.get(trade_signal, "➡️")

    # 构建 Markdown 文章内容
    # 包含 YAML 前置信息和正文内容
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
    # 返回去除首尾空白后的 Markdown 内容
    return markdown.strip()


def publish_signal_article(signals_text: str, trade_signal: str,
                           symbol: str, symbol_name: str) -> dict:
    """
    将技术信号内容发布到微信公众号草稿箱。

    这是本模块的主要对外接口函数，整合了 Markdown 内容构建
    和 wenyan CLI 调用两个步骤，完成文章发布流程。

    参数
    ----
    signals_text : str
        格式化后的技术信号文本内容。
        包含各技术指标的信号描述和分析结果。
    trade_signal : str
        简化的交易信号建议，取值范围：买入、卖出、观望。
    symbol : str
        股票/ETF 代码，如 "518880"。
    symbol_name : str
        股票/ETF 名称，如 "黄金ETF"。

    返回值
    ------
    dict
        包含发布结果的字典，格式如下：
        - success (bool): 发布是否成功
        - media_id (str | None): 成功时返回微信素材 ID
        - output (str): 成功时的输出信息（仅成功时存在）
        - error (str | None): 失败时的错误信息（仅失败时存在）

    使用示例
    --------
    >>> result = publish_signal_article(
    ...     signals_text="RSI(14): 65.2 ↗\\nMACD: 金叉 ↑",
    ...     trade_signal="买入",
    ...     symbol="518880",
    ...     symbol_name="黄金ETF"
    ... )
    >>> if result["success"]:
    ...     print(f"发布成功，media_id: {result['media_id']}")
    ... else:
    ...     print(f"发布失败: {result['error']}")

    注意事项
    --------
    - 发布成功后，文章会保存在微信公众号后台的草稿箱中
    - 需要手动登录微信公众号后台进行预览和发布操作
    - 确保已正确配置微信公众号的 App ID 和 App Secret
    """
    # 步骤1：构建 Markdown 格式的文章内容
    markdown = build_signal_markdown(signals_text, trade_signal, symbol, symbol_name)
    
    # 步骤2：调用 wenyan CLI 发布文章到草稿箱
    return _run_wenyan(markdown, f"{symbol_name} 技术信号日报")
