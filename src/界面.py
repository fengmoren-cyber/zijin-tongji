#!/usr/bin/env python3
"""
界面.py — 资金统计软件 v2.3.1  图形界面入口
========================================
软件名称：资金统计软件
版权所属：玉玄道·资金管理部
版    本：v2.3.1

修复说明：
  v2.3   - 改用进程内执行(runpy)，彻底解决 EXE 模式下开新窗口的问题
           精简界面，扩大日志区，移除多余选项
  v2.3.1 - 修复 --rules 参数未识别错误
           按钮行移至日志区上方，确保始终可见
"""
from __future__ import annotations

import io
import json
import os
import queue
import runpy
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

try:
    import customtkinter as ctk
except ImportError:
    print("请先安装 customtkinter：pip install customtkinter")
    sys.exit(1)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ══════════════════════════════════════════════════════════════════
# 路径常量（兼容 PyInstaller --onefile）
# ══════════════════════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    _MEIPASS = Path(sys._MEIPASS)   # 临时解压目录（脚本/资源在此）
    _ROOT    = Path(sys.executable).parent  # EXE 所在目录（配置/数据在此）
    _SRC     = _MEIPASS             # Python 脚本路径
    _ASSETS  = _MEIPASS / "assets"
    _FROZEN  = True
else:
    _SRC     = Path(__file__).resolve().parent
    _ROOT    = _SRC.parent
    _ASSETS  = _ROOT / "assets"
    _FROZEN  = False

_CONFIG_FILE = _ROOT / "config.json"
_LOGO_PATH   = _ASSETS / "logo.png"

# ══════════════════════════════════════════════════════════════════
# 应用信息
# ══════════════════════════════════════════════════════════════════
APP_NAME  = "资金统计软件"
APP_VER   = "v2.3.1"
APP_CORP  = "玉玄道·资金管理部"
APP_YEAR  = "2026"

# ══════════════════════════════════════════════════════════════════
# 白色主题配色
# ══════════════════════════════════════════════════════════════════
GOLD      = "#B8860B"
GOLD_LT   = "#D4A820"
GOLD_BG   = "#FDF8EE"
GOLD_LINE = "#D4C080"
BG_WIN    = "#F5F2EC"
BG_PANEL  = "#FFFFFF"
BG_CARD   = "#FAFAF7"
BG_ENTRY  = "#FFFFFF"
BG_HDR    = "#1A1A2E"
BG_LOG    = "#F8F8F4"
TXT_MAIN  = "#1A1510"
TXT_SUB   = "#665A40"
TXT_DIM   = "#AAA080"
TXT_LOG   = "#2A2A18"
TXT_HDR   = "#F0EAD6"
BORDER    = "#DDD5BC"
C_OK      = "#1A7A2A"
C_WARN    = "#8A5A00"
C_ERR     = "#A01010"
C_INFO    = "#1A5080"
C_RULE    = "#5A35A0"
BTN_PRI   = "#8A6010"
BTN_HOV   = "#6A4800"
BTN_TXT   = "#FFF0C0"

# ══════════════════════════════════════════════════════════════════
# 操作说明
# ══════════════════════════════════════════════════════════════════
HELP_TEXT = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  资金统计软件  操作说明          v2.3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

一、首次配置路径

  【源文件目录】  存放银行流水 Excel 的文件夹
                  将所有 .xlsx / .xls 放入此文件夹
  【规则库文件】  rules\\规则库.xlsx 的完整路径
  【输出目录】    统计报表的输出位置

  → 点击各路径右侧【选择】按钮选取
  → 路径自动保存，下次启动无需重新配置

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

二、生成报表（每月操作）

  1. 将当月银行流水 Excel 放入源文件目录
  2. 确认年份（默认当年）
  3. 点击【▶ 执行生成报表】
  4. 等待绿色「执行成功」提示
  5. 点击【打开输出目录】查看报表

  每次执行自动生成：
  ・支出统计报表（含未匹配 ★ 清单）
  ・收入统计报表

  ◆ 快速模式：跳过迷你图/条件格式等图表美化，
    速度更快，数据完全相同，文件量较大时推荐。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

