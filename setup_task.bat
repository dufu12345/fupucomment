@echo off
echo ===== 创建 Windows 定时任务：每天 22:00 自动运行虎扑回帖脚本 =====
echo.

schtasks /create /tn "HupuAutoReply" /tr "D:\jhu_blockchain_reseasrch\fupucomment\run.bat" /sc daily /st 22:00 /f

echo.
echo 任务已创建！
echo - 任务名: HupuAutoReply
echo - 运行时间: 每天 22:00
echo - 脚本路径: D:\jhu_blockchain_reseasrch\fupucomment\run.bat
echo.
echo 管理方式:
echo   查看任务:  schtasks /query /tn "HupuAutoReply"
echo   删除任务:  schtasks /delete /tn "HupuAutoReply" /f
echo   手动运行:  schtasks /run /tn "HupuAutoReply"
echo.
pause
