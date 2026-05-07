[English](README.md) | 中文

# 虎扑自动回帖脚本（仅用于学习）

Python + Playwright 实现的虎扑 BBS 自动回帖工具，支持 AI 生成回复内容、GUI 一键运行、Windows 定时任务自动执行。

---

## 给非开发者：下载即用

**已打包的 Windows 程序**放在 [GitHub Releases](https://github.com/dufu12345/fupucomment/releases)。网页上绿色的 **Code** 只有源码，没有 exe；需要可执行文件请打开 Releases。

1. **下载**：在 Releases 里下载最新的 zip（由维护者用本地 `build.bat` 打包后上传）。
2. **解压**：解压到任意文件夹（路径尽量不用中文，可减少个别环境下的兼容问题）。
3. **使用**：按压缩包内说明配置 `.env`（通常是把 `.env.example` 复制为 `.env` 并填写），双击 `HupuBot.exe`。

若 Releases 里暂时没有附件，说明尚未发布构建版本；可从本仓库拉源码，本地运行 `build.bat` 生成 `dist\HupuBot\`（见下文「打包为 exe」）。

---

## 项目结构

```
fupucomment/
├── main.py                 # 主入口（命令行运行）
├── launcher.py             # GUI 启动器（打包为 exe 后双击运行）
├── config.yaml             # 配置文件：版块 URL、回帖数、延迟、模式等
├── .env.example            # 凭据模板（复制为 .env 后填值）
├── .env                    # 敏感信息：虎扑账号密码、AI API Key（不上传 Git）
├── requirements.txt        # Python 依赖列表
│
├── actions/                # 【动作层】浏览器上的具体操作
│   ├── login.py            #   登录：检测登录状态、打开登录弹窗、填账号密码
│   ├── scrape.py           #   抓取：从版块页获取帖子列表、抓取帖子正文
│   └── reply.py            #   回帖：定位回复框、填内容、点发表
│
├── browser/                # 【浏览器层】Playwright 生命周期管理
│   └── session.py          #   启动/关闭浏览器、持久化 Cookie、反检测（UA/webdriver）
│
├── strategy/               # 【策略层】决定"回什么"和"回哪个"
│   ├── selector.py         #   筛选：根据关键词、回复数过滤帖子
│   └── content.py          #   内容生成：random / template / AI（Groq/Gemini/DeepSeek/OpenAI）
│
├── utils/                  # 【工具层】通用辅助
│   ├── config_loader.py    #   加载 config.yaml + .env 合并配置
│   ├── logger.py           #   loguru 日志初始化（控制台 + 文件）
│   └── delay.py            #   随机延迟：模拟人类阅读/操作节奏
│
├── data/                   # 【数据目录】运行时产生的文件
│   ├── replies.txt         #   随机回复语料库（random 模式用）
│   ├── browser_profile/    #   Playwright 持久化浏览器 Cookie（自动生成）
│   └── hupu_bot.log        #   运行日志（自动生成）
│
├── run.bat                 # Windows 一键运行脚本（conda activate + python main.py）
├── setup_task.bat          # 创建 Windows 定时任务（每天 22:00 自动执行）
└── build.bat               # PyInstaller 打包脚本（生成 exe）
```

---

## 调用流程

```
用户双击 HupuBot.exe（GUI）或运行 python main.py（CLI）
    │
    ├── utils/config_loader.py   ← 读取 config.yaml + .env
    ├── utils/logger.py          ← 初始化日志
    │
    ▼
browser/session.py               ← 启动 Playwright 浏览器（反检测）
    │
    ▼
actions/login.py                 ← 自动登录虎扑
    │
    ▼
actions/scrape.py                ← 抓取帖子列表 + 正文
    │
    ▼
strategy/selector.py             ← 筛选要回复的帖子
    │
    ▼
strategy/content.py              ← 生成回复内容（AI / 随机 / 模板）
    │
    ▼
actions/reply.py                 ← 提交回复
    │
    ▼
utils/delay.py                   ← 等待随机间隔 → 继续下一帖
```

---

## 环境要求

- Python 3.10+
- Conda 虚拟环境（推荐）
- Playwright Chromium 浏览器

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

把 `.env.example` 复制为 `.env`，然后填入你的凭据（`.env` 文件被 git ignore，不会上传）：

```powershell
copy .env.example .env
```

然后编辑 `.env`：

```
HUPU_USERNAME=你的用户名
HUPU_PASSWORD=你的密码
GROQ_API_KEY=你的Groq密钥
```

编辑 `config.yaml`，调整目标版块和参数：

```yaml
targets:
  - board_url: "https://bbs.hupu.us/bxj"
    keywords: []
    max_threads: 3

reply:
  max_per_run: 1

content:
  mode: "ai"    # random / template / ai
```

### 4. 运行

```powershell
# 正常运行
python main.py

# 演练模式（只抓取帖子，不实际回帖）
python main.py --dry-run

# 调试选择器（帮助定位 DOM 元素）
python main.py --debug-selectors
```

---

## 两种运行方式

| 方式 | 入口 | 适合场景 |
|---|---|---|
| **GUI（exe）** | 双击 `dist/HupuBot/HupuBot.exe` | 日常使用，不懂命令行也能用 |
| **命令行** | `python main.py` | 开发调试，支持 `--dry-run` 等参数 |

---

## 内容生成模式

在 `config.yaml` 的 `content.mode` 中配置：

| 模式 | 说明 |
|------|------|
| `random` | 从 `data/replies.txt` 随机选一条 |
| `template` | 根据帖子标题填充模板 |
| `ai` | 调用 AI API 生成上下文相关的自然回复（推荐） |

### AI 优先级

Groq（免费）→ Gemini → DeepSeek → OpenAI → 降级随机回复

在 `.env` 中设置对应的 API Key 即可，脚本自动按优先级选择可用的 API。

---

## 定时自动运行

### Windows 定时任务（推荐）

```powershell
# 创建每天 22:00 自动执行的定时任务
schtasks /create /tn "HupuAutoReply" /tr "D:\path\to\run.bat" /sc daily /st 22:00 /f

# 管理命令
schtasks /query /tn "HupuAutoReply"      # 查看任务
schtasks /run /tn "HupuAutoReply"        # 手动运行
schtasks /delete /tn "HupuAutoReply" /f  # 删除任务
schtasks /change /tn "HupuAutoReply" /st 08:00  # 改时间
```

---

## 打包为 exe

直接运行打包脚本即可（它会处理所有步骤）：

```powershell
build.bat
```

输出在 `dist/HupuBot/`，双击 `HupuBot.exe` 即可运行。

**前提**：本机需已执行过 `playwright install chromium`，打包后的 exe 会在运行时查找系统已安装的浏览器。

**发布给别人前**：先清理 `dist/HupuBot/.env`（删掉你的真实账号密码），并删除 `dist/HupuBot/data/browser_profile/` 和所有 `*.log` 文件。打包脚本结束时也会打印这个提醒。

**对外分发**：将清理后的整个 `dist/HupuBot` 文件夹打成 zip，在 [Releases](https://github.com/dufu12345/fupucomment/releases) 新建版本并上传该 zip 作为附件（与本文开头的「给非开发者」说明一致）。

---

## 选择器调试

虎扑页面更新后，CSS 选择器可能会失效。运行调试模式查找正确选择器：

```powershell
python main.py --debug-selectors
```

在打开的浏览器中按 `F12` 打开 DevTools，找到正确选择器后更新：
- `actions/scrape.py` — 帖子列表选择器
- `actions/reply.py` — 回复框和提交按钮选择器
- `actions/login.py` — 登录表单选择器

---

## 关键技术点

| 技术 | 用途 |
|------|------|
| Playwright | 浏览器自动化，模拟真人操作 |
| 持久化 Cookie | `user_data_dir` 保持登录态，避免重复登录 |
| 反检测 | 修改 `navigator.webdriver`、自定义 User-Agent |
| AI 回复 | Groq/Gemini/DeepSeek 生成上下文相关内容，避免灌水检测 |
| 随机延迟 | 正态分布采样，模拟人类操作节奏 |
| loguru | 彩色控制台日志 + 按天轮转文件日志 |
| tkinter GUI | 打包为 exe 后提供图形界面，双击即用 |

---

## 工作原理

本项目 **不是传统爬虫**，不直接发 HTTP 请求，而是用 Playwright 控制一个 **真实的 Chromium 浏览器**，模拟人类的每一步操作：

1. **启动浏览器** — 打开一个真实的 Chrome 窗口，注入反检测脚本（修改 `navigator.webdriver`、自定义 User-Agent），让虎扑服务器认为是正常用户
2. **自动登录** — 打开虎扑首页 → 检测是否已登录 → 点击"登录"按钮 → 在弹窗中填入账号密码 → 提交（和你手动操作完全一样）
3. **抓取帖子** — 通过 CSS 选择器定位页面上的帖子元素，提取标题、URL、回复数等信息
4. **AI 生成回复** — 把帖子标题和正文发给 AI（Groq/Gemini 等），生成一条上下文相关的自然回复
5. **提交回帖** — 定位回复输入框（`contenteditable` 的 `<div>`），用 JavaScript 注入回复内容，点击"发表"按钮
6. **随机等待** — 用正态分布随机延迟模拟人类节奏，避免被检测为机器人

### 为什么不用传统爬虫（requests）？

| 维度 | 传统爬虫 (requests) | 本项目 (Playwright) |
|---|---|---|
| 速度 | 极快（毫秒级） | 慢（要真的加载页面） |
| 资源占用 | 极低（几 MB） | 高（开浏览器，几百 MB） |
| 反 Cloudflare | 几乎过不去 | 真实浏览器，能过 |
| 登录难度 | 要逆向 JS 加密 + 验证码 | 直接打字点按钮 |
| 回帖难度 | 要逆向 API 接口 + 签名 | 直接在页面上操作 |
| 维护成本 | 接口一改就废 | 页面布局没大改就行 |
| 被检测风险 | 高（特征明显） | 低（和真人一样） |

虎扑部署了 **Cloudflare Turnstile 反机器人验证** + **动态 JS 渲染** + **复杂登录流程**，传统爬虫的开发成本反而更高，还容易被拦截。Playwright 虽然更重，但开发简单、稳定、不容易被检测。

---

## 注意事项

- 请遵守虎扑用户协议，合理使用，勿用于刷分/营销
- 建议 `min_delay_seconds` 不低于 30 秒
- 首次运行建议 `headless: false` 以便手动处理验证码
- `.env` 文件不要提交到 Git
- 虎扑回帖内容要求至少 10 个中文字