三、修正补录（报表含「待完善」时）

  报表文件名含「待完善」= 有未能自动分类的交易

  1. 打开「待完善」报表，找到带 ★ 的 Sheet
  2. 在黄色列填写正确的费用/收入类型及部门
  3. 保存并关闭 Excel 文件（务必关闭！）
  4. 切换到【修正补录】标签页
  5. 点击【✎ 执行修正补录】
  6. 程序自动读取修正内容 → 更新规则库 → 重新生成报表
  7. 完成后弹窗显示本次新增/更新规则明细

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

四、注意事项

  ◆ 执行前请确保相关 Excel 文件已完全关闭
  ◆ 规则库会累积学习，补录越多匹配率越高
  ◆ 日志红色文字表示错误，截图发给技术支持
  ◆ output/ 目录保留所有历史记录，可随时查阅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              技术支持：玉玄道·资金管理部
"""


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════
def _norm(p: str) -> str:
    return str(Path(p)) if p else p


def _default_cfg() -> dict:
    return {
        "input_dir":  _norm(str(_ROOT / "input")),
        "rules_file": _norm(str(_ROOT / "rules" / "规则库.xlsx")),
        "output_dir": _norm(str(_ROOT / "output")),
        "year":       str(datetime.now().year),
        "no_enhance": False,
    }


def _load_cfg() -> dict:
    cfg = _default_cfg()
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            for k in ("input_dir", "rules_file", "output_dir"):
                if k in saved:
                    saved[k] = _norm(saved[k])
            cfg.update(saved)
        except Exception:
            pass
    return cfg


def _save_cfg(cfg: dict) -> None:
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _open_dir(path: str) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    p.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "darwin":
            import subprocess; subprocess.Popen(["open", str(p)])
        elif sys.platform == "win32":
            os.startfile(str(p))
        else:
            import subprocess; subprocess.Popen(["xdg-open", str(p)])
    except Exception:
        pass


def _lvl(line: str) -> str:
    lo = line.lower()
    if any(k in lo for k in ("error","错误","traceback","exception","failed","失败","✗")):
        return "err"
    if any(k in lo for k in ("warning","警告","warn","注意")):
        return "warn"
    if any(k in lo for k in ("✓","完成","success","成功","已保存","已写入")):
        return "ok"
    if any(k in lo for k in ("新增规则","更新规则","added rule")):
        return "rule"
    return "info"


def _parse_rules(lines: list[str]) -> tuple[list[str], list[str]]:
    new_r, upd_r = [], []
    for line in lines:
        lo = line.lower()
        if "新增" in line and "规则" in line:
            new_r.append(line.strip())
        elif "更新" in line and "规则" in line:
            upd_r.append(line.strip())
        elif "added rule" in lo:
            new_r.append(line.strip())
        elif "updated rule" in lo:
            upd_r.append(line.strip())
    return new_r, upd_r


# ══════════════════════════════════════════════════════════════════
# 进程内脚本执行器（EXE / 开发模式通用）
# ══════════════════════════════════════════════════════════════════
class _LogWriter(io.RawIOBase):
    """将 stdout/stderr 重定向到日志队列（线程安全）。"""

    def __init__(self, log_q: queue.Queue, target: tk.Text,
                 collected: list[str]) -> None:
        self._q = log_q
        self._t = target
        self._col = collected
        self._buf = ""

    def write(self, b) -> int:
        s = b if isinstance(b, str) else b.decode("utf-8", errors="replace")
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip()
            if line:
                self._col.append(line)
                self._q.put((line, _lvl(line), self._t))
        return len(b)

    def flush(self) -> None:
        if self._buf.strip():
            self._col.append(self._buf)
            self._q.put((self._buf.rstrip(), _lvl(self._buf), self._t))
            self._buf = ""

    def readable(self) -> bool: return False
    def writable(self) -> bool: return True
    def isatty(self) -> bool:   return False


def _exec_script(script: Path, argv: list[str],
                 log_q: queue.Queue, log_w: tk.Text,
                 collected: list[str]) -> int:
    """
    用 runpy 在当前进程内执行 Python 脚本，捕获输出到日志队列。
    EXE 模式下避免 subprocess 调用自身的问题。
    """
    # 确保脚本目录在搜索路径中
    src_dir = str(script.parent)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    writer = _LogWriter(log_q, log_w, collected)
    old_stdout, old_stderr = sys.stdout, sys.stderr
    old_argv = sys.argv[:]

    # TextIOWrapper 让脚本的 print() 可以正常工作
    tw = io.TextIOWrapper(writer, encoding="utf-8", errors="replace",
                          line_buffering=True)
    sys.stdout = sys.stderr = tw
    sys.argv = [str(script)] + argv

    rc = 0
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as e:
        rc = 0 if (e.code is None or e.code == 0) else 1
    except Exception as exc:
        import traceback
        msg = traceback.format_exc()
        for ln in msg.splitlines():
            collected.append(ln)
            log_q.put((ln, "err", log_w))
        rc = 1
    finally:
        try:
            tw.flush()
        except Exception:
            pass
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv

    return rc


# ══════════════════════════════════════════════════════════════════
# 主应用类
# ══════════════════════════════════════════════════════════════════
class App(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title(f"{APP_NAME}  {APP_VER}   |   {APP_CORP}")
        self.geometry("980x740")
        self.minsize(820, 620)
        self.configure(fg_color=BG_WIN)

        self._running = False
        self._cfg = _load_cfg()
        self._log_q: queue.Queue = queue.Queue()

        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(60, self._poll_log)

        self._log("─" * 50, "dim")
        self._log(f"  {APP_NAME}  {APP_VER}  已启动", "ok")
        self._log(f"  {APP_CORP}", "dim")
        self._log("─" * 50, "dim")
        self._log(f"  源文件目录：{self._cfg['input_dir']}", "info")
        self._log(f"  规则库文件：{self._cfg['rules_file']}", "info")
        self._log(f"  输出目录：{self._cfg['output_dir']}", "info")
        self._log("  就绪，等待执行...", "ok")
        self._log("", "dim")

    # ── Header ───────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=BG_HDR, corner_radius=0, height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkFrame(hdr, fg_color=GOLD, height=3,
                      corner_radius=0).pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=8)

        # Logo
        loaded = False
        if HAS_PIL and _LOGO_PATH.exists():
            try:
                img = Image.open(_LOGO_PATH).convert("RGBA")
                self._logo = ctk.CTkImage(light_image=img, dark_image=img,
                                           size=(48, 48))
                ctk.CTkLabel(inner, image=self._logo, text="").pack(
                    side="left", padx=(0, 14))
                loaded = True
            except Exception:
                pass
        if not loaded:
            ph = ctk.CTkFrame(inner, fg_color="#2A2010", width=48, height=48,
                               corner_radius=6)
            ph.pack(side="left", padx=(0, 14))
            ph.pack_propagate(False)
            ctk.CTkLabel(ph, text="玉\n玄道", font=("Microsoft YaHei", 11, "bold"),
                          text_color=GOLD_LT).place(relx=.5, rely=.5, anchor="center")

        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="y", expand=True)
        ctk.CTkLabel(txt, text=APP_NAME,
                      font=("Microsoft YaHei", 22, "bold"),
                      text_color=GOLD_LT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=APP_CORP,
                      font=("Microsoft YaHei", 10),
                      text_color="#9090A8", anchor="w").pack(anchor="w")

        ctk.CTkLabel(inner, text=APP_VER,
                      font=("Consolas", 11), text_color="#505060").pack(side="right")

    # ── Tabs ─────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        self._tabs = ctk.CTkTabview(
            self,
            fg_color=BG_PANEL,
            segmented_button_fg_color="#E8E0CC",
            segmented_button_selected_color=GOLD,
            segmented_button_selected_hover_color=BTN_HOV,
            segmented_button_unselected_color="#E8E0CC",
            segmented_button_unselected_hover_color="#D8D0B8",
            text_color=TXT_MAIN,
            border_width=1, border_color=BORDER, corner_radius=8,
        )
        self._tabs.pack(fill="both", expand=True, padx=14, pady=(10, 0))
        t1 = self._tabs.add("  ▶  生成报表  ")
        t2 = self._tabs.add("  ✎  修正补录  ")
        self._build_generate_tab(t1)
        self._build_correct_tab(t2)

    # ── 生成报表 Tab ─────────────────────────────────────────────

    def _build_generate_tab(self, parent) -> None:
        self._gi = tk.StringVar(value=self._cfg["input_dir"])
        self._gr = tk.StringVar(value=self._cfg["rules_file"])
        self._go = tk.StringVar(value=self._cfg["output_dir"])
        self._gy = tk.StringVar(value=self._cfg["year"])
        self._gf = tk.BooleanVar(value=self._cfg.get("no_enhance", False))

        # 配置卡（紧凑）
        card = self._card(parent, "目录配置   （配置将自动保存，下次启动无需重新设置）")
        card.pack(fill="x", padx=10, pady=(6, 4))
        self._prow(card, "源文件目录", self._gi, "dir",  self._sync_g)
        self._prow(card, "规则库文件", self._gr, "file", self._sync_g)
        self._prow(card, "输出目录",   self._go, "dir",  self._sync_g)

        # 年份 + 快速模式（一行，紧凑）
        opt = ctk.CTkFrame(card, fg_color="transparent")
        opt.pack(fill="x", padx=14, pady=(4, 10))
        ctk.CTkLabel(opt, text="年  份", width=72, anchor="e",
                      font=("Microsoft YaHei", 11),
                      text_color=TXT_SUB).pack(side="left")
        ctk.CTkEntry(opt, textvariable=self._gy, width=66, height=28,
                      corner_radius=5, fg_color=BG_ENTRY, border_color=BORDER,
                      text_color=TXT_MAIN,
                      font=("Consolas", 12)).pack(side="left", padx=(8, 28))
        ctk.CTkCheckBox(
            opt, text="快速模式（跳过图表美化，速度更快）",
            variable=self._gf,
            font=("Microsoft YaHei", 11), text_color=TXT_SUB,
            fg_color=GOLD, hover_color=GOLD_LT,
            checkmark_color="#FFFFFF", border_color=BORDER,
            command=self._sync_g,
        ).pack(side="left")

        # 按钮行（日志区上方，始终可见）
        bb = ctk.CTkFrame(parent, fg_color=BG_WIN, height=54)
        bb.pack(fill="x", padx=10, pady=(4, 2))
        bb.pack_propagate(False)
        self._btn(bb, "清空日志",      lambda: self._clear(self._gl), False).pack(side="left", pady=9)
        self._btn(bb, "📂 打开输出目录",
                  lambda: _open_dir(self._go.get()), False).pack(side="left", padx=(8, 0), pady=9)
        self._gen_btn = self._btn(bb, "▶   执行生成报表",
                                   self._on_gen, True)
        self._gen_btn.pack(side="right", pady=8)

        # 日志区（占满剩余空间）
        lc = self._card(parent, "执行日志")
        lc.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._gl = self._logbox(lc)

    # ── 修正补录 Tab ─────────────────────────────────────────────

    def _build_correct_tab(self, parent) -> None:
        self._ci = tk.StringVar(value=self._cfg["input_dir"])
        self._cr = tk.StringVar(value=self._cfg["rules_file"])
        self._co = tk.StringVar(value=self._cfg["output_dir"])
        self._cf1 = tk.StringVar()
        self._cf2 = tk.StringVar()

        # 配置卡
        card = self._card(parent, "目录配置   （与生成报表共用，修改自动同步）")
        card.pack(fill="x", padx=10, pady=(6, 4))
        self._prow(card, "源文件目录", self._ci, "dir",  self._sync_c)
        self._prow(card, "规则库文件", self._cr, "file", self._sync_c)
        self._prow(card, "输出目录",   self._co, "dir",  self._sync_c)

        # 待完善报表（可选，留空自动检测）
        rc = self._card(parent,
                         "待完善报表   （留空 = 自动检测输出目录中最新的待完善文件）")
        rc.pack(fill="x", padx=10, pady=(0, 4))
        self._prow(rc, "报表文件 1", self._cf1, "report", None)
        self._prow(rc, "报表文件 2", self._cf2, "report", None)
        ctk.CTkFrame(rc, fg_color="transparent", height=6).pack()  # 底部留白

        # 按钮行（日志区上方，始终可见）
        bb = ctk.CTkFrame(parent, fg_color=BG_WIN, height=54)
        bb.pack(fill="x", padx=10, pady=(4, 2))
        bb.pack_propagate(False)
        self._btn(bb, "清空日志",      lambda: self._clear(self._cl), False).pack(side="left", pady=9)
        self._btn(bb, "📂 打开输出目录",
                  lambda: _open_dir(self._co.get()), False).pack(side="left", padx=(8, 0), pady=9)
        self._cor_btn = self._btn(bb, "✎   执行修正补录",
                                   self._on_cor, True)
        self._cor_btn.pack(side="right", pady=8)

        # 日志区（占满剩余空间）
        lc = self._card(parent, "执行日志")
        lc.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._cl = self._logbox(lc)

    # ── 状态栏 ───────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        ctk.CTkFrame(self, fg_color=GOLD_LINE, height=1,
                      corner_radius=0).pack(fill="x", side="bottom")
        sb = ctk.CTkFrame(self, fg_color="#EDE8DC", height=34, corner_radius=0)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self._sdot = ctk.CTkLabel(sb, text="●", font=("Arial", 13),
                                   text_color=C_OK)
        self._sdot.pack(side="left", padx=(12, 3))
        self._slbl = ctk.CTkLabel(sb, text="就绪",
                                   font=("Microsoft YaHei", 11),
                                   text_color=TXT_SUB)
        self._slbl.pack(side="left")

        ctk.CTkButton(
            sb, text="❓  操作说明", width=96, height=24, corner_radius=5,
            fg_color=GOLD, hover_color=BTN_HOV,
            text_color="#FFFFFF", font=("Microsoft YaHei", 11, "bold"),
            command=self._show_help,
        ).pack(side="right", padx=(0, 12))

        ctk.CTkLabel(sb, text=f"© {APP_YEAR}  {APP_CORP}",
                      font=("Microsoft YaHei", 10),
                      text_color=TXT_DIM).pack(side="right", padx=(0, 16))

    # ── 通用组件 ─────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        w = ctk.CTkFrame(parent, fg_color=BG_CARD,
                          border_color=BORDER, border_width=1, corner_radius=8)
        h = ctk.CTkFrame(w, fg_color=GOLD_BG, corner_radius=0, height=28)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkLabel(h, text=f"  {title}",
                      font=("Microsoft YaHei", 11, "bold"),
                      text_color=GOLD, anchor="w").pack(fill="both",
                                                          expand=True, padx=8)
        ctk.CTkFrame(w, fg_color=GOLD_LINE, height=1,
                      corner_radius=0).pack(fill="x")
        return w

    def _prow(self, parent, label: str, var: tk.StringVar,
              mode: str, cb) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(5, 0))
        ctk.CTkLabel(row, text=label, width=76, anchor="e",
                      font=("Microsoft YaHei", 11),
                      text_color=TXT_SUB).pack(side="left")
        ent = ctk.CTkEntry(row, textvariable=var, height=28, corner_radius=5,
                            fg_color=BG_ENTRY, border_color=BORDER,
                            text_color=TXT_MAIN,
                            font=("Microsoft YaHei", 11))
        ent.pack(side="left", fill="x", expand=True, padx=(8, 6))
        if cb:
            var.trace_add("write", lambda *_: cb())

        def _browse():
            if mode == "dir":
                p = filedialog.askdirectory(title=f"选择{label}")
            elif mode == "file":
                p = filedialog.askopenfilename(
                    title=f"选择{label}",
                    filetypes=[("Excel", "*.xlsx *.xlsm"), ("所有文件", "*.*")])
            else:
                p = filedialog.askopenfilename(
                    title="选择待完善报表",
                    filetypes=[("待完善报表", "*待完善*.xlsx"),
                               ("Excel", "*.xlsx"), ("所有文件", "*.*")])
            if p:
                var.set(_norm(p))

        ctk.CTkButton(row, text="选择", width=50, height=26, corner_radius=5,
                       fg_color=GOLD, hover_color=BTN_HOV,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 11),
                       command=_browse).pack(side="left")

    def _logbox(self, parent) -> tk.Text:
        f = ctk.CTkFrame(parent, fg_color=BG_LOG, corner_radius=0)
        f.pack(fill="both", expand=True)
        t = tk.Text(f, bg=BG_LOG, fg=TXT_LOG, insertbackground=GOLD,
                     font=("Consolas", 11), relief="flat", borderwidth=0,
                     state="disabled", wrap="word",
                     selectbackground="#D4C080", selectforeground=TXT_MAIN)
        sb = tk.Scrollbar(f, command=t.yview, bg="#EEE8D8",
                           troughcolor=BG_LOG, activebackground=GOLD_LINE)
        t.configure(yscrollcommand=sb.set)
        t.tag_configure("ok",   foreground=C_OK,  font=("Consolas", 11, "bold"))
        t.tag_configure("err",  foreground=C_ERR, font=("Consolas", 11, "bold"))
        t.tag_configure("warn", foreground=C_WARN)
        t.tag_configure("info", foreground=C_INFO)
        t.tag_configure("rule", foreground=C_RULE)
        t.tag_configure("dim",  foreground=TXT_DIM)
        t.tag_configure("gold", foreground=GOLD, font=("Consolas", 11, "bold"))
        t.tag_configure("ts",   foreground="#BBAA80")
        sb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True, padx=6, pady=4)
        return t

    def _btn(self, parent, text: str, cmd, primary: bool) -> ctk.CTkButton:
        if primary:
            return ctk.CTkButton(
                parent, text=text, width=160, height=36, corner_radius=8,
                fg_color=BTN_PRI, hover_color=BTN_HOV,
                text_color=BTN_TXT, font=("Microsoft YaHei", 13, "bold"),
                command=cmd)
        return ctk.CTkButton(
            parent, text=text, width=110, height=30, corner_radius=6,
            fg_color="#E8E4DC", hover_color=BORDER,
            text_color=TXT_SUB, font=("Microsoft YaHei", 11),
            command=cmd)

    # ── 日志 ─────────────────────────────────────────────────────

    def _log(self, msg: str, level: str = "info",
             target: tk.Text | None = None) -> None:
        self._log_q.put((msg, level, target))

    def _poll_log(self) -> None:
        try:
            while True:
                msg, level, tgt = self._log_q.get_nowait()
                if tgt is None:
                    tgt = self._gl if "生成" in self._tabs.get() else self._cl
                tgt.configure(state="normal")
                tgt.insert("end", f"[{_ts()}] ", "ts")
                tgt.insert("end", msg + "\n", level)
                tgt.see("end")
                tgt.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(50, self._poll_log)

    def _clear(self, w: tk.Text) -> None:
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.configure(state="disabled")

    # ── 状态 ─────────────────────────────────────────────────────

    def _set_st(self, text: str, color: str = C_OK) -> None:
        self._slbl.configure(text=text)
        self._sdot.configure(text_color=color)

    # ── 配置同步 ─────────────────────────────────────────────────

    def _sync_g(self) -> None:
        self._ci.set(self._gi.get())
        self._cr.set(self._gr.get())
        self._co.set(self._go.get())
        self._flush()

    def _sync_c(self) -> None:
        self._gi.set(self._ci.get())
        self._gr.set(self._cr.get())
        self._go.set(self._co.get())
        self._flush()

    def _flush(self) -> None:
        self._cfg.update({
            "input_dir":  self._gi.get(),
            "rules_file": self._gr.get(),
            "output_dir": self._go.get(),
            "year":       self._gy.get(),
            "no_enhance": self._gf.get(),
        })
        _save_cfg(self._cfg)

    # ── 执行 ─────────────────────────────────────────────────────

    def _on_gen(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行。")
            return
        self._flush()
        argv = [
            "--input",  self._gi.get(),
            "--rules",  self._gr.get(),
            "--output", self._go.get(),
            "--year",   self._gy.get(),
        ]
        if self._gf.get():
            argv.append("--no-enhance")
        self._run(_SRC / "生成报表.py", argv,
                   self._gl, self._gen_btn, "生成报表", None)

    def _on_cor(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行。")
            return
        self._flush()
        argv = [
            "--output", self._co.get(),
            "--rules",  self._cr.get(),
        ]
        files = [f for f in [self._cf1.get(), self._cf2.get()] if f.strip()]
        if files:
            argv += ["--input"] + files
        self._run(_SRC / "修正补录.py", argv,
                   self._cl, self._cor_btn, "修正补录",
                   self._after_cor)

    def _run(self, script: Path, argv: list[str], log_w: tk.Text,
             btn: ctk.CTkButton, label: str, on_done) -> None:
        self._running = True
        btn.configure(state="disabled", text=f"⏳  正在{label}...")
        self._set_st(f"正在执行 {label}...", C_WARN)

        collected: list[str] = []

        def _worker():
            self._log("─" * 46, "dim", log_w)
            self._log(f"开始执行：{label}", "gold", log_w)
            self._log("─" * 46, "dim", log_w)
            rc = _exec_script(script, argv, self._log_q, log_w, collected)
            self.after(0, lambda: _done(rc))

        def _done(rc: int):
            self._running = False
            sep = "─" * 46
            if rc == 0:
                self._log(sep, "dim", log_w)
                self._log(f"✓  {label} 执行成功", "ok", log_w)
                self._log(sep, "dim", log_w)
                self._set_st(f"{label} 完成  ✓", C_OK)
            else:
                self._log(sep, "dim", log_w)
                self._log(f"✗  {label} 执行失败（退出码 {rc}）", "err", log_w)
                self._log(sep, "dim", log_w)
                self._set_st(f"{label} 失败  ✗", C_ERR)
            btn.configure(
                state="normal",
                text="▶   执行生成报表" if label == "生成报表" else "✎   执行修正补录")
            if on_done and rc == 0:
                on_done(collected)

        threading.Thread(target=_worker, daemon=True).start()

    def _after_cor(self, lines: list[str]) -> None:
        new_r, upd_r = _parse_rules(lines)
        if new_r or upd_r:
            self._rule_popup(new_r, upd_r)

    # ── 弹窗 ─────────────────────────────────────────────────────

    def _rule_popup(self, new_r, upd_r) -> None:
        pop = ctk.CTkToplevel(self)
        pop.title("规则更新明细")
        pop.geometry("600x440")
        pop.configure(fg_color=BG_PANEL)
        pop.grab_set()
        ctk.CTkLabel(pop, text="本次规则库更新明细",
                      font=("Microsoft YaHei", 14, "bold"),
                      text_color=GOLD).pack(pady=(16, 2))
        ctk.CTkLabel(pop, text=f"新增 {len(new_r)} 条    更新 {len(upd_r)} 条",
                      font=("Microsoft YaHei", 11),
                      text_color=TXT_SUB).pack(pady=(0, 8))
        ctk.CTkFrame(pop, fg_color=GOLD_LINE, height=1).pack(fill="x", padx=14)
        t = tk.Text(pop, bg=BG_LOG, fg=TXT_LOG, font=("Consolas", 11),
                     relief="flat", state="normal", wrap="word", padx=10, pady=8)
        t.tag_configure("new",  foreground=C_OK, font=("Consolas",11,"bold"))
        t.tag_configure("upd",  foreground=C_WARN)
        t.tag_configure("head", foreground=GOLD, font=("Microsoft YaHei",11,"bold"))
        t.tag_configure("dim",  foreground=TXT_DIM)
        if new_r:
            t.insert("end", f"\n  ✚  新增规则（{len(new_r)} 条）\n", "head")
            t.insert("end", "  " + "─"*44 + "\n", "dim")
            for r in new_r: t.insert("end", f"  {r}\n", "new")
        if upd_r:
            t.insert("end", f"\n  ✎  更新规则（{len(upd_r)} 条）\n", "head")
            t.insert("end", "  " + "─"*44 + "\n", "dim")
            for r in upd_r: t.insert("end", f"  {r}\n", "upd")
        if not new_r and not upd_r:
            t.insert("end", "\n  （本次没有规则变更）\n", "dim")
        t.configure(state="disabled")
        t.pack(fill="both", expand=True, padx=14, pady=(8, 4))
        ctk.CTkButton(pop, text="关闭", width=90, height=30,
                       fg_color=GOLD, hover_color=BTN_HOV,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 12),
                       command=pop.destroy).pack(pady=(4, 12))

    def _show_help(self) -> None:
        pop = ctk.CTkToplevel(self)
        pop.title("操作说明")
        pop.geometry("640x560")
        pop.configure(fg_color=BG_PANEL)
        pop.grab_set()
        hdr = ctk.CTkFrame(pop, fg_color=BG_HDR, corner_radius=0, height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"  {APP_NAME}  操作说明",
                      font=("Microsoft YaHei", 13, "bold"),
                      text_color=GOLD_LT, anchor="w").pack(
            side="left", padx=16, fill="y")
        ctk.CTkLabel(hdr, text=APP_VER, font=("Consolas", 10),
                      text_color="#606070").pack(side="right", padx=16)
        ctk.CTkFrame(pop, fg_color=GOLD, height=2,
                      corner_radius=0).pack(fill="x")
        t = tk.Text(pop, bg=BG_LOG, fg=TXT_LOG,
                     font=("Microsoft YaHei", 11), relief="flat",
                     state="normal", wrap="word", padx=14, pady=10)
        sb = tk.Scrollbar(pop, command=t.yview,
                           bg="#EEE8D8", troughcolor=BG_LOG)
        t.configure(yscrollcommand=sb.set)
        t.insert("end", HELP_TEXT)
        t.configure(state="disabled")
        sb.pack(side="right", fill="y")
        t.pack(fill="both", expand=True)
        ctk.CTkButton(pop, text="关闭", width=90, height=30,
                       fg_color=GOLD, hover_color=BTN_HOV,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 12),
                       command=pop.destroy).pack(pady=10)

    # ── 生命周期 ─────────────────────────────────────────────────

    def _on_close(self) -> None:
        self._flush()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
