"""
虎扑自动回帖 - 一键启动器（GUI 版）
打包为 exe 后双击即可运行，无需命令行。
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pathlib import Path


def resource_path(relative: str) -> str:
    """兼容 PyInstaller 打包后的资源路径"""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent
    return str(base / relative)


class HupuApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("虎扑自动回帖")
        self.root.geometry("700x520")
        self.root.resizable(True, True)
        self.root.configure(bg="#1a1a2e")
        self._running = False
        self._build_ui()

    def _build_ui(self):
        title = tk.Label(
            self.root, text="虎扑自动回帖脚本", font=("Microsoft YaHei UI", 18, "bold"),
            fg="#e94560", bg="#1a1a2e",
        )
        title.pack(pady=(18, 6))

        subtitle = tk.Label(
            self.root, text="点击「开始运行」即可自动回帖",
            font=("Microsoft YaHei UI", 10), fg="#aaaaaa", bg="#1a1a2e",
        )
        subtitle.pack(pady=(0, 12))

        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=6)

        self.btn_run = tk.Button(
            btn_frame, text="开始运行", font=("Microsoft YaHei UI", 13, "bold"),
            bg="#e94560", fg="white", activebackground="#c81e45",
            width=14, height=1, relief="flat", cursor="hand2",
            command=self._on_run,
        )
        self.btn_run.pack(side=tk.LEFT, padx=8)

        self.btn_dryrun = tk.Button(
            btn_frame, text="演练模式", font=("Microsoft YaHei UI", 13),
            bg="#16213e", fg="#00d2ff", activebackground="#0f3460",
            width=14, height=1, relief="flat", cursor="hand2",
            command=self._on_dry_run,
        )
        self.btn_dryrun.pack(side=tk.LEFT, padx=8)

        status_frame = tk.Frame(self.root, bg="#1a1a2e")
        status_frame.pack(fill=tk.X, padx=20, pady=(10, 2))
        self.status_label = tk.Label(
            status_frame, text="状态：就绪", font=("Microsoft YaHei UI", 10),
            fg="#00d2ff", bg="#1a1a2e", anchor="w",
        )
        self.status_label.pack(side=tk.LEFT)

        self.log_area = scrolledtext.ScrolledText(
            self.root, font=("Consolas", 9), bg="#0f3460", fg="#e0e0e0",
            insertbackground="white", wrap=tk.WORD, state=tk.DISABLED,
            relief="flat", borderwidth=0,
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 18))

    def _log(self, text: str):
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def _set_status(self, text: str, color: str = "#00d2ff"):
        self.status_label.config(text=f"状态：{text}", fg=color)

    def _on_run(self):
        self._start_task(dry_run=False)

    def _on_dry_run(self):
        self._start_task(dry_run=True)

    def _start_task(self, dry_run: bool):
        if self._running:
            messagebox.showwarning("提示", "脚本正在运行中，请等待完成")
            return

        self._running = True
        self.btn_run.config(state=tk.DISABLED)
        self.btn_dryrun.config(state=tk.DISABLED)
        mode_text = "演练" if dry_run else "正式"
        self._set_status(f"正在运行（{mode_text}模式）...", "#ffcc00")
        self._log(f"===== {mode_text}模式启动 =====")

        thread = threading.Thread(target=self._run_bot, args=(dry_run,), daemon=True)
        thread.start()

    def _gui_sink(self, message):
        """loguru 自定义 sink：把日志转发到 GUI 日志区"""
        text = message.strip()
        if text:
            self.root.after(0, self._log, text)

    def _run_bot(self, dry_run: bool):
        from loguru import logger

        try:
            os.chdir(resource_path("."))

            from utils.config_loader import load_config
            from main import run

            config = load_config(resource_path("config.yaml"))

            log_cfg = config.get("logging", {})
            level = log_cfg.get("level", "INFO").upper()
            log_file = log_cfg.get("file", "./data/hupu_bot.log")

            logger.remove()

            logger.add(
                self._gui_sink,
                level=level,
                format="{time:HH:mm:ss} | {level: <8} | {message}",
                colorize=False,
            )

            logger.add(
                log_file,
                level=level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
                rotation="1 day",
                retention="7 days",
                encoding="utf-8",
            )

            logger.info("日志已初始化")

            run(config, dry_run=dry_run)

            self.root.after(0, self._set_status, "运行完成", "#00ff88")
            self.root.after(0, self._log, "===== 运行完成 =====")
        except Exception as e:
            self.root.after(0, self._set_status, f"出错: {e}", "#ff4444")
            self.root.after(0, self._log, f"错误: {e}")
            import traceback
            self.root.after(0, self._log, traceback.format_exc())
        finally:
            self._running = False
            self.root.after(0, lambda: self.btn_run.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_dryrun.config(state=tk.NORMAL))

    def start(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = HupuApp()
    app.start()
