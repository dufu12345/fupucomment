"""
登录模块：检测登录状态、执行账号密码登录、处理异常情况

虎扑登录方式：首页点击"登录"按钮后弹出 Modal，
Modal 内表单结构（来自 DevTools 确认）：
  <form id="loginForm">
    <input name="login" autocomplete="username">        ← 用户名/邮箱
    <input name="password" type="password">             ← 密码
    <button type="submit" class="btn btn-primary">登录</button>
    <button type="button" id="authCancelBtn">取消</button>
  </form>
"""
import os
from loguru import logger
from playwright.sync_api import Page, TimeoutError as PWTimeoutError

HUPU_HOME = "https://bbs.hupu.us/"

# 首页右上角"登录"按钮（非 Modal 内的，点击触发弹窗）
# 截图可见右上角有 "登录" 文字链接
_HOME_LOGIN_BTN = "#authPane ~ * a:has-text('登录'), header a:has-text('登录'), .nav a:has-text('登录'), a:has-text('登录'):not(#loginForm *)"

# 登录 Modal 内的表单选择器（DevTools 确认）
_LOGIN_SELECTORS = {
    "username_input": "#loginForm input[name='login'], input[name='login']",
    "password_input": "#loginForm input[name='password'], input[name='password']",
    "submit_btn":     "#loginForm button[type='submit'], button.btn-primary[type='submit']",
}

# 判断未登录：页面顶部能找到"登录"入口且没有用户信息
# 截图显示游客状态时右上角有 "登录" 和 "注册" 按钮
_GUEST_INDICATORS = [
    "text=游客",
    # 右上角的登录按钮（Modal 外）
    ".header a:has-text('登录')",
    "nav a:has-text('登录')",
]

# 判断已登录：找到用户头像或发帖入口
_LOGGED_IN_SELECTORS = [
    "a:has-text('发帖')",
    ".avatar",
    "[class*='avatar']",
    "[class*='userInfo']",
    "[class*='userName']",
    ".user-info",
]


def is_logged_in(page: Page) -> bool:
    """
    检查当前页面是否已登录。
    访问首页，用 JS 直接读取页面上的用户信息区域。
    判断依据：
      - 未登录：右上角出现"游客"文字
      - 已登录：右上角出现用户头像/昵称，"游客"消失
    """
    try:
        page.goto(HUPU_HOME, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5000)

        # 用 JS 读取整个 body 文字，判断是否包含"游客"
        body_text = page.evaluate("() => document.body.innerText")

        if "游客" in body_text:
            logger.info("检测到游客状态，未登录")
            return False

        # 没有"游客"说明已登录（或页面异常，保守认为已登录避免死循环）
        logger.info("未检测到游客标识，判断为已登录")
        return True

    except PWTimeoutError:
        logger.warning("检测登录状态时页面超时")
        return False


def login(page: Page, username: str, password: str) -> bool:
    """
    执行登录流程：
    1. 在首页点击"登录"按钮，弹出 Modal
    2. 在 Modal 内填写用户名和密码
    3. 点击提交
    """
    if not username or not password:
        logger.error("账号或密码为空，请在 .env 文件中填写 HUPU_USERNAME 和 HUPU_PASSWORD")
        return False

    logger.info(f"正在登录账号: {username}")

    try:
        page.goto(HUPU_HOME, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5000)

        # 点击右上角"登录"按钮，触发 Modal 弹出
        # 多次重试，headless 模式下页面渲染可能较慢
        clicked = False
        for attempt in range(3):
            result = page.evaluate("""
                () => {
                    const candidates = Array.from(
                        document.querySelectorAll('a, button, span, div')
                    );
                    for (const el of candidates) {
                        const text = el.textContent.trim();
                        if ((text === '登录' || text === '登 录') && el.offsetParent !== null) {
                            el.click();
                            return el.tagName + '#' + (el.id || '') + '.' + el.className;
                        }
                    }
                    return null;
                }
            """)
            if result:
                logger.debug(f"已点击登录按钮: {result}")
                clicked = True
                break
            logger.debug(f"第 {attempt+1} 次未找到登录按钮，等待重试...")
            page.wait_for_timeout(2000)

        if not clicked:
            logger.warning("JS 方式未找到登录按钮，尝试直接定位输入框")
        logger.debug("等待 Modal 弹出")

        # 等待 Modal 中的用户名输入框出现（headless 下给更多时间）
        username_input = page.locator(_LOGIN_SELECTORS["username_input"]).first
        username_input.wait_for(state="visible", timeout=15_000)

        # 填写用户名
        username_input.click()
        username_input.fill(username)
        page.wait_for_timeout(400)

        # 填写密码
        password_input = page.locator(_LOGIN_SELECTORS["password_input"]).first
        password_input.click()
        password_input.fill(password)
        page.wait_for_timeout(600)

        # 点击提交
        submit_btn = page.locator(_LOGIN_SELECTORS["submit_btn"]).first
        submit_btn.wait_for(state="visible", timeout=5_000)
        submit_btn.click()
        logger.debug("已点击登录提交按钮")

        # 等待 Modal 关闭 / 页面刷新
        page.wait_for_timeout(3000)

        if is_logged_in(page):
            logger.success("登录成功！")
            return True
        else:
            logger.error("登录失败，可能密码错误或触发了验证码")
            _handle_captcha_hint(page)
            return False

    except PWTimeoutError as e:
        logger.error(f"登录超时: {e}")
        return False
    except Exception as e:
        logger.error(f"登录过程出现异常: {e}")
        return False


def ensure_logged_in(page: Page, config: dict) -> bool:
    """
    确保处于登录状态。先检测 Cookie 是否有效，
    无效时才执行账号密码登录。
    """
    if is_logged_in(page):
        return True

    username = os.getenv("HUPU_USERNAME") or config.get("account", {}).get("username", "")
    password = os.getenv("HUPU_PASSWORD") or config.get("account", {}).get("password", "")

    return login(page, username, password)


def _handle_captcha_hint(page: Page):
    """检测是否出现验证码，给出提示并等待用户手动处理"""
    # 只匹配页面可见文字中的验证码关键词，避免 URL/脚本中的 false positive
    visible_text = page.evaluate("() => document.body.innerText").lower()
    captcha_keywords = ["验证码", "滑块验证", "请完成验证", "人机验证"]
    for keyword in captcha_keywords:
        if keyword in visible_text:
            logger.warning(
                "检测到验证码！请在浏览器窗口中手动完成验证，完成后脚本自动继续（最多等 2 分钟）"
            )
            try:
                page.wait_for_function(
                    "() => !document.body.innerText.includes('验证码') "
                    "&& !document.body.innerText.includes('滑块验证')",
                    timeout=120_000,
                )
                logger.info("验证码已处理，继续流程")
            except PWTimeoutError:
                logger.error("等待验证码超时，请重新运行脚本")
            break
