"""
帖子抓取模块：从版块列表页获取帖子信息
注意：选择器基于虎扑 bbs.hupu.us 页面结构，若页面改版需要更新。
"""
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from strategy.selector import ThreadInfo
from utils.delay import human_delay

# ──────────────────── 版块列表页选择器 ────────────────────
# 每行帖子的容器
# bbs.hupu.us 新版页面结构：帖子列表在 ul > li 里
_THREAD_ROW_SELECTOR = (
    "li.thread, "
    "section[aria-label='thread list'] li, "
    "ul.for-list li"
)

# 帖子标题按钮（DevTools 确认：<button class="u-link" data-open-topic="ID">标题</button>）
_TITLE_BTN_SELECTOR = "button.u-link[data-open-topic]"

# 帖子回复数（在 .t-meta 区域里）
_REPLY_COUNT_SELECTOR = (
    ".t-reply, "
    ".reply-count, "
    "[class*='reply']"
)

# 帖子作者
_AUTHOR_SELECTOR = (
    ".t-author, "
    ".t-name, "
    "[class*='author'] a, "
    "a[href*='/user-']"
)

# 置顶标记
_PINNED_SELECTOR = ".icon-top, [class*='isTop'], span:has-text('置顶'), .t-tag:has-text('置顶')"

# 自己用户名（从右上角用户信息区域读取）
_CURRENT_USER_SELECTOR = (
    ".user-info .name, "
    "[class*='userName'], "
    "[class*='userInfo'] span, "
    ".avatar + span"
)


def get_threads_from_board(page: Page, board_url: str) -> list[ThreadInfo]:
    """
    访问版块列表页，抓取当前页所有帖子的基本信息。
    返回 ThreadInfo 列表。
    """
    logger.info(f"正在抓取版块: {board_url}")
    threads: list[ThreadInfo] = []

    try:
        page.goto(board_url, wait_until="domcontentloaded", timeout=30_000)
        # headless 模式下页面渲染更慢，等久一些
        page.wait_for_timeout(5000)

        # 打印当前 URL 和页面标题，确认跳转正确
        logger.info(f"当前 URL: {page.url}，页面标题: {page.title()}")

        # 读取当前登录用户名（用于判断是否已回复）
        current_user = _get_current_username(page)

        # 尝试多种选择器找帖子列表
        rows = page.locator(_THREAD_ROW_SELECTOR).all()

        # 如果主选择器找不到，尝试更宽泛的备选
        if not rows:
            fallback_selectors = [
                "li",
                "ul li",
                "article",
                "div[data-topic-id]",
                "[data-open-topic]",
            ]
            for sel in fallback_selectors:
                rows = page.locator(sel).all()
                if rows:
                    logger.info(f"主选择器未匹配，备选 '{sel}' 找到 {len(rows)} 个元素")
                    break

        if not rows:
            logger.warning(f"未找到帖子列表，可能选择器需要更新")
            # 打印页面结构帮助调试
            body_text = page.evaluate("() => document.body.innerText.substring(0, 500)")
            logger.warning(f"页面文本（前500字）: {body_text}")
            html_snippet = page.evaluate("() => document.body.innerHTML.substring(0, 1000)")
            logger.warning(f"页面 HTML（前1000字）: {html_snippet}")
            return []

        logger.info(f"找到 {len(rows)} 个帖子条目")

        # 调试：打印前两行的 innerHTML，帮助确认选择器
        for i, row in enumerate(rows[:2]):
            try:
                html = row.inner_html()
                logger.debug(f"[帖子行 {i}] HTML 片段: {html[:800]}")
            except Exception:
                pass

        for row in rows:
            try:
                thread = _parse_thread_row(row, current_user)
                if thread:
                    threads.append(thread)
            except Exception as e:
                logger.debug(f"解析帖子行失败，跳过: {e}")
                continue

        # 如果一个都没解析出来，打印更多信息
        if not threads and rows:
            logger.warning("所有帖子行均解析失败，请查看上方 DEBUG 日志确认选择器")
            logger.warning(f"当前标题选择器: {_TITLE_LINK_SELECTOR}")

    except PWTimeoutError:
        logger.error(f"访问版块超时: {board_url}")
    except Exception as e:
        logger.error(f"抓取版块异常: {e}")

    logger.info(f"成功解析 {len(threads)} 个帖子")
    return threads


def _parse_thread_row(row, current_user: str) -> ThreadInfo | None:
    """从单行帖子 DOM 元素中提取信息"""
    # 获取标题按钮（<button class="u-link" data-open-topic="ID">）
    title_el = row.locator(_TITLE_BTN_SELECTOR).first
    if title_el.count() == 0:
        return None

    title = title_el.inner_text().strip()
    topic_id = title_el.get_attribute("data-open-topic") or ""

    if not title or not topic_id:
        return None

    # 根据 topic_id 构造帖子 URL（虎扑帖子格式：/?t={id}）
    href = f"https://bbs.hupu.us/?t={topic_id}"

    # 回复数
    reply_count = 0
    reply_el = row.locator(_REPLY_COUNT_SELECTOR).first
    if reply_el.count() > 0:
        try:
            reply_count = int(reply_el.inner_text().strip().replace(",", ""))
        except ValueError:
            pass

    # 作者
    author = ""
    author_el = row.locator(_AUTHOR_SELECTOR).first
    if author_el.count() > 0:
        author = author_el.inner_text().strip()

    # 是否置顶
    is_pinned = row.locator(_PINNED_SELECTOR).count() > 0

    # 是否自己已回复（列表页通常不显示，先设 False，进入帖子后再检测）
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
            ".post-content",
            "[class*='topicContent']",
            "[class*='topic-body']",
            ".content-wrap",
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
