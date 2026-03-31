"""
回帖核心逻辑：进入帖子页面、定位回复框、输入内容、提交

虎扑帖子页回复区结构（DevTools 确认）：
  div#topicReplyEditor
    div#topicReplyDiv
      div#topicReplyBody.editor-input.editor-editable  ← contenteditable，直接可见
  button.btn.btn-primary  ← 提交按钮，文字"提交"
"""
import random
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

from strategy.selector import ThreadInfo
from utils.delay import human_delay, read_delay

# 回复输入框（contenteditable div，页面加载后默认可见）
_REPLY_INPUT = "#topicReplyBody"

# 提交按钮（多个候选，按优先级尝试）
_SUBMIT_BTN_SELECTORS = [
    "#topicReplyEditor button.btn.btn-primary",
    "#topicReplyEditor button[type='submit']",
    "#topicReplyDiv button.btn.btn-primary",
    "button.btn.btn-primary",
    "button:has-text('提交')",
    "button.btn-primary",
]

# 回复成功的判断：输入框被清空 或 出现成功提示
_SUCCESS_INDICATORS = [
    "text=回复成功",
    "text=发表成功",
    ".reply-success",
    ".toast-success",
]


def post_reply(page: Page, thread: ThreadInfo, content: str) -> bool:
    """
    在指定帖子中发表回复。
    返回 True 表示成功，False 表示失败。
    """
    logger.info(f"准备回帖: 「{thread.title[:30]}」")
    logger.info(f"回复内容: {content}")

    try:
        page.goto(thread.url, wait_until="domcontentloaded", timeout=20_000)
        human_delay(2.0, 4.0)

        # 模拟阅读帖子内容（简短停顿，不要等太久）
        read_delay(len(thread.title))

        # 等待回复输入框出现
        reply_box = page.locator(_REPLY_INPUT).first
        reply_box.wait_for(state="visible", timeout=10_000)

        # 滚动到回复框
        reply_box.scroll_into_view_if_needed()
        human_delay(0.5, 1.0)

        # 点击输入框激活
        reply_box.click()
        human_delay(0.5, 1.0)

        # contenteditable div 用 JS 设置内容，再触发 input 事件
        # （直接 type() 也可以，但 JS 方式更稳定，不受输入法干扰）
        page.evaluate(
            """(args) => {
                const el = document.querySelector(args.selector);
                if (!el) return;
                el.focus();
                // 清空现有内容
                el.innerHTML = '';
                // 插入文本节点
                const textNode = document.createTextNode(args.content);
                el.appendChild(textNode);
                // 触发 input / change 事件，让编辑器感知到内容变化
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            {"selector": _REPLY_INPUT, "content": content},
        )

        human_delay(0.8, 1.5)

        # 验证内容确实写进去了
        actual_text = reply_box.inner_text().strip()
        if not actual_text:
            logger.warning("JS 写入后内容为空，改用 type() 方式")
            reply_box.click()
            # 全选清空再输入
            reply_box.press("Control+a")
            reply_box.type(content, delay=_typing_delay_ms())
            human_delay(0.5, 1.0)

        # 点击提交按钮（遍历候选选择器）
        submitted = _click_submit(page)
        if not submitted:
            logger.error("所有提交按钮选择器均失败，回帖中止")
            return False

        # 等待提交响应
        page.wait_for_timeout(3000)

        # 判断是否成功（回复框被清空 = 成功）
        if _check_success(page, reply_box):
            logger.success(f"回帖成功: 「{thread.title[:30]}」")
            return True
        else:
            logger.warning("未检测到明确成功标志，可能已成功，请手动确认")
            return True  # 保守返回 True，避免重复提交

    except PWTimeoutError as e:
        logger.error(f"回帖超时: {e}")
        return False
    except Exception as e:
        logger.error(f"回帖异常: {e}")
        return False


def _click_submit(page: Page) -> bool:
    """遍历候选选择器找到并点击提交按钮"""
    for selector in _SUBMIT_BTN_SELECTORS:
        try:
            btn = page.locator(selector).last
            if btn.count() > 0:
                btn.scroll_into_view_if_needed()
                btn.wait_for(state="visible", timeout=3_000)
                human_delay(0.3, 0.8)
                btn.click()
                logger.debug(f"已点击提交按钮: {selector}")
                return True
        except Exception:
            continue

    # 最后兜底：用 JS 找"提交"文字按钮并点击
    try:
        clicked = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.trim() === '提交' && b.offsetParent !== null);
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)
        if clicked:
            logger.debug("JS 兜底点击了提交按钮")
            return True
    except Exception:
        pass

    return False


def _check_success(page: Page, reply_box) -> bool:
    """判断回帖是否成功：优先检测成功提示，其次检测输入框是否被清空"""
    # 检测 toast / 成功提示
    for indicator in _SUCCESS_INDICATORS:
        try:
            if page.locator(indicator).count() > 0:
                return True
        except Exception:
            continue

    # 输入框被清空说明提交成功
    try:
        text_after = reply_box.inner_text().strip()
        if not text_after:
            return True
    except Exception:
        pass

    return False


def _typing_delay_ms() -> int:
    """随机打字速度（毫秒/字符）"""
    return random.randint(60, 150)
