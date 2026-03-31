"""
日志配置：同时输出到控制台和文件
"""
import sys
from loguru import logger


def setup_logger(config: dict):
    """根据 config 初始化 loguru 日志"""
    log_cfg = config.get("logging", {})
    level = log_cfg.get("level", "INFO").upper()
    log_file = log_cfg.get("file", "./data/hupu_bot.log")

    # 移除默认的 handler
    logger.remove()

    # Windows 终端强制 UTF-8，避免 emoji/中文编码报错
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 控制台输出（带颜色）
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    # 文件输出（自动按天轮转，保留 7 天）
    logger.add(
        log_file,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )

    logger.info(f"日志已初始化，级别: {level}，文件: {log_file}")
