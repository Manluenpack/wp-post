#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp-post env 设置小工具
=======================

把 WordPress 凭据（WP_API_USERNAME / WP_APP_PASSWORD / WP_SITE_DOMAIN）
写进当前用户的 shell 环境变量，跨平台（macOS / Linux / Windows）兼容。

设计要点：
- Tkinter 桌面窗口，标准库自带，零依赖。
- 写值时用 marker 块（# >>> wp-post env >>> ... # <<< wp-post env <<<）做幂等更新，
  不会重复追加、也不会破坏用户已有的配置。
- macOS / Linux：优先写 ~/.zshenv（关键！非交互 shell 只读 zshenv，不读 zshrc），
  如果用户的默认 shell 是 bash，则写 ~/.bashrc（Linux 桌面默认）。
  用户可在 UI 里手动切换写入目标。
- Windows：调用 PowerShell 的 [Environment]::SetEnvironmentVariable("VAR","val","User")
  写入用户级注册表，新开终端自动生效。
- 密码不回显到日志；保存后用 messagebox 提示，不打印到 stdout。
- 启动时自动检测当前系统 / shell，并把当前已存在的环境变量值预填到表单里
  （方便用户看到/修改现状，不会误覆盖——保存时才真正写入）。
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
import webbrowser

APP_TITLE = "wp-post 环境变量设置"
MARKER_START = "# >>> wp-post env >>>"
MARKER_END = "# <<< wp-post env <<<"

VARS = [
    ("WP_API_USERNAME", "用户名", False),
    ("WP_APP_PASSWORD", "应用密码", True),       # 密码，遮罩
    ("WP_SITE_DOMAIN", "站点域名（不含 https://）", False),
]


# ---------- 平台 / shell 检测 ----------

def detect_platform() -> str:
    """返回 'macos' / 'linux' / 'windows'。"""
    s = platform.system().lower()
    if s == "darwin":
        return "macos"
    if s == "windows":
        return "windows"
    return "linux"


def detect_default_shell() -> str:
    """
    返回 'zsh' / 'bash' / 'powershell' / 'cmd'。
    macOS 现代默认 zsh，Linux 桌面默认 bash，Windows 走 PowerShell。
    """
    plat = detect_platform()
    if plat == "windows":
        # PowerShell 才是 mavis 在 Windows 上的默认 shell
        return "powershell"
    # macOS / Linux：看 $SHELL
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return "zsh"
    if shell.endswith("bash"):
        return "bash"
    # 兜底
    return "zsh" if plat == "macos" else "bash"


def target_rc_file(shell: str) -> Path:
    """
    给定 shell 类型，返回应该写入的 rc / env 文件。
    - zsh: ~/.zshenv  （非交互 shell 唯一会读的文件，重要！）
    - bash (Linux 桌面): ~/.bashrc  （交互登录读 .profile / .bash_profile，但 GUI 应用启动的子进程一般会读 .bashrc）
    - powershell: 返回一个虚拟路径，实际写入走 _set_windows_user_env
    """
    home = Path.home()
    if shell == "zsh":
        return home / ".zshenv"
    if shell == "bash":
        return home / ".bashrc"
    # powershell 不会走到这里
    raise ValueError(f"unsupported shell: {shell}")


# ---------- 环境变量读取 ----------

def read_current_env() -> dict[str, str]:
    """
    读取三个变量当前在 os.environ 中的值。
    如果变量未设置，值为空字符串。
    """
    return {name: os.environ.get(name, "") for name, _, _ in VARS}


# ---------- POSIX (macOS / Linux) 写入逻辑 ----------

POSIX_VAR_RE = re.compile(r"^export\s+([A-Z_][A-Z0-9_]*)=(.*)$")


def _strip_quotes(val: str) -> str:
    """去掉 shell 里的单/双引号包裹。

    write_posix 现在用单引号包值，单引号内任何字符都是字面量，
    所以解析时直接剥掉最外层单引号即可，不需要做反向转义解码。
    """
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] == "'":
        return val[1:-1]
    return val


def _parse_existing_block(text: str) -> dict[str, str]:
    """从已有 rc 文件内容里提取 marker 块内的变量。"""
    result: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.strip() == MARKER_START:
            in_block = True
            continue
        if line.strip() == MARKER_END:
            in_block = False
            continue
        if in_block:
            m = POSIX_VAR_RE.match(line.strip())
            if m:
                result[m.group(1)] = _strip_quotes(m.group(2))
    return result


