#!/usr/bin/env python3
"""
界面.py — 资金统计软件 v2  图形界面入口
========================================

软件名称：资金统计软件
版权所属：玉玄道·资金管理部
版    本：v2.1

使用说明：
    python src/界面.py          # 直接启动 GUI
    # 或通过 PyInstaller 打包后双击 EXE 运行

依赖：
    pip install customtkinter pillow
"""
from __future__ import annotations

import io
import json
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

# ── 尝试导入 customtkinter ─────────────────────────────────────
try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False
    print("请先安装 customtkinter：pip install customtkinter")
    sys.exit(1)

# ── 尝试导入 PIL（Logo 显示用） ────────────────────────────────
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ══════════════════════════════════════════════════════════════════
# 路径常量
# ══════════════════════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    # PyInstaller EXE 模式
    _EXE_DIR = Path(sys.executable).parent
    _ROOT    = _EXE_DIR
    _SRC     = _EXE_DIR / "_internal"
else:
    # 开发模式
    _SRC  = Path(__file__).resolve().parent   # src/
    _ROOT = _SRC.parent                       # project root

_ASSETS     = _ROOT / "assets"
_CONFIG_FILE = _ROOT / "config.json"
_LOGO_PATH  = _ASSETS / "logo.png"

# ══════════════════════════════════════════════════════════════════
# 应用信息
# ══════════════════════════════════════════════════════════════════
APP_NAME  = "资金统计软件"
APP_VER   = "v2.1"
APP_CORP  = "玉玄道·资金管理部"
APP_YEAR  = "2026"
WIN_TITLE = f"{APP_NAME}  {APP_VER}   |   {APP_CORP}"

# ══════════════════════════════════════════════════════════════════
# 配色方案（玉玄道 · 深邃金系）
# ══════════════════════════════════════════════════════════════════
GOLD      = "#C9A24A"
GOLD_LT   = "#E8C875"
GOLD_DIM  = "#7A6228"
GOLD_DARK = "#4A3A14"
BG_DEEP   = "#0D0D1A"
BG_PANEL  = "#14142A"
BG_CARD   = "#1C1C36"
BG_ENTRY  = "#181830"
BG_LOG    = "#10101E"
TXT_MAIN  = "#F0EAD6"
TXT_SUB   = "#8888AA"
TXT_DIM   = "#555575"
C_OK      = "#52C878"
C_WARN    = "#F5A623"
C_ERR     = "#E05050"
C_INFO    = "#7EB8D4"
C_RULE    = "#A882E8"
TXT_LOG   = "#C8C8D8"

# ══════════════════════════════════════════════════════════════════
# 操作说明文本
# ══════════════════════════════════════════════════════════════════
HELP_TEXT = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  资金统计软件  操作说明          版本 v2.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

一、首次使用 — 配置路径

  软件启动后会自动读取上次保存的路径配置。
  首次使用需手动配置以下三个路径：

  【源文件目录】  存放银行流水 Excel 的文件夹
                  （将所有 .xlsx / .xls 放入此目录）
  【规则库文件】  rules/规则库.xlsx 的完整路径
  【输出目录】    报表输出的目标文件夹

  点击路径右侧【选择】按钮选取，路径会自动保存，
  关闭程序后下次启动无需重新配置。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

二、生成报表（每月第一步）

  1. 将当期银行流水文件放入「源文件目录」
  2. 切换到【生成报表】标签页
  3. 确认「年份」正确（默认为当前年份）
  4. 点击【▶ 执行生成报表】
  5. 观察日志区域，等待执行完成
  6. 完成后可点击【打开输出目录】查看报表

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

三、修正补录（如报表含「待完善」字样）

  「待完善」表示有交易记录未能自动分类：

  1. 打开输出目录中带「待完善」的报表文件
  2. 找到带 ★ 的 Sheet（如「★支出未匹配」）
  3. 在【黄色列】填写正确的费用/收入类型、部门
  4. 保存并关闭 Excel 文件（务必关闭！）
  5. 切换到【修正补录】标签页
  6. 点击【▶ 执行修正补录】
  7. 程序将更新规则库，并自动重新生成报表
  8. 完成后弹窗显示本次新增/更新规则的明细

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

