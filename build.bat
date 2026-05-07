@echo off
chcp 65001 >nul
echo ===== 虎扑自动回帖 - 打包为 exe =====
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 python。请从「Anaconda Prompt」或已安装 Python 的终端进入本目录后再运行 build.bat。
    pause
    exit /b 1
)

echo [1/5] 安装项目依赖与 PyInstaller...
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

echo [2/5] 校验当前 Python 是否已安装 Playwright...
python -c "import playwright.sync_api; print('playwright OK')"
if errorlevel 1 (
    echo.
    echo 打包用的 Python 里找不到 playwright。日志里的「Hidden import playwright.sync_api not found」也是这个原因。
    echo 请在本机已能运行「python main.py」的同一环境里执行：先 conda activate 你的环境，再运行本脚本；或对该 Python 执行：
    echo   python -m pip install -r requirements.txt
    echo   playwright install chromium
    pause
    exit /b 1
)

echo [3/5] 清理旧的构建产物...
if exist "dist\HupuBot" rd /s /q "dist\HupuBot"
if exist "build\HupuBot" rd /s /q "build\HupuBot"

echo [4/5] 开始打包...
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "HupuBot" ^
    --add-data "config.yaml;." ^
    --add-data "data\replies.txt;data" ^
    --hidden-import=playwright ^
    --hidden-import=playwright.sync_api ^
    --hidden-import=yaml ^
    --hidden-import=loguru ^
    --hidden-import=dotenv ^
    --hidden-import=openai ^
    --hidden-import=google.genai ^
    --hidden-import=actions ^
    --hidden-import=actions.login ^
    --hidden-import=actions.scrape ^
    --hidden-import=actions.reply ^
    --hidden-import=browser ^
    --hidden-import=browser.session ^
    --hidden-import=strategy ^
    --hidden-import=strategy.selector ^
    --hidden-import=strategy.content ^
    --hidden-import=utils ^
    --hidden-import=utils.config_loader ^
    --hidden-import=utils.logger ^
    --hidden-import=utils.delay ^
    --collect-all playwright ^
    launcher.py

if errorlevel 1 (
    echo.
    echo 打包失败：PyInstaller 执行出错。请确认本目录下能运行 python launcher.py，并已执行 pip install -r requirements.txt
    pause
    exit /b 1
)

echo [5/5] 复制运行所需文件到输出目录...
xcopy /Y /I "config.yaml" "dist\HupuBot\"
xcopy /Y /I ".env" "dist\HupuBot\"
xcopy /Y /I /E "data" "dist\HupuBot\data\"
xcopy /Y /I /E "actions" "dist\HupuBot\actions\"
xcopy /Y /I /E "browser" "dist\HupuBot\browser\"
xcopy /Y /I /E "strategy" "dist\HupuBot\strategy\"
xcopy /Y /I /E "utils" "dist\HupuBot\utils\"
copy /Y "main.py" "dist\HupuBot\"

echo.
echo ===== 打包完成！=====
echo 输出目录: dist\HupuBot\
echo 双击 "dist\HupuBot\HupuBot.exe" 即可运行
echo.
echo 提示：发布到 GitHub Releases 前请清理 dist\HupuBot\.env 里的真实凭据，并删除 dist\HupuBot\data\browser_profile 目录及其中所有 .log 日志文件。
echo.
pause
