# 虎扑自动回帖脚本

Python + Playwright 实现的虎扑 BBS 自动回帖工具。

## 环境要求

- Python 3.10+
- Conda 或 venv 虚拟环境（推荐）

## 快速开始

### 1. 创建并激活 Conda 环境

```powershell
conda create -n hupu python=3.11
conda activate hupu
```

### 2. 安装依赖

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. 填写配置

编辑 `config.yaml`，填入账号信息和目标版块：

```yaml
account:
  username: "你的用户名"
  password: "你的密码"

targets:
  - board_url: "https://bbs.hupu.us/bxj"
    keywords: []
    max_threads: 3
```

或者在 `.env` 文件中填写（更安全）：

```
HUPU_USERNAME=你的用户名
HUPU_PASSWORD=你的密码
```

### 4. 编辑回复语料库

在 `data/replies.txt` 中每行写一条回复，脚本会随机选取：

```
哈哈哈，同意
说得有道理
这个角度没想到
```

### 5. 运行

```powershell
# 正常运行
python main.py

# 演练模式（只抓取帖子，不实际回帖）
python main.py --dry-run

# 调试选择器（帮助定位 DOM 元素）
python main.py --debug-selectors
```

## 项目结构

```
fupucomment/
├── main.py                  # 主入口
├── config.yaml              # 配置文件
├── .env                     # 敏感信息（账号密码）
├── requirements.txt
│
├── browser/
│   └── session.py           # 浏览器启动与反检测
│
├── actions/
│   ├── login.py             # 登录逻辑
│   ├── scrape.py            # 帖子列表抓取
│   └── reply.py             # 回帖提交
│
├── strategy/
│   ├── selector.py          # 帖子筛选规则
│   └── content.py           # 回复内容生成（random/template/ai）
│
├── utils/
│   ├── config_loader.py     # 配置加载
│   ├── logger.py            # 日志配置
│   └── delay.py             # 延迟/节奏控制
│
└── data/
    ├── browser_profile/     # 持久化登录态（自动生成）
    ├── replies.txt          # 回复语料库
    └── hupu_bot.log         # 运行日志（自动生成）
```

## 内容生成模式

在 `config.yaml` 的 `content.mode` 中配置：

| 模式 | 说明 |
|------|------|
| `random` | 从 `data/replies.txt` 随机选一条（默认） |
| `template` | 根据帖子标题填充模板 |
| `ai` | 调用 OpenAI API 生成（需设置 `OPENAI_API_KEY`） |

## 选择器调试

虎扑页面更新后，CSS 选择器可能会失效。运行调试模式查找正确选择器：

```powershell
python main.py --debug-selectors
```

然后在打开的浏览器中按 `F12` 打开 DevTools，找到正确的选择器后更新：
- `actions/scrape.py` 中的版块列表选择器
- `actions/reply.py` 中的回复框和提交按钮选择器
- `actions/login.py` 中的登录表单选择器

## 注意事项

- 请遵守虎扑用户协议，合理使用，勿用于刷分/营销
- 建议 `min_delay_seconds` 不低于 30 秒
- 首次运行建议 `headless: false` 以便手动处理验证码
- `.env` 文件不要提交到 Git