四、注意事项

  ◆ 执行前请确保 Excel 文件已完全关闭
  ◆ 规则库会累积学习，补录越多匹配率越高
  ◆ 建议每月执行一次补录以维护规则准确性
  ◆ 日志中红色文字表示错误，黄色表示警告
  ◆ 如遇问题，将日志内容截图反馈给技术支持

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                              技术支持：玉玄道·资金管理部
"""


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════
def _default_config() -> dict:
    return {
        "input_dir":  str(_ROOT / "input"),
        "rules_file": str(_ROOT / "rules" / "规则库.xlsx"),
        "output_dir": str(_ROOT / "output"),
        "year":       str(datetime.now().year),
        "expense_only": False,
        "income_only":  False,
        "no_enhance":   False,
    }


def _load_config() -> dict:
    cfg = _default_config()
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            cfg.update(saved)
        except Exception:
            pass
    return cfg


def _save_config(cfg: dict) -> None:
    try:
        with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 配置保存失败: {e}")


def _ts() -> str:
    """返回当前时间戳字符串。"""
    return datetime.now().strftime("%H:%M:%S")


def _open_dir(path: str) -> None:
    """用系统文件管理器打开目录。"""
    p = Path(path)
    if p.is_file():
        p = p.parent
    if p.exists():
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        elif sys.platform == "win32":
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])


# ══════════════════════════════════════════════════════════════════
# 主应用类
# ══════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    """资金统计软件 主窗口。"""

    def __init__(self) -> None:
        super().__init__()

        # customtkinter 全局主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(WIN_TITLE)
        self.geometry("980x780")
        self.minsize(880, 680)
        self.configure(fg_color=BG_DEEP)

        # 任务运行状态（防止并发）
        self._running = False

        # 加载配置
        self._cfg = _load_config()

        # 消息队列（线程 → UI）
        self._log_q: queue.Queue = queue.Queue()

        # 构建界面
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 启动日志轮询
        self.after(100, self._poll_log_queue)

        # 初始欢迎消息
        self._log(f"{'═'*50}", "dim")
        self._log(f"  {APP_NAME}  {APP_VER}  已启动", "ok")
        self._log(f"  {APP_CORP}", "dim")
        self._log(f"{'═'*50}", "dim")
        self._log(f"  项目目录：{_ROOT}", "info")
        self._log(f"  源文件目录：{self._cfg['input_dir']}", "info")
        self._log(f"  规则库：{self._cfg['rules_file']}", "info")
        self._log(f"  输出目录：{self._cfg['output_dir']}", "info")
        self._log(f"  就绪，等待执行...", "ok")
        self._log("", "dim")

    # ── 界面构建 ──────────────────────────────────────────────────

    def _build_header(self) -> None:
        """顶部 Header：Logo + 软件名 + 副标题。"""
        hdr = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=80)
        hdr.pack(fill="x", padx=0, pady=0)
        hdr.pack_propagate(False)

        # 分隔线（金色）
        bar = ctk.CTkFrame(hdr, fg_color=GOLD, height=3, corner_radius=0)
        bar.pack(side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=10)

        # Logo
        logo_loaded = False
        if HAS_PIL and _LOGO_PATH.exists():
            try:
                img = Image.open(_LOGO_PATH).convert("RGBA")
                img = img.resize((52, 52), Image.LANCZOS)
                self._logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(52, 52))
                lbl = ctk.CTkLabel(inner, image=self._logo_img, text="")
                lbl.pack(side="left", padx=(0, 18))
                logo_loaded = True
            except Exception:
                pass

        if not logo_loaded:
            # 文字替代 Logo（金色方块）
            ph = ctk.CTkFrame(inner, fg_color=GOLD_DARK, width=52, height=52, corner_radius=6)
            ph.pack(side="left", padx=(0, 18))
            ph.pack_propagate(False)
            ctk.CTkLabel(ph, text="玉\n玄道", font=("Microsoft YaHei", 13, "bold"),
                         text_color=GOLD).place(relx=0.5, rely=0.5, anchor="center")

        # 文字区域
        txt_frame = ctk.CTkFrame(inner, fg_color="transparent")
        txt_frame.pack(side="left", fill="y", expand=True)

        ctk.CTkLabel(
            txt_frame, text=APP_NAME,
            font=("Microsoft YaHei", 26, "bold"),
            text_color=GOLD,
            anchor="w",
        ).pack(side="top", anchor="w")

        ctk.CTkLabel(
            txt_frame, text=APP_CORP,
            font=("Microsoft YaHei", 12),
            text_color=TXT_SUB,
            anchor="w",
        ).pack(side="top", anchor="w", pady=(2, 0))

        # 右侧版本号
        ctk.CTkLabel(
            inner, text=APP_VER,
            font=("Consolas", 13),
            text_color=GOLD_DIM,
        ).pack(side="right", padx=(0, 4))

    def _build_tabs(self) -> None:
        """中间主体：TabView。"""
        self._tab_view = ctk.CTkTabview(
            self,
            fg_color=BG_PANEL,
            segmented_button_fg_color=BG_CARD,
            segmented_button_selected_color=GOLD_DARK,
            segmented_button_selected_hover_color=GOLD_DIM,
            segmented_button_unselected_color=BG_CARD,
            segmented_button_unselected_hover_color=BG_CARD,
            text_color=TXT_MAIN,
            text_color_disabled=TXT_DIM,
            border_width=0,
            corner_radius=8,
        )
        self._tab_view.pack(fill="both", expand=True, padx=16, pady=(12, 0))

        tab1 = self._tab_view.add("  ▶  生成报表  ")
        tab2 = self._tab_view.add("  ✎  修正补录  ")

        self._build_generate_tab(tab1)
        self._build_correct_tab(tab2)

    def _build_generate_tab(self, parent: ctk.CTkFrame) -> None:
        """生成报表 Tab 内容。"""
        # ── 路径配置区 ─────────────────────────────────────────────
        self._gen_input_var  = tk.StringVar(value=self._cfg["input_dir"])
        self._gen_rules_var  = tk.StringVar(value=self._cfg["rules_file"])
        self._gen_output_var = tk.StringVar(value=self._cfg["output_dir"])
        self._gen_year_var   = tk.StringVar(value=self._cfg["year"])
        self._gen_expense_var = tk.BooleanVar(value=self._cfg.get("expense_only", False))
        self._gen_income_var  = tk.BooleanVar(value=self._cfg.get("income_only", False))
        self._gen_noenh_var   = tk.BooleanVar(value=self._cfg.get("no_enhance", False))

        cfg_frame = self._make_card(parent, "  目录配置  （配置将自动保存）")
        cfg_frame.pack(fill="x", padx=12, pady=(10, 6))

        rows = [
            ("源文件目录", self._gen_input_var,  "dir"),
            ("规则库文件", self._gen_rules_var,  "file"),
            ("输出目录",   self._gen_output_var, "dir"),
        ]
        for label, var, mode in rows:
            self._make_path_row(cfg_frame, label, var, mode, self._on_gen_config_change)

        # 年份 + 选项行
        opt_row = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        opt_row.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(opt_row, text="年  份", width=80,
                     text_color=TXT_SUB, font=("Microsoft YaHei", 12)).pack(side="left")
        ctk.CTkEntry(
            opt_row, textvariable=self._gen_year_var,
            width=72, height=32, corner_radius=6,
            fg_color=BG_ENTRY, border_color=GOLD_DARK,
            text_color=TXT_MAIN, font=("Consolas", 13),
        ).pack(side="left", padx=(0, 24))

        for text, var in [("仅生成支出", self._gen_expense_var),
                          ("仅生成收入", self._gen_income_var),
                          ("快速模式", self._gen_noenh_var)]:
            ctk.CTkCheckBox(
                opt_row, text=text, variable=var,
                font=("Microsoft YaHei", 12), text_color=TXT_SUB,
                fg_color=GOLD_DIM, hover_color=GOLD,
                checkmark_color=TXT_MAIN, border_color=GOLD_DIM,
                command=self._on_gen_config_change,
            ).pack(side="left", padx=(0, 18))

        # ── 日志区 ────────────────────────────────────────────────
        log_frame = self._make_card(parent, "  执行日志")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        self._gen_log = self._make_log_widget(log_frame)

        # ── 底部按钮 ──────────────────────────────────────────────
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="清空日志",
            width=90, height=34, corner_radius=6,
            fg_color=BG_CARD, hover_color=BG_ENTRY,
            text_color=TXT_SUB, font=("Microsoft YaHei", 12),
            command=lambda: self._clear_log(self._gen_log),
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="📂  打开输出目录",
            width=130, height=34, corner_radius=6,
            fg_color=BG_CARD, hover_color=BG_ENTRY,
            text_color=TXT_SUB, font=("Microsoft YaHei", 12),
            command=lambda: _open_dir(self._gen_output_var.get()),
        ).pack(side="left", padx=(8, 0))

        self._gen_run_btn = ctk.CTkButton(
            btn_row,
            text="▶   执行生成报表",
            width=160, height=38, corner_radius=8,
            fg_color=GOLD_DARK, hover_color=GOLD_DIM,
            text_color=GOLD_LT, font=("Microsoft YaHei", 14, "bold"),
            command=self._on_run_generate,
        )
        self._gen_run_btn.pack(side="right")

    def _build_correct_tab(self, parent: ctk.CTkFrame) -> None:
        """修正补录 Tab 内容。"""
        # 路径配置（与生成报表共用变量）
        self._cor_input_var  = tk.StringVar(value=self._cfg["input_dir"])
        self._cor_rules_var  = tk.StringVar(value=self._cfg["rules_file"])
        self._cor_output_var = tk.StringVar(value=self._cfg["output_dir"])

        # 待完善报表（最多2个）
        self._cor_file1_var = tk.StringVar(value="")
        self._cor_file2_var = tk.StringVar(value="")
        self._cor_auto_var  = tk.BooleanVar(value=True)
        self._cor_norerun_var = tk.BooleanVar(value=False)
        self._cor_dryrun_var  = tk.BooleanVar(value=False)

        # ── 路径配置区 ─────────────────────────────────────────────
        cfg_frame = self._make_card(parent, "  目录配置  （与生成报表共用，修改自动同步）")
        cfg_frame.pack(fill="x", padx=12, pady=(10, 6))

        rows = [
            ("源文件目录", self._cor_input_var,  "dir"),
            ("规则库文件", self._cor_rules_var,  "file"),
            ("输出目录",   self._cor_output_var, "dir"),
        ]
        for label, var, mode in rows:
            self._make_path_row(cfg_frame, label, var, mode, self._on_cor_config_change)

        # 待完善报表区
        rpt_frame = self._make_card(parent, "  待完善报表  （留空则自动检测最新输出目录）")
        rpt_frame.pack(fill="x", padx=12, pady=(0, 6))

        self._make_path_row(rpt_frame, "报表文件 1", self._cor_file1_var, "report", None)
        self._make_path_row(rpt_frame, "报表文件 2", self._cor_file2_var, "report", None)

        opt2_row = ctk.CTkFrame(rpt_frame, fg_color="transparent")
        opt2_row.pack(fill="x", padx=12, pady=(4, 8))

        for text, var in [("仅更新规则（不重新生成报表）", self._cor_norerun_var),
                          ("预览模式（不实际修改）", self._cor_dryrun_var)]:
            ctk.CTkCheckBox(
                opt2_row, text=text, variable=var,
                font=("Microsoft YaHei", 12), text_color=TXT_SUB,
                fg_color=GOLD_DIM, hover_color=GOLD,
                checkmark_color=TXT_MAIN, border_color=GOLD_DIM,
            ).pack(side="left", padx=(0, 20))

        # ── 日志区 ────────────────────────────────────────────────
        log_frame = self._make_card(parent, "  执行日志")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self._cor_log = self._make_log_widget(log_frame)

        # ── 底部按钮 ──────────────────────────────────────────────
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="清空日志",
            width=90, height=34, corner_radius=6,
            fg_color=BG_CARD, hover_color=BG_ENTRY,
            text_color=TXT_SUB, font=("Microsoft YaHei", 12),
            command=lambda: self._clear_log(self._cor_log),
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="📂  打开输出目录",
            width=130, height=34, corner_radius=6,
            fg_color=BG_CARD, hover_color=BG_ENTRY,
            text_color=TXT_SUB, font=("Microsoft YaHei", 12),
            command=lambda: _open_dir(self._cor_output_var.get()),
        ).pack(side="left", padx=(8, 0))

        self._cor_run_btn = ctk.CTkButton(
            btn_row,
            text="✎   执行修正补录",
            width=160, height=38, corner_radius=8,
            fg_color=GOLD_DARK, hover_color=GOLD_DIM,
            text_color=GOLD_LT, font=("Microsoft YaHei", 14, "bold"),
            command=self._on_run_correct,
        )
        self._cor_run_btn.pack(side="right")

    def _build_statusbar(self) -> None:
        """底部状态栏。"""
        # 金色顶边线
        bar = ctk.CTkFrame(self, fg_color=GOLD, height=2, corner_radius=0)
        bar.pack(fill="x", side="bottom")

        sb = ctk.CTkFrame(self, fg_color=BG_PANEL, height=36, corner_radius=0)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        # 状态指示灯 + 文字
        self._status_dot = ctk.CTkLabel(sb, text="●", font=("Arial", 14), text_color=C_OK)
        self._status_dot.pack(side="left", padx=(14, 4))
        self._status_lbl = ctk.CTkLabel(sb, text="就绪", font=("Microsoft YaHei", 12),
                                         text_color=TXT_SUB)
        self._status_lbl.pack(side="left")

        # 右侧：版权 + 操作说明按钮
        ctk.CTkButton(
            sb, text="❓  操作说明",
            width=100, height=26, corner_radius=5,
            fg_color=BG_CARD, hover_color=BG_ENTRY,
            text_color=TXT_SUB, font=("Microsoft YaHei", 11),
            command=self._show_help,
        ).pack(side="right", padx=(0, 14))

        ctk.CTkLabel(
            sb,
            text=f"©  {APP_YEAR}  {APP_CORP}",
            font=("Microsoft YaHei", 11),
            text_color=TXT_DIM,
        ).pack(side="right", padx=(0, 20))

    # ── 通用组件工厂 ──────────────────────────────────────────────

    def _make_card(self, parent, title: str) -> ctk.CTkFrame:
        """创建带标题的卡片容器。"""
        wrapper = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=8)
        ctk.CTkLabel(
            wrapper, text=title,
            font=("Microsoft YaHei", 12, "bold"),
            text_color=GOLD,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 4))
        # 金色细分割线
        ctk.CTkFrame(wrapper, fg_color=GOLD_DARK, height=1, corner_radius=0).pack(
            fill="x", padx=14, pady=(0, 6))
        return wrapper

    def _make_path_row(self, parent, label: str, var: tk.StringVar,
                       mode: str, on_change) -> None:
        """创建一行路径选择控件。"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(3, 3))

        ctk.CTkLabel(row, text=label, width=80,
                     font=("Microsoft YaHei", 12), text_color=TXT_SUB,
                     anchor="e").pack(side="left")

        entry = ctk.CTkEntry(
            row, textvariable=var,
            height=32, corner_radius=6,
            fg_color=BG_ENTRY, border_color=GOLD_DARK,
            text_color=TXT_MAIN, font=("Consolas", 11),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(8, 6))

        if on_change:
            var.trace_add("write", lambda *_: on_change())

        def _browse():
            if mode == "dir":
                p = filedialog.askdirectory(title=f"选择{label}")
            elif mode == "file":
                p = filedialog.askopenfilename(
                    title=f"选择{label}",
                    filetypes=[("Excel 文件", "*.xlsx *.xlsm"), ("所有文件", "*.*")],
                )
            else:  # report
                p = filedialog.askopenfilename(
                    title=f"选择{label}",
                    filetypes=[("待完善报表", "*待完善*.xlsx"), ("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
                )
            if p:
                var.set(p)

        ctk.CTkButton(
            row, text="选择", width=54, height=30, corner_radius=6,
            fg_color=GOLD_DARK, hover_color=GOLD_DIM,
            text_color=GOLD_LT, font=("Microsoft YaHei", 11),
            command=_browse,
        ).pack(side="left")

    def _make_log_widget(self, parent) -> tk.Text:
        """创建日志文本框（带色彩支持）。"""
        frame = ctk.CTkFrame(parent, fg_color=BG_LOG, corner_radius=6)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        txt = tk.Text(
            frame,
            bg=BG_LOG, fg=TXT_LOG, insertbackground=GOLD,
            font=("Consolas", 11),
            relief="flat", borderwidth=0,
            state="disabled", wrap="word",
            selectbackground=GOLD_DARK, selectforeground=TXT_MAIN,
        )
        sb = tk.Scrollbar(frame, command=txt.yview, bg=BG_CARD,
                          troughcolor=BG_LOG, activebackground=GOLD_DIM)
        txt.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True, padx=4, pady=4)

        # 色彩标签
        txt.tag_configure("ok",   foreground=C_OK)
        txt.tag_configure("err",  foreground=C_ERR)
        txt.tag_configure("warn", foreground=C_WARN)
        txt.tag_configure("info", foreground=C_INFO)
        txt.tag_configure("rule", foreground=C_RULE)
        txt.tag_configure("dim",  foreground=TXT_DIM)
        txt.tag_configure("gold", foreground=GOLD)
        txt.tag_configure("ts",   foreground=TXT_DIM)

        return txt

    # ── 日志写入 ──────────────────────────────────────────────────

    def _log(self, msg: str, level: str = "info",
             target: tk.Text | None = None) -> None:
        """将日志消息放入队列（线程安全）。"""
        self._log_q.put((msg, level, target))

    def _poll_log_queue(self) -> None:
        """每 50ms 轮询日志队列，写入 Text 组件。"""
        try:
            while True:
                msg, level, target = self._log_q.get_nowait()
                self._write_log(msg, level, target)
        except queue.Empty:
            pass
        self.after(50, self._poll_log_queue)

    def _write_log(self, msg: str, level: str,
                   target: tk.Text | None = None) -> None:
        """实际写入日志。"""
        # 确定写入哪个 log 组件
        widgets = [self._gen_log, self._cor_log] if target is None else [target]
        # 若指定了 target，则只写入该 target；否则写入当前激活 tab 的 log
        current_tab = self._tab_view.get()
        if target is None:
            if "生成" in current_tab:
                widgets = [self._gen_log]
            else:
                widgets = [self._cor_log]

        for w in widgets:
            w.configure(state="normal")
            ts = f"[{_ts()}] "
            w.insert("end", ts, "ts")
            w.insert("end", msg + "\n", level)
            w.see("end")
            w.configure(state="disabled")

    def _clear_log(self, widget: tk.Text) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    # ── 状态栏 ────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = C_OK) -> None:
        self._status_lbl.configure(text=text)
        self._status_dot.configure(text_color=color)

    # ── 配置同步 ──────────────────────────────────────────────────

    def _on_gen_config_change(self) -> None:
        """生成报表 Tab 的配置变更 → 同步到修正补录 Tab 并保存。"""
        self._cor_input_var.set(self._gen_input_var.get())
        self._cor_rules_var.set(self._gen_rules_var.get())
        self._cor_output_var.set(self._gen_output_var.get())
        self._flush_config()

    def _on_cor_config_change(self) -> None:
        """修正补录 Tab 的配置变更 → 同步到生成报表 Tab 并保存。"""
        self._gen_input_var.set(self._cor_input_var.get())
        self._gen_rules_var.set(self._cor_rules_var.get())
        self._gen_output_var.set(self._cor_output_var.get())
        self._flush_config()

    def _flush_config(self) -> None:
        """将当前界面状态写入 config.json。"""
        self._cfg.update({
            "input_dir":   self._gen_input_var.get(),
            "rules_file":  self._gen_rules_var.get(),
            "output_dir":  self._gen_output_var.get(),
            "year":        self._gen_year_var.get(),
            "expense_only": self._gen_expense_var.get(),
            "income_only":  self._gen_income_var.get(),
            "no_enhance":   self._gen_noenh_var.get(),
        })
        _save_config(self._cfg)

    # ── 执行逻辑 ──────────────────────────────────────────────────

    def _build_generate_cmd(self) -> list[str]:
        """构建 生成报表.py 的命令行参数列表。"""
        script = _SRC / "生成报表.py"
        cmd = [
            sys.executable, str(script),
            "--input",  self._gen_input_var.get(),
            "--rules",  self._gen_rules_var.get(),
            "--output", self._gen_output_var.get(),
            "--year",   self._gen_year_var.get(),
        ]
        if self._gen_expense_var.get():
            cmd.append("--expense-only")
        if self._gen_income_var.get():
            cmd.append("--income-only")
        if self._gen_noenh_var.get():
            cmd.append("--no-enhance")
        return cmd

    def _build_correct_cmd(self) -> list[str]:
        """构建 修正补录.py 的命令行参数列表。"""
        script = _SRC / "修正补录.py"
        cmd = [
            sys.executable, str(script),
            "--output", self._cor_output_var.get(),
            "--rules",  self._cor_rules_var.get(),
        ]
        # 手动指定的报表文件
        files = [
            f for f in [self._cor_file1_var.get(), self._cor_file2_var.get()]
            if f.strip()
        ]
        if files:
            cmd += ["--input"] + files
        if self._cor_norerun_var.get():
            cmd.append("--no-rerun")
        if self._cor_dryrun_var.get():
            cmd.append("--dry-run")
        return cmd

    def _on_run_generate(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行，请稍候...")
            return
        self._flush_config()
        cmd = self._build_generate_cmd()
        self._start_task(cmd, self._gen_log, self._gen_run_btn,
                         label="生成报表", on_done=None)

    def _on_run_correct(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行，请稍候...")
            return
        self._flush_config()
        cmd = self._build_correct_cmd()
        self._start_task(cmd, self._cor_log, self._cor_run_btn,
                         label="修正补录", on_done=self._on_correct_done)

    def _start_task(self, cmd: list[str], log_widget: tk.Text,
                    run_btn: ctk.CTkButton, label: str,
                    on_done) -> None:
        """在后台线程执行命令，实时写入日志。"""
        self._running = True
        run_btn.configure(state="disabled", text=f"⏳  正在{label}...")
        self._set_status(f"正在执行 {label}...", C_WARN)

        collected_lines: list[str] = []

        def _worker():
            self._log(f"{'─'*46}", "dim", log_widget)
            self._log(f"开始执行：{label}", "gold", log_widget)
            self._log(f"命令：{' '.join(cmd)}", "dim", log_widget)
            self._log(f"{'─'*46}", "dim", log_widget)

            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    collected_lines.append(line)
                    lvl = _classify_line(line)
                    self._log(line, lvl, log_widget)

                proc.wait()
                rc = proc.returncode

            except FileNotFoundError:
                self._log(f"错误：找不到脚本文件 {cmd[1]}", "err", log_widget)
                rc = -1
            except Exception as exc:
                self._log(f"执行异常：{exc}", "err", log_widget)
                rc = -1

            # 在主线程更新 UI
            self.after(0, lambda: _finish(rc))

        def _finish(rc: int):
            self._running = False
            if rc == 0:
                self._log(f"{'─'*46}", "dim", log_widget)
                self._log(f"✓  {label} 执行成功", "ok", log_widget)
                self._log(f"{'─'*46}", "dim", log_widget)
                self._set_status(f"{label} 完成  ✓", C_OK)
            else:
                self._log(f"{'─'*46}", "dim", log_widget)
                self._log(f"✗  {label} 执行失败（退出码 {rc}）", "err", log_widget)
                self._log(f"{'─'*46}", "dim", log_widget)
                self._set_status(f"{label} 失败  ✗", C_ERR)

            run_btn.configure(
                state="normal",
                text="▶   执行生成报表" if label == "生成报表" else "✎   执行修正补录",
            )
            if on_done and rc == 0:
                on_done(collected_lines)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_correct_done(self, lines: list[str]) -> None:
        """修正补录完成后，解析规则变更并弹窗展示。"""
        new_rules, upd_rules = _parse_rule_changes(lines)
        if new_rules or upd_rules:
            self._show_rule_summary(new_rules, upd_rules)

    # ── 弹窗 ──────────────────────────────────────────────────────

    def _show_rule_summary(self, new_rules: list[str], upd_rules: list[str]) -> None:
        """弹窗显示规则新增/更新明细。"""
        popup = ctk.CTkToplevel(self)
        popup.title("规则更新明细")
        popup.geometry("640x480")
        popup.configure(fg_color=BG_PANEL)
        popup.grab_set()

        ctk.CTkLabel(
            popup, text="本次规则库更新明细",
            font=("Microsoft YaHei", 16, "bold"), text_color=GOLD,
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            popup,
            text=f"新增规则  {len(new_rules)} 条    更新规则  {len(upd_rules)} 条",
            font=("Microsoft YaHei", 12), text_color=TXT_SUB,
        ).pack(pady=(0, 12))

        txt = tk.Text(
            popup, bg=BG_LOG, fg=TXT_LOG,
            font=("Consolas", 11), relief="flat", state="normal",
            wrap="word", borderwidth=0,
        )
        txt.tag_configure("new",  foreground=C_OK)
        txt.tag_configure("upd",  foreground=C_WARN)
        txt.tag_configure("head", foreground=GOLD, font=("Microsoft YaHei", 12, "bold"))
        txt.tag_configure("dim",  foreground=TXT_DIM)

        if new_rules:
            txt.insert("end", f"\n  ✚  新增规则（{len(new_rules)} 条）\n", "head")
            txt.insert("end", "  " + "─"*50 + "\n", "dim")
            for r in new_rules:
                txt.insert("end", f"  {r}\n", "new")

        if upd_rules:
            txt.insert("end", f"\n  ✎  更新规则（{len(upd_rules)} 条）\n", "head")
            txt.insert("end", "  " + "─"*50 + "\n", "dim")
            for r in upd_rules:
                txt.insert("end", f"  {r}\n", "upd")

        if not new_rules and not upd_rules:
            txt.insert("end", "\n  （本次没有规则变更）\n", "dim")

        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        ctk.CTkButton(
            popup, text="关闭", width=100, height=34, corner_radius=6,
            fg_color=GOLD_DARK, hover_color=GOLD_DIM,
            text_color=GOLD_LT, font=("Microsoft YaHei", 13),
            command=popup.destroy,
        ).pack(pady=(0, 16))

    def _show_help(self) -> None:
        """操作说明弹窗。"""
        popup = ctk.CTkToplevel(self)
        popup.title("操作说明")
        popup.geometry("680x620")
        popup.configure(fg_color=BG_PANEL)
        popup.grab_set()

        # 标题区
        hdr = ctk.CTkFrame(popup, fg_color=BG_CARD, corner_radius=0)
        hdr.pack(fill="x")
        ctk.CTkLabel(
            hdr, text=f"  {APP_NAME}  操作说明",
            font=("Microsoft YaHei", 16, "bold"), text_color=GOLD, anchor="w",
        ).pack(side="left", padx=20, pady=16)
        ctk.CTkLabel(
            hdr, text=APP_VER,
            font=("Consolas", 12), text_color=GOLD_DIM,
        ).pack(side="right", padx=20)
        ctk.CTkFrame(popup, fg_color=GOLD_DARK, height=1, corner_radius=0).pack(fill="x")

        # 内容
        txt = tk.Text(
            popup, bg=BG_LOG, fg=TXT_LOG,
            font=("Microsoft YaHei", 11), relief="flat", state="normal",
            wrap="word", borderwidth=0, padx=10, pady=10,
        )
        sb = tk.Scrollbar(popup, command=txt.yview, bg=BG_CARD,
                          troughcolor=BG_LOG, activebackground=GOLD_DIM)
        txt.configure(yscrollcommand=sb.set)

        txt.tag_configure("title", foreground=GOLD, font=("Microsoft YaHei", 12, "bold"))
        txt.tag_configure("body",  foreground=TXT_LOG)

        txt.insert("end", HELP_TEXT, "body")
        txt.configure(state="disabled")

        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkButton(
            popup, text="关闭", width=100, height=34, corner_radius=6,
            fg_color=GOLD_DARK, hover_color=GOLD_DIM,
            text_color=GOLD_LT, font=("Microsoft YaHei", 13),
            command=popup.destroy,
        ).pack(pady=14)

    # ── 生命周期 ──────────────────────────────────────────────────

    def _on_close(self) -> None:
        """关闭前保存配置。"""
        self._flush_config()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════════

def _classify_line(line: str) -> str:
    """根据行内容猜测日志级别（用于着色）。"""
    lo = line.lower()
    if any(k in lo for k in ("error", "错误", "traceback", "exception", "failed", "失败")):
        return "err"
    if any(k in lo for k in ("warning", "警告", "warn", "注意")):
        return "warn"
    if any(k in lo for k in ("✓", "完成", "success", "成功", "已保存", "已写入")):
        return "ok"
    if any(k in lo for k in ("新增规则", "更新规则", "append", "added rule")):
        return "rule"
    if any(k in lo for k in ("加载", "读取", "loading", "读入", "处理", "匹配")):
        return "info"
    return "info"


def _parse_rule_changes(lines: list[str]) -> tuple[list[str], list[str]]:
    """从子进程输出中解析新增/更新规则行。"""
    new_rules: list[str] = []
    upd_rules: list[str] = []
    for line in lines:
        lo = line.lower()
        if "新增" in line and "规则" in line:
            new_rules.append(line.strip())
        elif "更新" in line and "规则" in line:
            upd_rules.append(line.strip())
        elif "added rule" in lo or "append rule" in lo:
            new_rules.append(line.strip())
        elif "updated rule" in lo or "update rule" in lo:
            upd_rules.append(line.strip())
    return new_rules, upd_rules


# ══════════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
