"""
回复内容生成策略：随机语料库 / 模板填空 / AI 生成

AI 模式支持：
  - DeepSeek API（推荐，便宜、中文好）：https://platform.deepseek.com
  - OpenAI API：https://platform.openai.com
"""
import os
import random
from pathlib import Path
from loguru import logger

from strategy.selector import ThreadInfo


def generate_reply(thread: ThreadInfo, config: dict) -> str:
    """
    根据配置的 content.mode 生成回复内容。
    mode:
      random   - 从语料库文件随机选一条
      template - 根据帖子标题填充模板
      ai       - 调用 AI API 生成（DeepSeek 或 OpenAI）
    """
    mode = config.get("content", {}).get("mode", "random")

    if mode == "random":
        reply = _random_reply(config)
    elif mode == "template":
        reply = _template_reply(thread)
    elif mode == "ai":
        reply = _ai_reply(thread, config)
    else:
        logger.warning(f"未知的 content.mode: {mode}，使用 random 模式")
        reply = _random_reply(config)

    return _ensure_min_length(reply)


_MIN_REPLY_LENGTH = 10  # 虎扑要求回帖至少 10 个字


def _ensure_min_length(reply: str) -> str:
    """确保回复不少于 10 个字，不够就补充"""
    if len(reply) >= _MIN_REPLY_LENGTH:
        return reply
    suffixes = [
        "，确实是这样的",
        "，感觉说得有道理",
        "，这个我也赞同",
        "，值得好好想想",
    ]
    reply = reply.rstrip("。，！？.!?,") + random.choice(suffixes)
    return reply


# ──────────────────────────── 策略实现 ────────────────────────────

def _random_reply(config: dict) -> str:
    """从语料库文件随机选一条回复"""
    replies_file = config.get("content", {}).get("replies_file", "./data/replies.txt")
    file_path = Path(replies_file)

    if not file_path.exists():
        return "说得有道理"

    lines = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return random.choice(lines) if lines else "顶一下"


def _template_reply(thread: ThreadInfo) -> str:
    """根据帖子标题生成模板回复"""
    templates = [
        "关于{title}这个问题，楼主分析得很到位",
        "{title}，确实有道理",
        "看了楼主说的{title}，感觉很有意思",
    ]
    short_title = thread.title[:10]
    return random.choice(templates).format(title=short_title)


def _ai_reply(thread: ThreadInfo, config: dict) -> str:
    """
    调用 AI API 根据帖子标题和正文生成自然回复。
    优先级：Groq（免费）> Gemini > DeepSeek > OpenAI > 随机降级
    """
    groq_key     = os.getenv("GROQ_API_KEY", "")
    gemini_key   = os.getenv("GEMINI_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    openai_key   = os.getenv("OPENAI_API_KEY", "")

    if groq_key:
        return _call_groq(thread, groq_key, config)
    elif gemini_key:
        return _call_gemini(thread, gemini_key, config)
    elif deepseek_key:
        return _call_deepseek(thread, deepseek_key, config)
    elif openai_key:
        return _call_openai(thread, openai_key, config)
    else:
        logger.error("AI 模式需要在 .env 中设置 GROQ_API_KEY / GEMINI_API_KEY / DEEPSEEK_API_KEY 之一")
        logger.warning("降级使用随机回复")
        return _random_reply(config)


def _build_prompt(thread: ThreadInfo) -> str:
    """构建发给 AI 的 prompt"""
    context = f"帖子标题：{thread.title}"
    if thread.body:
        context += f"\n\n帖子内容（前300字）：\n{thread.body}"

    return f"""你是一个虎扑篮球论坛的普通用户，正在看一个帖子。

{context}

请根据以上内容，写一条自然的中文跟帖回复。
要求：
1. 口语化、自然，像真人在论坛发言
2. 长度必须在 15-50 个中文字之间（严格不少于 15 字！论坛要求至少 10 字）
3. 内容要和帖子有关联，发表自己的看法或感想
4. 不要含广告、链接、或政治敏感内容
5. 只输出回复内容本身，不要加引号、不要解释、不要重复标题"""


def _call_groq(thread: ThreadInfo, api_key: str, config: dict) -> str:
    """
    调用 Groq API（完全免费，无需绑卡）
    使用 llama-3.3-70b-versatile 模型，中文效果好，速度极快
    """
    try:
        from openai import OpenAI  # Groq 兼容 OpenAI SDK

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": _build_prompt(thread)}],
            max_tokens=80,
            temperature=0.9,
        )
        reply = response.choices[0].message.content.strip().strip('"').strip("'").strip("「」")
        logger.debug(f"Groq 生成回复: {reply}")
        return reply
    except ImportError:
        logger.error("缺少 openai 包，请运行: pip install openai")
        return _random_reply(config)
    except Exception as e:
        logger.error(f"Groq API 调用失败: {e}，降级到随机回复")
        return _random_reply(config)


def _call_gemini(thread: ThreadInfo, api_key: str, config: dict) -> str:
    """
    调用 Gemini API（新版 google-genai SDK）
    遇到 429 速率限制时自动等待后重试，最多重试 2 次。
    """
    import time, re

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(thread)

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=80,
                        temperature=0.9,
                    ),
                )
                reply = response.text.strip().strip('"').strip("'").strip("「」")
                logger.debug(f"Gemini 生成回复: {reply}")
                return reply

            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    # 从错误信息里提取建议等待时间
                    match = re.search(r"retry in (\d+\.?\d*)", err)
                    wait = float(match.group(1)) if match else 20.0
                    wait = min(wait + 2, 60.0)  # 额外多等 2 秒，最多 60 秒

                    if attempt < max_retries:
                        logger.warning(f"Gemini 速率限制，等待 {wait:.0f} 秒后重试（第 {attempt+1}/{max_retries} 次）")
                        time.sleep(wait)
                        continue
                    else:
                        logger.error("Gemini 重试次数耗尽，降级到随机回复")
                        return _random_reply(config)
                else:
                    raise e

    except ImportError:
        logger.error("缺少 google-genai 包，请运行: pip install google-genai")
        return _random_reply(config)
    except Exception as e:
        logger.error(f"Gemini API 调用失败: {e}，降级到随机回复")
        return _random_reply(config)


def _call_deepseek(thread: ThreadInfo, api_key: str, config: dict) -> str:
    """调用 DeepSeek API"""
    try:
        from openai import OpenAI  # DeepSeek 兼容 OpenAI SDK

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": _build_prompt(thread)}],
            max_tokens=80,
            temperature=0.9,
        )
        reply = response.choices[0].message.content.strip()
        # 去掉 AI 可能加的引号
        reply = reply.strip('"').strip("'").strip("「」")
        logger.debug(f"DeepSeek 生成回复: {reply}")
        return reply
    except ImportError:
        logger.error("缺少 openai 包，请运行: pip install openai")
        return _random_reply(config)
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}，降级到随机回复")
        return _random_reply(config)


def _call_openai(thread: ThreadInfo, api_key: str, config: dict) -> str:
    """调用 OpenAI API"""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": _build_prompt(thread)}],
            max_tokens=80,
            temperature=0.9,
        )
        reply = response.choices[0].message.content.strip().strip('"').strip("'").strip("「」")
        logger.debug(f"OpenAI 生成回复: {reply}")
        return reply
    except ImportError:
        logger.error("缺少 openai 包，请运行: pip install openai")
        return _random_reply(config)
    except Exception as e:
        logger.error(f"OpenAI API 调用失败: {e}，降级到随机回复")
        return _random_reply(config)
