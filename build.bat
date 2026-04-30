@echo off
chcp 65001 >nul
echo ===== 虎扑自动回帖 - 打包为 exe =====
echo.

cd /d "%~dp0"

echo [1/4] 安装 PyInstaller...
pip install pyinstaller -q

echo [2/4] 清理旧的构建产物...
if exist "dist\HupuBot" rd /s /q "dist\HupuBot"
if exist "build\HupuBot" rd /s /q "build\HupuBot"

echo [3/4] 开始打包...
pyinstaller --noconfirm --onedir --windowed ^
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

echo [4/4] 复制运行所需文件到输出目录...
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
echo 提示：发布到 GitHub Releases 前请先清理 dist\HupuBot\.env 中的真实凭据，
echo       并删除 dist\HupuBot\data\browser_profile\ 和 *.log 文件！
echo.
pause
