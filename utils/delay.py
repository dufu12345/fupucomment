"""
延迟工具：模拟人类操作节奏，降低被检测风险
"""
import random
import time
from loguru import logger


def human_delay(min_s: float = 1.0, max_s: float = 3.0):
    """短暂随机停顿，模拟人类思考/操作间隔"""
    duration = random.uniform(min_s, max_s)
    time.sleep(duration)


def post_interval(min_s: float = 45.0, max_s: float = 120.0):
    """
    回帖之间的较长间隔。
    使用正态分布采样，使间隔更自然（大多数集中在均值附近，偶尔很短或很长）。
    """
    mu = (min_s + max_s) / 2
    sigma = (max_s - min_s) / 6
    duration = max(min_s, min(max_s, random.gauss(mu, sigma)))
    logger.info(f"等待 {duration:.1f} 秒后继续下一次回帖...")
    time.sleep(duration)


def read_delay(content_length: int = 200):
    """
    根据帖子内容长度模拟阅读时间。
    假设阅读速度约 300 字/分钟。
    """
    reading_time = content_length / 300 * 60  # 秒
    reading_time = max(3.0, min(reading_time, 30.0))  # 限制在 3~30 秒
    jitter = random.uniform(-1.0, 2.0)
    time.sleep(reading_time + jitter)
