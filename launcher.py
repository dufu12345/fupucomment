"""
虎扑自动回帖 - 一键启动器（GUI 版）
打包为 exe 后双击即可运行，无需命令行。
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from pathlib import Path

from dotenv import dotenv_values

_ENV_FIELD_ROWS = (
    ("虎扑账号", "HUPU_USERNAME", False),
    ("虎扑密码", "HUPU_PASSWORD", True),
    ("Groq API Key（可选）", "GROQ_API_KEY", False),
    ("Gemini API Key（可选）", "GEMINI_API_KEY", False),
    ("DeepSeek API Key（可选）", "DEEPSEEK_API_KEY", False),
    ("OpenAI API Key（可选）", "OPENAI_API_KEY", False),
)
_ENV_KEYS_GUI = {row[1] for row in _ENV_FIELD_ROWS}


def _format_env_line_value(val: str) -> str:
    """写入 .env 时对含空格、#、引号的值做必要转义"""
    if not val:
        return ""
    if any(c in val for c in " \t\n\r#\"") or val.startswith("'"):
        esc = val.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{esc}"'
    return val


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
        self.root.geometry("700x720")
        self.root.minsize(640, 600)
        self.root.resizable(True, True)
        self.root.configure(bg="#1a1a2e")
        self._running = False
        self._env_entries: dict[str, tk.Entry] = {}
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        title = tk.Label(
            self.root, text="虎扑自动回帖脚本", font=("Microsoft YaHei UI", 18, "bold"),
            fg="#e94560", bg="#1a1a2e",
        )
        title.pack(pady=(18, 6))

        subtitle = tk.Label(
            self.root, text="配置会保存到程序目录的 .env，下次打开自动填入；运行或关窗口时会自动保存",
            font=("Microsoft YaHei UI", 10), fg="#aaaaaa", bg="#1a1a2e",
        )
        subtitle.pack(pady=(0, 8))

        settings = tk.LabelFrame(
            self.root,
            text=" 账户与 API（写入程序目录下的 .env，与 config_loader 一致） ",
            font=("Microsoft YaHei UI", 10),
            fg="#e0e0e0",
            bg="#16213e",
            bd=1,
            labelanchor="n",
        )
        settings.pack(fill=tk.X, padx=20, pady=(0, 8))

        hint = tk.Label(
            settings,
            text="填写后一般无需每次再输：关闭窗口或点「开始运行」都会写入 .env。勿将 .env 分享给他人。",
            font=("Microsoft YaHei UI", 9),
            fg="#888899",
            bg="#16213e",
            wraplength=620,
            justify=tk.LEFT,
        )
        hint.pack(anchor="w", padx=10, pady=(6, 4))

        for label_text, env_key, is_pw in _ENV_FIELD_ROWS:
            row = tk.Frame(settings, bg="#16213e")
            row.pack(fill=tk.X, padx=10, pady=2)
            lbl = tk.Label(
                row, text=label_text, font=("Microsoft YaHei UI", 9),
                fg="#cccccc", bg="#16213e", width=22, anchor="e",
            )
            lbl.pack(side=tk.LEFT, padx=(0, 8))
            ent = tk.Entry(row, font=("Microsoft YaHei UI", 9), width=52, bg="#0f3460", fg="#e8e8e8", insertbackground="white")
            if is_pw:
                ent.configure(show="*")
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._env_entries[env_key] = ent

        settings_btn = tk.Frame(settings, bg="#16213e")
        settings_btn.pack(fill=tk.X, padx=10, pady=(10, 10))
        tk.Button(
            settings_btn,
            text="保存到 .env",
            font=("Microsoft YaHei UI", 10),
            bg="#e94560",
            fg="white",
            activebackground="#c81e45",
            relief="flat",
            cursor="hand2",
            command=self._on_save_env,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(
            settings_btn,
            text="打开配置目录",
            font=("Microsoft YaHei UI", 10),
            bg="#0f3460",
            fg="#00d2ff",
            activebackground="#16213e",
            relief="flat",
            cursor="hand2",
            command=self._on_open_config_dir,
        ).pack(side=tk.LEFT)

        self._load_env_into_fields()

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

    def _env_file_path(self) -> Path:
        return Path(resource_path(".env"))

    def _load_env_into_fields(self):
        path = self._env_file_path()
        data = dotenv_values(path) if path.exists() else {}
        for _label, env_key, _is_pw in _ENV_FIELD_ROWS:
            raw = data.get(env_key)
            val = (raw or "").strip() if isinstance(raw, str) else (str(raw) if raw else "")
            self._env_entries[env_key].delete(0, tk.END)
            self._env_entries[env_key].insert(0, val)

    def _persist_env_to_disk(
        self,
        *,
        show_success_dialog: bool = False,
        log_message: str | None = None,
    ) -> bool:
        path = self._env_file_path()
        existing = dotenv_values(path) if path.exists() else {}
        lines: list[str] = [
            "# 由虎扑自动回帖 GUI 写入；也可手动编辑。勿上传或分享本文件。",
            "",
        ]
        for _label, env_key, _is_pw in _ENV_FIELD_ROWS:
            val = self._env_entries[env_key].get().strip()
            lines.append(f"{env_key}={_format_env_line_value(val)}")
        extras = [
            (k, v)
            for k, v in existing.items()
            if k and k not in _ENV_KEYS_GUI
        ]
        if extras:
            lines.append("")
            lines.append("# 其他变量（保留自原 .env）")
            for k, v in sorted(extras, key=lambda x: x[0]):
                vv = v if v is not None else ""
                lines.append(f"{k}={_format_env_line_value(str(vv))}")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            if show_success_dialog:
                messagebox.showinfo("已保存", f"已写入：\n{path}")
            if log_message:
                self._log(log_message)
            return True
        except OSError as e:
            messagebox.showerror("保存失败", str(e))
            return False

    def _on_save_env(self):
        p = self._env_file_path()
        self._persist_env_to_disk(show_success_dialog=True, log_message=f"已保存 .env → {p}")

    def _on_close(self):
        self._persist_env_to_disk(show_success_dialog=False, log_message=None)
        self.root.destroy()

    def _on_open_config_dir(self):
        folder = resource_path(".")
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except OSError as e:
            messagebox.showerror("无法打开目录", str(e))

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

        if not self._persist_env_to_disk(show_success_dialog=False, log_message=None):
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
