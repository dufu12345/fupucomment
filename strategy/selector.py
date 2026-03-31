"""
帖子筛选策略：决定哪些帖子值得回复
"""
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ThreadInfo:
    """代表一个帖子的基本信息"""
    title: str
    url: str
    reply_count: int = 0
    author: str = ""
    is_pinned: bool = False
    already_replied: bool = False
    body: str = ""   # 帖子正文（进入帖子页后抓取，供 AI 生成上下文回复）


def should_reply(thread: ThreadInfo, board_config: dict) -> bool:
    """
    判断是否应该回复某个帖子。
    规则：
      1. 跳过置顶帖（一般是公告）
      2. 跳过自己已回复过的帖子（如配置了 skip_if_already_replied）
      3. 关键词过滤：配置了关键词则标题必须包含其中至少一个
      4. 回复数过多的帖子（>500）跳过，太热门容易被淹没
    """
    skip_if_replied = board_config.get("skip_if_already_replied", True)

    if thread.is_pinned:
        logger.debug(f"跳过置顶帖: {thread.title}")
        return False

    if skip_if_replied and thread.already_replied:
        logger.debug(f"跳过已回复帖: {thread.title}")
        return False

    keywords = board_config.get("keywords", [])
    if keywords:
        title_lower = thread.title.lower()
        matched = any(kw.lower() in title_lower for kw in keywords)
        if not matched:
            logger.debug(f"关键词不匹配，跳过: {thread.title}")
            return False

    if thread.reply_count > 500:
        logger.debug(f"帖子过热（{thread.reply_count}回复），跳过: {thread.title}")
        return False

    return True


def filter_threads(threads: list[ThreadInfo], board_config: dict) -> list[ThreadInfo]:
    """过滤帖子列表，返回符合条件的帖子"""
    selected = [t for t in threads if should_reply(t, board_config)]
    max_threads = board_config.get("max_threads", 3)
    result = selected[:max_threads]
    logger.info(f"筛选结果: {len(threads)} 个帖子中选出 {len(result)} 个准备回复")
    return result
