English | [中文](README.md)

# Hupu Auto-Reply Bot (Study Only)

An automated reply bot for [Hupu BBS](https://bbs.hupu.us/) built with Python + Playwright. Features AI-powered reply generation, a one-click GUI, and Windows scheduled task support.

---

## Project Structure

```
fupucomment/
├── main.py                 # CLI entry point
├── launcher.py             # GUI launcher (packaged as exe)
├── config.yaml             # Configuration: board URLs, reply limits, delays, modes
├── .env                    # Secrets: Hupu credentials, AI API keys (not tracked by Git)
├── requirements.txt        # Python dependencies
│
├── actions/                # [Action Layer] Browser interactions
│   ├── login.py            #   Login: detect status, open modal, fill credentials
│   ├── scrape.py           #   Scrape: fetch thread lists and thread body content
│   └── reply.py            #   Reply: locate reply box, fill content, submit
│
├── browser/                # [Browser Layer] Playwright lifecycle management
│   └── session.py          #   Launch/close browser, persistent cookies, anti-detection
│
├── strategy/               # [Strategy Layer] Decide "what to reply" and "which thread"
│   ├── selector.py         #   Filter: by keywords, reply count
│   └── content.py          #   Content generation: random / template / AI (Groq/Gemini/DeepSeek/OpenAI)
│
├── utils/                  # [Utility Layer] Common helpers
│   ├── config_loader.py    #   Load config.yaml + .env
│   ├── logger.py           #   loguru initialization (console + file)
│   └── delay.py            #   Random delays simulating human behavior
│
├── data/                   # [Data] Runtime-generated files
│   ├── replies.txt         #   Reply corpus (for random mode)
│   ├── browser_profile/    #   Persistent browser cookies (auto-generated)
│   └── hupu_bot.log        #   Run logs (auto-generated)
│
├── run.bat                 # One-click Windows run script
├── setup_task.bat          # Create Windows scheduled task (daily at 22:00)
├── build.bat               # PyInstaller packaging script
│
└── .github/workflows/
    └── auto_reply.yml      # GitHub Actions workflow (deprecated, blocked by Cloudflare)
```

---

## Execution Flow

```
User double-clicks HupuBot.exe (GUI) or runs python main.py (CLI)
    │
    ├── utils/config_loader.py   ← Load config.yaml + .env
    ├── utils/logger.py          ← Initialize logging
    │
    ▼
browser/session.py               ← Launch Playwright browser (anti-detection)
    │
    ▼
actions/login.py                 ← Auto-login to Hupu
    │
    ▼
actions/scrape.py                ← Scrape thread list + body content
    │
    ▼
strategy/selector.py             ← Filter threads to reply to
    │
    ▼
strategy/content.py              ← Generate reply content (AI / random / template)
    │
    ▼
actions/reply.py                 ← Submit reply
    │
    ▼
utils/delay.py                   ← Wait random interval → next thread
```

---

## Requirements

- Python 3.10+
- Conda virtual environment (recommended)
- Playwright Chromium browser

## Quick Start

### 1. Create and activate Conda environment

```powershell
conda create -n hupu python=3.11
conda activate hupu
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure

Create a `.env` file (secrets, not tracked by Git):

```
HUPU_USERNAME=your_username
HUPU_PASSWORD=your_password
GROQ_API_KEY=your_groq_key
```

Edit `config.yaml` to set target boards and parameters:

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

### 4. Run

```powershell
# Normal run
python main.py

# Dry run (scrape only, no actual replies)
python main.py --dry-run

# Debug selectors (inspect DOM elements)
python main.py --debug-selectors
```

---

## Two Ways to Run

| Method | Entry Point | Best For |
|---|---|---|
| **GUI (exe)** | Double-click `dist/HupuBot/HupuBot.exe` | Daily use, no command line needed |
| **CLI** | `python main.py` | Development, supports `--dry-run` etc. |

---

## Content Generation Modes

Set `content.mode` in `config.yaml`:

| Mode | Description |
|------|------|
| `random` | Pick a random line from `data/replies.txt` |
| `template` | Fill template based on thread title |
| `ai` | AI-generated context-aware reply (recommended) |

### AI Priority

Groq (free) → Gemini → DeepSeek → OpenAI → fallback to random

Set the corresponding API key in `.env` and the script automatically picks the best available API.

---

## Scheduled Execution

### Windows Task Scheduler (Recommended)

```powershell
# Create a daily task at 22:00
schtasks /create /tn "HupuAutoReply" /tr "D:\path\to\run.bat" /sc daily /st 22:00 /f

# Management commands
schtasks /query /tn "HupuAutoReply"      # View task
schtasks /run /tn "HupuAutoReply"        # Run manually
schtasks /delete /tn "HupuAutoReply" /f  # Delete task
schtasks /change /tn "HupuAutoReply" /st 08:00  # Change time
```

### GitHub Actions (Deprecated)

Hupu uses Cloudflare Turnstile anti-bot verification, which blocks headless browsers and foreign IPs. GitHub Actions is therefore not viable for this project.

---

## Packaging as exe

```powershell
# Option 1: Run the build script
build.bat

# Option 2: Manual
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --name "HupuBot" --collect-all playwright launcher.py
```

Output is in `dist/HupuBot/`. Double-click `HupuBot.exe` to launch.

Prerequisite: `playwright install chromium` must have been run on the machine. The exe automatically locates the system-installed browser.

---

## Selector Debugging

Hupu may update its page structure, breaking CSS selectors. Use debug mode to find correct selectors:

```powershell
python main.py --debug-selectors
```

Open DevTools (`F12`) in the browser window and update the selectors in:
- `actions/scrape.py` — Thread list selectors
- `actions/reply.py` — Reply box and submit button selectors
- `actions/login.py` — Login form selectors

---

## Key Technologies

| Technology | Purpose |
|------|------|
| Playwright | Browser automation, simulates real user interactions |
| Persistent Cookies | `user_data_dir` maintains login state across sessions |
| Anti-Detection | Overrides `navigator.webdriver`, custom User-Agent |
| AI Replies | Groq/Gemini/DeepSeek generate context-relevant content to avoid spam detection |
| Random Delays | Gaussian-distributed intervals to mimic human behavior |
| loguru | Colored console logs + daily-rotating file logs |
| tkinter GUI | Graphical interface for packaged exe, one-click operation |

---

## How It Works

This project is **not a traditional web scraper**. Instead of sending raw HTTP requests, it uses Playwright to control a **real Chromium browser**, simulating every step a human would take:

1. **Launch browser** — Opens a real Chrome window with anti-detection scripts (overrides `navigator.webdriver`, custom User-Agent) so Hupu's servers see a normal user
2. **Auto-login** — Navigates to Hupu homepage → checks login status → clicks "Login" button → fills username/password in the modal → submits (exactly like manual operation)
3. **Scrape threads** — Uses CSS selectors to locate thread elements on the page, extracting title, URL, reply count, etc.
4. **AI-generated replies** — Sends thread title and body to an AI (Groq/Gemini/etc.) to generate a natural, context-aware reply
5. **Submit reply** — Locates the reply input box (`contenteditable` `<div>`), injects content via JavaScript, clicks "Submit"
6. **Random delays** — Uses Gaussian-distributed random delays to mimic human browsing patterns and avoid bot detection

### Why Not a Traditional Scraper (requests)?

| Aspect | Traditional Scraper (requests) | This Project (Playwright) |
|---|---|---|
| Speed | Very fast (milliseconds) | Slower (loads real pages) |
| Resource usage | Very low (a few MB) | Higher (browser process, hundreds of MB) |
| Anti-Cloudflare | Almost impossible to bypass | Real browser, passes through |
| Login difficulty | Must reverse-engineer JS encryption + CAPTCHA | Just types and clicks buttons |
| Reply difficulty | Must reverse-engineer API endpoints + signatures | Operates directly on the page |
| Maintenance cost | Breaks when API changes | Works as long as page layout is similar |
| Detection risk | High (obvious bot fingerprint) | Low (indistinguishable from a real user) |

Hupu uses **Cloudflare Turnstile anti-bot verification** + **dynamic JS rendering** + **complex login flow**. A traditional scraper would actually be harder to develop and easier to block. Playwright is heavier but simpler to build, more stable, and much harder to detect.

---

## Notes

- Please comply with Hupu's Terms of Service; do not use for spam or marketing
- Recommended `min_delay_seconds` of at least 30 seconds
- Set `headless: false` for the first run to handle CAPTCHAs manually
- Never commit `.env` to Git
- Hupu requires replies to be at least 10 Chinese characters
