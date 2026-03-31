"""
虎扑自动回帖脚本 - 主入口
用法:
    python main.py                   # 运行一次
    python main.py --config my.yaml  # 指定配置文件
    python main.py --dry-run         # 演练模式（只抓取，不真正回帖）
    python main.py --debug-selectors # 打印页面结构帮助调试选择器
"""
import argparse
import sys

from loguru import logger

from browser.session import BrowserSession
from actions.login import ensure_logged_in
from actions.scrape import get_threads_from_board, fetch_thread_body
from actions.reply import post_reply
from strategy.selector import filter_threads
from strategy.content import generate_reply
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.delay import post_interval


def parse_args():
    parser = argparse.ArgumentParser(description="虎扑自动回帖脚本")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="演练模式，不真正提交回帖")
    parser.add_argument("--debug-selectors", action="store_true", help="打印页面信息帮助调试")
    return parser.parse_args()


def run(config: dict, dry_run: bool = False, debug_selectors: bool = False):
    reply_cfg = config.get("reply", {})
    max_per_run: int = reply_cfg.get("max_per_run", 5)
    min_delay: float = reply_cfg.get("min_delay_seconds", 45.0)
    max_delay: float = reply_cfg.get("max_delay_seconds", 120.0)

    session = BrowserSession(config)
    context = session.start()
    page = context.new_page()

    try:
        # 1. 确保已登录
        logged_in = ensure_logged_in(page, config)
        if not logged_in:
            logger.error("无法登录，脚本终止。请检查账号密码或手动完成验证码。")
            return

        # 2. 调试模式：打印页面信息后退出
        if debug_selectors:
            _debug_mode(page, config)
            return

        # 3. 遍历所有目标版块
        total_replied = 0
        targets = config.get("targets", [])

        if not targets:
            logger.warning("config.yaml 中没有配置 targets 版块，脚本无事可做")
            return

        for board_cfg in targets:
            if total_replied >= max_per_run:
                logger.info(f"已达到本次运行上限 {max_per_run} 帖，停止")
                break

            board_url = board_cfg.get("board_url", "")
            if not board_url:
                continue

            # 3.1 抓取版块帖子列表
            all_threads = get_threads_from_board(page, board_url)

            # 3.2 筛选符合条件的帖子
            selected = filter_threads(all_threads, board_cfg)

            # 3.3 逐帖回复
            for thread in selected:
                if total_replied >= max_per_run:
                    break

                # AI 模式下先抓帖子正文，供 AI 生成上下文回复
                if config.get("content", {}).get("mode") == "ai" and not thread.body:
                    thread.body = fetch_thread_body(page, thread.url)
                    logger.debug(f"抓取正文（前50字）: {thread.body[:50]}")

                # 生成回复内容
                content = generate_reply(thread, config)

                if dry_run:
                    logger.info(f"[演练] 将回复「{thread.title[:30]}」: {content}")
                    total_replied += 1
                    continue

                # 真正发帖
                success = post_reply(page, thread, content)
                if success:
                    total_replied += 1

                # 如果还有下一帖，等待一段时间
                remaining = max_per_run - total_replied
                if remaining > 0 and (selected.index(thread) < len(selected) - 1):
                    post_interval(min_delay, max_delay)

        logger.info(f"本次运行结束，共回复 {total_replied} 帖")

    except KeyboardInterrupt:
        logger.info("用户中断，脚本退出")
    except Exception as e:
        logger.exception(f"脚本运行异常: {e}")
    finally:
        session.stop()


def _debug_mode(page, config: dict):
    """调试模式：访问第一个版块并打印页面结构"""
    targets = config.get("targets", [])
    if not targets:
        logger.warning("没有配置 targets")
        return

    board_url = targets[0].get("board_url", "")
    logger.info(f"调试模式 - 访问: {board_url}")
    page.goto(board_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    logger.info(f"页面 title: {page.title()}")
    logger.info(f"当前 URL: {page.url}")

    # 打印所有 li 元素数量（帮助找帖子列表选择器）
    for tag in ["li", "div", "article", "tr"]:
        count = page.locator(tag).count()
        logger.info(f"  <{tag}> 元素数量: {count}")

    logger.info("浏览器保持打开，请用 DevTools 检查元素后按 Ctrl+C 退出")
    try:
        page.wait_for_timeout(300_000)  # 等待 5 分钟
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    args = parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    setup_logger(config)

    run(config, dry_run=args.dry_run, debug_selectors=args.debug_selectors)
