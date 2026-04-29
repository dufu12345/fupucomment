@echo off
chcp 65001 >nul
echo ===== 虎扑自动回帖 - 打包为 exe =====
echo.

cd /d "%~dp0"

echo [1/3] 安装 PyInstaller...
pip install pyinstaller -q

echo [2/3] 开始打包...
pyinstaller --noconfirm --onedir --windowed ^
    --name "虎扑自动回帖" ^
    --add-data "config.yaml;." ^
    --add-data "data\replies.txt;data" ^
    --add-data ".env;." ^
    --hidden-import=playwright ^
    --hidden-import=playwright.sync_api ^
    --hidden-import=yaml ^
    --hidden-import=loguru ^
    --hidden-import=dotenv ^
    --hidden-import=openai ^
    --hidden-import=google.genai ^
    --hidden-import=google.generativeai ^
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

echo [3/3] 复制运行所需文件到输出目录...
xcopy /Y /I "config.yaml" "dist\虎扑自动回帖\"
xcopy /Y /I ".env" "dist\虎扑自动回帖\"
xcopy /Y /I /E "data" "dist\虎扑自动回帖\data\"
xcopy /Y /I /E "actions" "dist\虎扑自动回帖\actions\"
xcopy /Y /I /E "browser" "dist\虎扑自动回帖\browser\"
xcopy /Y /I /E "strategy" "dist\虎扑自动回帖\strategy\"
xcopy /Y /I /E "utils" "dist\虎扑自动回帖\utils\"
copy /Y "main.py" "dist\虎扑自动回帖\"

echo.
echo ===== 打包完成！=====
echo 输出目录: dist\虎扑自动回帖\
echo 双击 "dist\虎扑自动回帖\虎扑自动回帖.exe" 即可运行
echo.
pause