def write_posix(values: dict[str, str], rc_path: Path) -> None:
    """
    把三个变量写入 POSIX rc 文件，用 marker 块做幂等更新。
    - 如果文件里已有 marker 块：替换整个块。
    - 否则：在文件末尾追加一个块。
    """
    # 先把文件读出来（不存在就当成空）
    original = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
    new_block_lines = [MARKER_START]
    for name, _, _ in VARS:
        val = values.get(name, "")
        # 用单引号包：单引号内任何字符都是字面量，$ ` " \ 都不会被 shell 解释
        # 唯一的例外是单引号本身，要用 '\'' 这种"关-转义-开"的写法
        safe = val.replace("'", "'\\''")
        new_block_lines.append(f"export {name}='{safe}'")
    new_block_lines.append(MARKER_END)
    new_block = "\n".join(new_block_lines) + "\n"

    if MARKER_START in original:
        # 替换已有块（start 行 到 end 行，含两端）
        pattern = re.compile(
            rf"^{re.escape(MARKER_START)}.*?^{re.escape(MARKER_END)}\n?",
            re.MULTILINE | re.DOTALL,
        )
        updated = pattern.sub(new_block, original)
    else:
        # 追加到文件末尾，前面留一个空行
        prefix = "" if not original or original.endswith("\n") else "\n"
        updated = original + prefix + "\n" + new_block

    rc_path.write_text(updated, encoding="utf-8")


def clear_posix(rc_path: Path) -> bool:
    """把 marker 块从 rc 文件里删掉。返回是否真的删了什么。"""
    if not rc_path.exists():
        return False
    original = rc_path.read_text(encoding="utf-8")
    if MARKER_START not in original:
        return False
    pattern = re.compile(
        rf"\n?{re.escape(MARKER_START)}.*?{re.escape(MARKER_END)}\n?",
        re.DOTALL,
    )
    updated = pattern.sub("\n", original)
    rc_path.write_text(updated, encoding="utf-8")
    return True


# ---------- Windows 写入逻辑 ----------

def write_windows(values: dict[str, str]) -> None:
    """
    Windows 上调用 PowerShell 把三个变量写到用户级环境变量。
    用 -NonInteractive 避免挂起。
    """
    if detect_platform() != "windows":
        raise RuntimeError("write_windows should only be called on Windows")
    # 优先用 pwsh，没有再退到 Windows PowerShell
    ps = "powershell" if shutil.which("powershell") else "pwsh"
    # PowerShell 里的转义：双引号需要前置反引号
    for name, _, _ in VARS:
        val = values.get(name, "")
        # PowerShell 双引号字符串里 $ ` " 需要转义
        ps_val = val.replace("`", "``").replace('"', '`"').replace("$", "`$")
        cmd = (
            f'[Environment]::SetEnvironmentVariable('
            f'"{name}", "{ps_val}", "User")'
        )
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"设置 {name} 失败：{result.stderr.strip() or '未知错误'}"
            )


