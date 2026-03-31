"""
浏览器会话管理：启动 Playwright、持久化 Cookie、反检测配置
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright
from loguru import logger


# 模拟真实 Windows Chrome 的 User-Agent
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

# 注入 JS 脚本，抹掉 webdriver 标识，降低被检测概率
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
window.chrome = { runtime: {} };
"""


class BrowserSession:
    """管理 Playwright 浏览器上下文的生命周期"""

    def __init__(self, config: dict):
        browser_cfg = config.get("browser", {})
        # CI 环境（GitHub Actions）强制无头模式
        is_ci = os.getenv("CI", "").lower() == "true"
        self.headless: bool = True if is_ci else browser_cfg.get("headless", False)
        self.slow_mo: int = 0 if is_ci else browser_cfg.get("slow_mo", 50)
        self.user_data_dir: str = browser_cfg.get("user_data_dir", "./data/browser_profile")

        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None

    def start(self) -> BrowserContext:
        """启动浏览器，返回持久化 Context"""
        profile_path = Path(self.user_data_dir).resolve()
        profile_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"启动浏览器，profile 目录: {profile_path}")

        self._playwright = sync_playwright().start()

        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 对每个新页面注入反检测脚本
        self._context.add_init_script(_STEALTH_SCRIPT)

        logger.success("浏览器启动成功")
        return self._context

    def new_page(self):
        """创建新页面"""
        if self._context is None:
            raise RuntimeError("BrowserSession 未启动，请先调用 start()")
        return self._context.new_page()

    def stop(self):
        """关闭浏览器和 Playwright"""
        if self._context:
            self._context.close()
            logger.info("浏览器上下文已关闭")
        if self._playwright:
            self._playwright.stop()
            logger.info("Playwright 已停止")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
