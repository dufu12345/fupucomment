"""
配置加载器：读取 config.yaml 并合并 .env 中的环境变量
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv


def load_config(config_path: str = "config.yaml") -> dict:
    """加载并返回配置字典"""
    # 加载 .env（如果存在）
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # .env 中的账号密码优先级高于 config.yaml
    env_username = os.getenv("HUPU_USERNAME")
    env_password = os.getenv("HUPU_PASSWORD")
    if env_username:
        config.setdefault("account", {})["username"] = env_username
    if env_password:
        config.setdefault("account", {})["password"] = env_password

    return config