def clear_windows() -> bool:
    """把三个 Windows 用户环境变量清空。"""
    if detect_platform() != "windows":
        raise RuntimeError("clear_windows should only be called on Windows")
    ps = "powershell" if shutil.which("powershell") else "pwsh"
    cleared = False
    for name, _, _ in VARS:
        cmd = f'[Environment]::SetEnvironmentVariable("{name}", $null, "User")'
        result = subprocess.run(
            [ps, "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            cleared = True
    return cleared


# ---------- UI ----------

class WpPostEnvApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("520x320")
        self.root.minsize(480, 280)

        self.platform = detect_platform()
        self.default_shell = detect_default_shell()
        self.entries: dict[str, tk.Entry] = {}
        self.show_password = tk.BooleanVar(value=False)

        self._build_ui()
        self._refresh_status()

    # ---- UI 构造 ----

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        # 平台信息条
        info = ttk.Frame(self.root)
        info.pack(fill="x", **pad)
        ttk.Label(
            info,
            text=f"系统: {self.platform}   默认 shell: {self.default_shell}",
            foreground="#666",
        ).pack(side="left")

        # shell 选择（仅 POSIX）
        if self.platform != "windows":
            shell_frame = ttk.Frame(self.root)
            shell_frame.pack(fill="x", **pad)
            ttk.Label(shell_frame, text="写入目标:").pack(side="left")
            self.shell_choice = tk.StringVar(value=self.default_shell)
            for opt in ("zsh", "bash"):
                ttk.Radiobutton(
                    shell_frame,
                    text=opt,
                    value=opt,
                    variable=self.shell_choice,
                    command=self._refresh_status,
                ).pack(side="left", padx=6)
        else:
            self.shell_choice = tk.StringVar(value="powershell")

        # 三个变量输入
        form = ttk.LabelFrame(self.root, text="WordPress 凭据")
        form.pack(fill="x", **pad)
        for name, label, is_secret in VARS:
            row = ttk.Frame(form)
            row.pack(fill="x", padx=8, pady=4)
            ttk.Label(row, text=label, width=24, anchor="w").pack(side="left")
            entry = ttk.Entry(row, show="*" if is_secret else "")
            entry.pack(side="left", fill="x", expand=True)
            self.entries[name] = entry

        # 显示密码复选框
        opt_row = ttk.Frame(self.root)
        opt_row.pack(fill="x", **pad)
        ttk.Checkbutton(
            opt_row,
            text="显示应用密码",
            variable=self.show_password,
            command=self._toggle_password_visibility,
        ).pack(side="left")

        # 状态栏
        self.status_var = tk.StringVar(value="")
        ttk.Label(
            self.root,
            textvariable=self.status_var,
            foreground="#06c",
            wraplength=480,
            justify="left",
        ).pack(fill="x", padx=12, pady=(4, 0))

        # 按钮
        btn_row = ttk.Frame(self.root)
        btn_row.pack(fill="x", padx=12, pady=12, side="bottom")
        ttk.Button(btn_row, text="清除", command=self.on_clear).pack(side="right", padx=(6, 0))
        ttk.Button(btn_row, text="保存", command=self.on_save).pack(side="right")
        ttk.Button(btn_row, text="打开配置文件", command=self.on_open_file).pack(side="left")

        # 预填当前值
        current = read_current_env()
        for name, entry in self.entries.items():
            entry.insert(0, current.get(name, ""))

    # ---- 事件 ----

    def _toggle_password_visibility(self) -> None:
        show = "" if self.show_password.get() else "*"
        self.entries["WP_APP_PASSWORD"].config(show=show)

    def _refresh_status(self) -> None:
        if self.platform == "windows":
            target = "Windows 用户环境变量（注册表）"
        else:
            target = str(target_rc_file(self.shell_choice.get()))
        self.status_var.set(f"将写入: {target}")

    def _collect_values(self) -> dict[str, str]:
        return {name: entry.get().strip() for name, entry in self.entries.items()}

    def _validate(self, values: dict[str, str]) -> str | None:
        if not values.get("WP_API_USERNAME"):
            return "用户名不能为空"
        if not values.get("WP_APP_PASSWORD"):
            return "应用密码不能为空"
        if not values.get("WP_SITE_DOMAIN"):
            return "站点域名不能为空"
        # 域名里不应该带协议头
        dom = values["WP_SITE_DOMAIN"]
        if dom.startswith("http://") or dom.startswith("https://"):
            return "站点域名不要带 http:// 或 https:// 前缀"
        return None

    def on_save(self) -> None:
        values = self._collect_values()
        err = self._validate(values)
        if err:
            messagebox.showerror(APP_TITLE, err)
            return
        try:
            if self.platform == "windows":
                write_windows(values)
            else:
                rc = target_rc_file(self.shell_choice.get())
                write_posix(values, rc)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"保存失败：{e}")
            return

        if self.platform == "windows":
            tip = "已写入 Windows 用户环境变量。\n请打开新的终端窗口，新变量才会生效。"
        else:
            rc = target_rc_file(self.shell_choice.get())
            tip = (
                f"已写入 {rc}。\n"
                "新开终端后变量会自动生效（已打开的终端需要 source 一下："
                f"source {rc}）。"
            )
        messagebox.showinfo(APP_TITLE, tip)

    def on_clear(self) -> None:
        if not messagebox.askyesno(APP_TITLE, "确认清除 wp-post 写入的环境变量？"):
            return
        try:
            if self.platform == "windows":
                cleared = clear_windows()
            else:
                rc = target_rc_file(self.shell_choice.get())
                cleared = clear_posix(rc)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"清除失败：{e}")
            return

        if cleared:
            messagebox.showinfo(APP_TITLE, "已清除。\n新开终端后失效。")
        else:
            messagebox.showinfo(APP_TITLE, "没找到之前写入的块，无需清除。")

    def on_open_file(self) -> None:
        """在 Finder / Explorer / 文件管理器里打开写入的 rc 文件。"""
        if self.platform == "windows":
            messagebox.showinfo(
                APP_TITLE,
                "Windows 写入的是用户环境变量（注册表），\n没有对应的配置文件。\n"
                "可以在 PowerShell 里跑 [Environment]::GetEnvironmentVariable(\"WP_API_USERNAME\",\"User\") 查看。",
            )
            return
        rc = target_rc_file(self.shell_choice.get())
        if not rc.exists():
            messagebox.showwarning(APP_TITLE, f"文件还没创建：{rc}\n请先点保存。")
            return
        # macOS / Linux 都支持 file:// URL
        webbrowser.open(rc.as_uri())


# ---------- 入口 ----------

def main() -> int:
    root = tk.Tk()
    # 让 ttk 风格跟系统走
    try:
        style = ttk.Style()
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
        elif "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:  # noqa: BLE001
        pass
    WpPostEnvApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
