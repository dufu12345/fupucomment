"""
帖子抓取模块：从版块列表页获取帖子信息
注意：选择器基于虎扑 bbs.hupu.us 页面结构，若页面改版需要更新。
"""
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from strategy.selector import ThreadInfo
from utils.delay import human_delay

# ──────────────────── 版块列表页选择器 ────────────────────
# 2026-04 新版页面结构:
#   <section class="feed" aria-label="Thread list">
#     <ul> <li class="thread"> ... </li> </ul>
#   </section>
_THREAD_ROW_SELECTOR = "li.thread"

# 帖子标题按钮: <button class="u-link" data-open-topic="116">标题</button>
_TITLE_BTN_SELECTOR = "button.u-link[data-open-topic]"

# 帖子元数据区（回复数、浏览数等）
_STATS_SELECTOR = ".t-stats span, .t-meta span, .t-right span"

# 帖子作者（头像旁的用户名链接）
_AUTHOR_SELECTOR = ".t-avatar, .t-meta a, a[href*='/user/']"

# 置顶/精华标记
_PINNED_SELECTOR = ".t-tag:has-text('置顶'), .badge:has-text('置顶'), .pin-icon"

# 当前登录用户名
_CURRENT_USER_SELECTOR = ".topbar a[href*='/user/'], .user-name, .avatar-wrap + span"


def get_threads_from_board(page: Page, board_url: str) -> list[ThreadInfo]:
    """
    访问版块列表页，抓取当前页所有帖子的基本信息。
    返回 ThreadInfo 列表。
    """
    logger.info(f"正在抓取版块: {board_url}")
    threads: list[ThreadInfo] = []

    try:
        page.goto(board_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5000)

        logger.info(f"当前 URL: {page.url}，页面标题: {page.title()}")

        current_user = _get_current_username(page)

        # 保存当前版块路径，用于拼接帖子 URL（如 /bxj）
        board_path = page.url.split("?")[0].rstrip("/")

        rows = page.locator(_THREAD_ROW_SELECTOR).all()

        if not rows:
            logger.warning("未找到帖子列表（li.thread），可能选择器需要更新")
            body_text = page.evaluate("() => document.body.innerText.substring(0, 500)")
            logger.warning(f"页面文本（前500字）: {body_text}")
            return []

        logger.info(f"找到 {len(rows)} 个帖子条目")

        for row in rows:
            try:
                thread = _parse_thread_row(row, current_user, board_path)
                if thread:
                    threads.append(thread)
            except Exception as e:
                logger.debug(f"解析帖子行失败，跳过: {e}")
                continue

        if not threads and rows:
            logger.warning("所有帖子行均解析失败，尝试打印第一行 HTML 辅助调试")
            try:
                logger.warning(f"第一行 HTML: {rows[0].inner_html()[:500]}")
            except Exception:
                pass

    except PWTimeoutError:
        logger.error(f"访问版块超时: {board_url}")
    except Exception as e:
        logger.error(f"抓取版块异常: {e}")

    logger.info(f"成功解析 {len(threads)} 个帖子")
    return threads


def _parse_thread_row(row, current_user: str, board_path: str) -> ThreadInfo | None:
    """从单行帖子 DOM 元素中提取信息"""
    title_el = row.locator(_TITLE_BTN_SELECTOR).first
    if title_el.count() == 0:
        return None

    title = title_el.inner_text().strip()
    topic_id = title_el.get_attribute("data-open-topic") or ""

    if not title or not topic_id:
        return None

    # URL 格式: https://bbs.hupu.us/bxj?t=116
    href = f"{board_path}?t={topic_id}"

    # 回复数：尝试从 stats 区域提取第一个纯数字
    reply_count = 0
    stats_els = row.locator(_STATS_SELECTOR).all()
    for el in stats_els:
        try:
            text = el.inner_text().strip().replace(",", "")
            if text.isdigit():
                reply_count = int(text)
                break
        except Exception:
            continue

    # 作者：从 data-user 属性或链接文本提取
    author = ""
    avatar_el = row.locator("[data-user]").first
    if avatar_el.count() > 0:
        author = avatar_el.get_attribute("data-user") or ""
    if not author:
        author_el = row.locator(_AUTHOR_SELECTOR).first
        if author_el.count() > 0:
            author = author_el.inner_text().strip()

    is_pinned = row.locator(_PINNED_SELECTOR).count() > 0
    already_replied = (author == current_user) if current_user else False

    return ThreadInfo(
        title=title,
        url=href,
        reply_count=reply_count,
        author=author,
        is_pinned=is_pinned,
        already_replied=already_replied,
    )


def check_already_replied(page: Page, thread_url: str, current_user: str) -> bool:
    """
    进入帖子页，检查自己是否已经回复过。
    适用于需要精确判断时调用（比列表页判断更准确）。
    """
    if not current_user:
        return False
    try:
        page.goto(thread_url, wait_until="domcontentloaded", timeout=15_000)
        human_delay(1.0, 2.0)
        # 查找页面中包含当前用户名的回复
        user_replies = page.locator(f"[class*='author']:has-text('{current_user}')").count()
        return user_replies > 0
    except Exception:
        return False


def _get_current_username(page: Page) -> str:
    """从页面顶部导航栏读取当前登录用户名"""
    try:
        el = page.locator(_CURRENT_USER_SELECTOR).first
        if el.count() > 0:
            return el.inner_text().strip()
    except Exception:
        pass
    return ""


def fetch_thread_body(page: Page, thread_url: str) -> str:
    """
    进入帖子页，抓取楼主第一楼的正文内容，供 AI 生成上下文回复。
    返回最多 300 字的正文文本，失败时返回空字符串。
    """
    try:
        page.goto(thread_url, wait_until="domcontentloaded", timeout=15_000)
        human_delay(1.0, 2.0)

        # 虎扑帖子正文选择器（楼主第一楼内容区域）
        body_selectors = [
            ".topic-content",
            ".topic.thread .post-content",
            ".topic.page .content",
            ".post-content",
            "[class*='topicContent']",
            "[class*='topic-body']",
            ".content-wrap",
            ".topic.thread",
        ]
        for selector in body_selectors:
            el = page.locator(selector).first
            if el.count() > 0:
                text = el.inner_text().strip()
                if text:
                    return text[:300]

        # 兜底：取页面主体文本前 300 字
        return page.locator("main, article, #app").first.inner_text().strip()[:300]

    except Exception as e:
        logger.debug(f"抓取帖子正文失败: {e}")
        return ""


def _debug_page_snapshot(page: Page):
    """调试用：打印页面 title 和部分 HTML，帮助定位选择器问题"""
    logger.debug(f"当前页面 title: {page.title()}")
    logger.debug(f"当前 URL: {page.url}")
    body_text = page.locator("body").inner_text()[:300]
    logger.debug(f"页面内容（前300字）: {body_text}")
