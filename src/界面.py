#!/usr/bin/env python3
"""
界面.py — 资金统计软件 v2.2  图形界面入口
========================================
软件名称：资金统计软件
版权所属：玉玄道·资金管理部
版    本：v2.2
"""
from __future__ import annotations

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

try:
    import customtkinter as ctk
    HAS_CTK = True
except ImportError:
    HAS_CTK = False
    print("请先安装 customtkinter：pip install customtkinter")
    sys.exit(1)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ══════════════════════════════════════════════════════════════════
# 路径常量（兼容 PyInstaller --onefile 打包）
# ══════════════════════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    # PyInstaller 单文件模式：资源在 _MEIPASS 临时目录，配置写在 EXE 旁边
    _MEIPASS = Path(sys._MEIPASS)
    _EXE_DIR = Path(sys.executable).parent
    _ROOT    = _EXE_DIR          # EXE 所在目录作为项目根（存 config/input/output/rules）
    _SRC     = _MEIPASS          # Python 脚本在 _MEIPASS 里
    _ASSETS  = _MEIPASS / "assets"
else:
    _SRC    = Path(__file__).resolve().parent   # src/
    _ROOT   = _SRC.parent                       # project root
    _ASSETS = _ROOT / "assets"

_CONFIG_FILE = _ROOT / "config.json"
_LOGO_PATH   = _ASSETS / "logo.png"

# ══════════════════════════════════════════════════════════════════
# 应用信息
# ══════════════════════════════════════════════════════════════════
APP_NAME  = "资金统计软件"
APP_VER   = "v2.2"
APP_CORP  = "玉玄道·资金管理部"
APP_YEAR  = "2026"
WIN_TITLE = f"{APP_NAME}  {APP_VER}   |   {APP_CORP}"

# ══════════════════════════════════════════════════════════════════
# 白色主题配色（金色点缀）
# ══════════════════════════════════════════════════════════════════
GOLD       = "#B8860B"      # 深金色（主强调色）
GOLD_LT    = "#D4A820"      # 亮金色
GOLD_BG    = "#FDF8EE"      # 金米色背景
GOLD_LINE  = "#D4C080"      # 金色分割线
BG_WIN     = "#F5F2EC"      # 窗口背景（暖白）
BG_PANEL   = "#FFFFFF"      # 面板白
BG_CARD    = "#FAFAF8"      # 卡片米白
BG_ENTRY   = "#FFFFFF"      # 输入框白
BG_HDR     = "#1A1A2E"      # 顶栏深色（保留品牌感）
BG_LOG     = "#F8F8F6"      # 日志区浅灰
TXT_MAIN   = "#1A1510"      # 主文字深棕黑
TXT_SUB    = "#665A40"      # 次要文字
TXT_DIM    = "#AAA080"      # 弱化文字
TXT_LOG    = "#333320"      # 日志文字
TXT_HDR    = "#F0EAD6"      # 顶栏文字（浅）
BORDER     = "#DDD5BC"      # 通用边框色
C_OK       = "#1A7A2A"      # 成功绿
C_WARN     = "#8A5A00"      # 警告黄褐
C_ERR      = "#A01010"      # 错误红
C_INFO     = "#1A5080"      # 信息蓝
C_RULE     = "#5A35A0"      # 规则紫
BTN_PRI    = "#8A6010"      # 主按钮背景
BTN_PRI_H  = "#6A4800"      # 主按钮悬停
BTN_PRI_T  = "#FFF0C0"      # 主按钮文字

# ══════════════════════════════════════════════════════════════════
# 操作说明文本
# ══════════════════════════════════════════════════════════════════
HELP_TEXT = """\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  资金统计软件  操作说明          v2.2
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
  2. 点击【生成报表】标签页
  3. 确认年份（默认当年）
  4. 点击【▶  执行生成报表】
  5. 查看日志，等待绿色「执行成功」提示
  6. 打开输出目录查看报表

  ◆ 快速模式：跳过迷你图/条件格式等美化步骤，
    速度更快，数据内容完全相同，推荐大文件时使用。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

三、修正补录（报表含「待完善」时）

  报表文件名含「待完善」= 有未能自动分类的交易

  1. 打开「待完善」报表，找到带 ★ 的 Sheet
  2. 在黄色列填写正确的费用/收入类型、承担部门
  3. 保存并关闭 Excel 文件（务必关闭！）
  4. 点击【修正补录】标签页
  5. 点击【✎  执行修正补录】
  6. 完成后弹窗显示本次新增/更新的规则

  ◆ 预览模式（不实际写入）：仅显示将要更新哪些
    规则，不对规则库做任何修改，用于事先核查。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

四、注意事项

  ◆ 执行前请确保相关 Excel 文件已完全关闭
  ◆ 规则库会累积学习，补录越多匹配率越高
  ◆ 日志红色文字表示错误，请截图发给技术支持
  ◆ 如需回退操作，在 output/ 目录保留历史记录

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              技术支持：玉玄道·资金管理部
"""


# ══════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════
def _norm(p: str) -> str:
    """将路径统一为当前系统的斜杠格式。"""
    return str(Path(p)) if p else p


def _default_config() -> dict:
    return {
        "input_dir":    _norm(str(_ROOT / "input")),
        "rules_file":   _norm(str(_ROOT / "rules" / "规则库.xlsx")),
        "output_dir":   _norm(str(_ROOT / "output")),
        "year":         str(datetime.now().year),
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
            # 统一斜杠
            for k in ("input_dir", "rules_file", "output_dir"):
                if k in saved:
                    saved[k] = _norm(saved[k])
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
    return datetime.now().strftime("%H:%M:%S")


def _open_dir(path: str) -> None:
    p = Path(path)
    if p.is_file():
        p = p.parent
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        elif sys.platform == "win32":
            os.startfile(str(p))
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# 主应用类
# ══════════════════════════════════════════════════════════════════
class App(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.title(WIN_TITLE)
        self.geometry("1000x760")
        self.minsize(860, 660)
        self.configure(fg_color=BG_WIN)

        self._running = False
        self._cfg = _load_config()
        self._log_q: queue.Queue = queue.Queue()

        self._build_header()
        self._build_tabs()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(80, self._poll_log_queue)

        # 欢迎日志
        self._log("─" * 52, "dim")
        self._log(f"  {APP_NAME}  {APP_VER}  已启动", "ok")
        self._log(f"  {APP_CORP}", "dim")
        self._log("─" * 52, "dim")
        self._log(f"  源文件目录：{self._cfg['input_dir']}", "info")
        self._log(f"  规则库文件：{self._cfg['rules_file']}", "info")
        self._log(f"  输出目录：{self._cfg['output_dir']}", "info")
        self._log("  就绪，等待执行...", "ok")
        self._log("", "dim")

    # ── Header ────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=BG_HDR, corner_radius=0, height=76)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # 底部金色线
        ctk.CTkFrame(hdr, fg_color=GOLD, height=3, corner_radius=0).pack(
            side="bottom", fill="x")

        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=8)

        # Logo
        logo_ok = False
        if HAS_PIL and _LOGO_PATH.exists():
            try:
                img = Image.open(_LOGO_PATH).convert("RGBA")
                self._logo_img = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(50, 50))
                ctk.CTkLabel(inner, image=self._logo_img, text="").pack(
                    side="left", padx=(0, 16))
                logo_ok = True
            except Exception:
                pass

        if not logo_ok:
            ph = ctk.CTkFrame(inner, fg_color="#2A2010", width=50, height=50,
                               corner_radius=6)
            ph.pack(side="left", padx=(0, 16))
            ph.pack_propagate(False)
            ctk.CTkLabel(ph, text="玉\n玄道",
                          font=("Microsoft YaHei", 12, "bold"),
                          text_color=GOLD_LT).place(relx=.5, rely=.5, anchor="center")

        # 标题
        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="y", expand=True)
        ctk.CTkLabel(txt, text=APP_NAME,
                      font=("Microsoft YaHei", 24, "bold"),
                      text_color=GOLD_LT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt, text=APP_CORP,
                      font=("Microsoft YaHei", 11),
                      text_color="#9090A8", anchor="w").pack(anchor="w", pady=(2, 0))

        # 版本号（右）
        ctk.CTkLabel(inner, text=APP_VER,
                      font=("Consolas", 12), text_color="#505060").pack(side="right")

    # ── Tabs ──────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        self._tab_view = ctk.CTkTabview(
            self,
            fg_color=BG_PANEL,
            segmented_button_fg_color="#E8E0CC",
            segmented_button_selected_color=GOLD,
            segmented_button_selected_hover_color=BTN_PRI_H,
            segmented_button_unselected_color="#E8E0CC",
            segmented_button_unselected_hover_color="#D8D0B8",
            text_color=TXT_MAIN,
            border_width=1,
            border_color=BORDER,
            corner_radius=8,
        )
        self._tab_view.pack(fill="both", expand=True, padx=14, pady=(10, 0))

        tab1 = self._tab_view.add("  ▶  生成报表  ")
        tab2 = self._tab_view.add("  ✎  修正补录  ")

        self._build_generate_tab(tab1)
        self._build_correct_tab(tab2)

    def _build_generate_tab(self, parent) -> None:
        # ── 路径配置卡片 ──────────────────────────────────────────
        self._gen_input_var   = tk.StringVar(value=self._cfg["input_dir"])
        self._gen_rules_var   = tk.StringVar(value=self._cfg["rules_file"])
        self._gen_output_var  = tk.StringVar(value=self._cfg["output_dir"])
        self._gen_year_var    = tk.StringVar(value=self._cfg["year"])
        self._gen_expense_var = tk.BooleanVar(value=self._cfg.get("expense_only", False))
        self._gen_income_var  = tk.BooleanVar(value=self._cfg.get("income_only", False))
        self._gen_noenh_var   = tk.BooleanVar(value=self._cfg.get("no_enhance", False))

        cfg_card = self._card(parent, "目录配置   （配置将自动保存，下次启动无需重新设置）")
        cfg_card.pack(fill="x", padx=10, pady=(8, 4))

        for label, var, mode in [
            ("源文件目录", self._gen_input_var,  "dir"),
            ("规则库文件", self._gen_rules_var,  "file"),
            ("输出目录",   self._gen_output_var, "dir"),
        ]:
            self._path_row(cfg_card, label, var, mode, self._sync_gen)

        # 年份 + 选项
        opt = ctk.CTkFrame(cfg_card, fg_color="transparent")
        opt.pack(fill="x", padx=14, pady=(4, 12))

        ctk.CTkLabel(opt, text="年  份", width=72,
                      font=("Microsoft YaHei", 12), text_color=TXT_SUB,
                      anchor="e").pack(side="left")
        ctk.CTkEntry(opt, textvariable=self._gen_year_var, width=68, height=30,
                      corner_radius=5, fg_color=BG_ENTRY, border_color=BORDER,
                      text_color=TXT_MAIN, font=("Consolas", 13)).pack(
            side="left", padx=(8, 24))

        for text, var, tip in [
            ("仅生成支出", self._gen_expense_var, ""),
            ("仅生成收入", self._gen_income_var,  ""),
            ("快速模式（跳过图表美化）", self._gen_noenh_var, ""),
        ]:
            ctk.CTkCheckBox(
                opt, text=text, variable=var,
                font=("Microsoft YaHei", 11), text_color=TXT_SUB,
                fg_color=GOLD, hover_color=GOLD_LT,
                checkmark_color="#FFFFFF", border_color=BORDER,
                command=self._sync_gen,
            ).pack(side="left", padx=(0, 20))

        # ── 日志区（填充剩余空间） ────────────────────────────────
        log_card = self._card(parent, "执行日志")
        log_card.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self._gen_log = self._log_widget(log_card)

        # ── 底部按钮行（固定在下方） ──────────────────────────────
        btn_bar = ctk.CTkFrame(parent, fg_color=BG_WIN, height=52)
        btn_bar.pack(fill="x", padx=10, pady=(0, 8))
        btn_bar.pack_propagate(False)

        ctk.CTkButton(btn_bar, text="清空日志", width=86, height=34,
                       corner_radius=6, fg_color="#E8E4DC", hover_color=BORDER,
                       text_color=TXT_SUB, font=("Microsoft YaHei", 11),
                       command=lambda: self._clear_log(self._gen_log),
                       ).pack(side="left", pady=9)

        ctk.CTkButton(btn_bar, text="📂  打开输出目录", width=130, height=34,
                       corner_radius=6, fg_color="#E8E4DC", hover_color=BORDER,
                       text_color=TXT_SUB, font=("Microsoft YaHei", 11),
                       command=lambda: _open_dir(self._gen_output_var.get()),
                       ).pack(side="left", padx=(8, 0), pady=9)

        self._gen_run_btn = ctk.CTkButton(
            btn_bar, text="▶   执行生成报表",
            width=168, height=38, corner_radius=8,
            fg_color=BTN_PRI, hover_color=BTN_PRI_H,
            text_color=BTN_PRI_T, font=("Microsoft YaHei", 14, "bold"),
            command=self._on_run_generate,
        )
        self._gen_run_btn.pack(side="right", pady=7)

    def _build_correct_tab(self, parent) -> None:
        self._cor_input_var   = tk.StringVar(value=self._cfg["input_dir"])
        self._cor_rules_var   = tk.StringVar(value=self._cfg["rules_file"])
        self._cor_output_var  = tk.StringVar(value=self._cfg["output_dir"])
        self._cor_file1_var   = tk.StringVar()
        self._cor_file2_var   = tk.StringVar()
        self._cor_norerun_var = tk.BooleanVar(value=False)
        self._cor_dryrun_var  = tk.BooleanVar(value=False)

        # 路径配置
        cfg_card = self._card(parent, "目录配置   （与生成报表共用，修改自动同步）")
        cfg_card.pack(fill="x", padx=10, pady=(8, 4))
        for label, var, mode in [
            ("源文件目录", self._cor_input_var,  "dir"),
            ("规则库文件", self._cor_rules_var,  "file"),
            ("输出目录",   self._cor_output_var, "dir"),
        ]:
            self._path_row(cfg_card, label, var, mode, self._sync_cor)

        # 待完善报表
        rpt_card = self._card(parent, "待完善报表   （留空 = 自动检测输出目录中最新的待完善文件）")
        rpt_card.pack(fill="x", padx=10, pady=(0, 4))
        self._path_row(rpt_card, "报表文件 1", self._cor_file1_var, "report", None)
        self._path_row(rpt_card, "报表文件 2", self._cor_file2_var, "report", None)

        opt2 = ctk.CTkFrame(rpt_card, fg_color="transparent")
        opt2.pack(fill="x", padx=14, pady=(4, 12))
        for text, var in [
            ("仅更新规则库（不重新生成报表）", self._cor_norerun_var),
            ("预览模式（仅查看将写入的规则，不实际修改）", self._cor_dryrun_var),
        ]:
            ctk.CTkCheckBox(
                opt2, text=text, variable=var,
                font=("Microsoft YaHei", 11), text_color=TXT_SUB,
                fg_color=GOLD, hover_color=GOLD_LT,
                checkmark_color="#FFFFFF", border_color=BORDER,
            ).pack(side="left", padx=(0, 24))

        # 日志
        log_card = self._card(parent, "执行日志")
        log_card.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        self._cor_log = self._log_widget(log_card)

        # 按钮行
        btn_bar = ctk.CTkFrame(parent, fg_color=BG_WIN, height=52)
        btn_bar.pack(fill="x", padx=10, pady=(0, 8))
        btn_bar.pack_propagate(False)

        ctk.CTkButton(btn_bar, text="清空日志", width=86, height=34,
                       corner_radius=6, fg_color="#E8E4DC", hover_color=BORDER,
                       text_color=TXT_SUB, font=("Microsoft YaHei", 11),
                       command=lambda: self._clear_log(self._cor_log),
                       ).pack(side="left", pady=9)

        ctk.CTkButton(btn_bar, text="📂  打开输出目录", width=130, height=34,
                       corner_radius=6, fg_color="#E8E4DC", hover_color=BORDER,
                       text_color=TXT_SUB, font=("Microsoft YaHei", 11),
                       command=lambda: _open_dir(self._cor_output_var.get()),
                       ).pack(side="left", padx=(8, 0), pady=9)

        self._cor_run_btn = ctk.CTkButton(
            btn_bar, text="✎   执行修正补录",
            width=168, height=38, corner_radius=8,
            fg_color=BTN_PRI, hover_color=BTN_PRI_H,
            text_color=BTN_PRI_T, font=("Microsoft YaHei", 14, "bold"),
            command=self._on_run_correct,
        )
        self._cor_run_btn.pack(side="right", pady=7)

    # ── 状态栏 ────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        ctk.CTkFrame(self, fg_color=GOLD_LINE, height=1,
                      corner_radius=0).pack(fill="x", side="bottom")

        sb = ctk.CTkFrame(self, fg_color="#EDE8DC", height=36,
                           corner_radius=0)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self._status_dot = ctk.CTkLabel(sb, text="●", font=("Arial", 14),
                                         text_color=C_OK)
        self._status_dot.pack(side="left", padx=(14, 4))
        self._status_lbl = ctk.CTkLabel(sb, text="就绪",
                                         font=("Microsoft YaHei", 11),
                                         text_color=TXT_SUB)
        self._status_lbl.pack(side="left")

        # 操作说明按钮（右侧，醒目）
        ctk.CTkButton(
            sb, text="❓  操作说明",
            width=100, height=26, corner_radius=5,
            fg_color=GOLD, hover_color=BTN_PRI_H,
            text_color="#FFFFFF", font=("Microsoft YaHei", 11, "bold"),
            command=self._show_help,
        ).pack(side="right", padx=(0, 14))

        ctk.CTkLabel(sb, text=f"© {APP_YEAR}  {APP_CORP}",
                      font=("Microsoft YaHei", 11),
                      text_color=TXT_DIM).pack(side="right", padx=(0, 18))

    # ── 通用组件 ──────────────────────────────────────────────────

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        w = ctk.CTkFrame(parent, fg_color=BG_CARD,
                          border_color=BORDER, border_width=1, corner_radius=8)
        hdr = ctk.CTkFrame(w, fg_color=GOLD_BG, corner_radius=0, height=32)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"  {title}",
                      font=("Microsoft YaHei", 11, "bold"),
                      text_color=GOLD, anchor="w").pack(fill="both",
                                                          expand=True, padx=8)
        ctk.CTkFrame(w, fg_color=GOLD_LINE, height=1,
                      corner_radius=0).pack(fill="x")
        return w

    def _path_row(self, parent, label: str, var: tk.StringVar,
                  mode: str, on_change) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(6, 0))

        ctk.CTkLabel(row, text=label, width=76,
                      font=("Microsoft YaHei", 11), text_color=TXT_SUB,
                      anchor="e").pack(side="left")

        ent = ctk.CTkEntry(row, textvariable=var, height=30, corner_radius=5,
                            fg_color=BG_ENTRY, border_color=BORDER,
                            text_color=TXT_MAIN, font=("Microsoft YaHei", 11))
        ent.pack(side="left", fill="x", expand=True, padx=(8, 6))

        if on_change:
            var.trace_add("write", lambda *_: on_change())

        def _browse():
            if mode == "dir":
                p = filedialog.askdirectory(title=f"选择{label}")
            elif mode == "file":
                p = filedialog.askopenfilename(
                    title=f"选择{label}",
                    filetypes=[("Excel 文件", "*.xlsx *.xlsm"), ("所有文件", "*.*")])
            else:
                p = filedialog.askopenfilename(
                    title="选择待完善报表",
                    filetypes=[("待完善报表", "*待完善*.xlsx"),
                               ("Excel 文件", "*.xlsx"), ("所有文件", "*.*")])
            if p:
                var.set(_norm(p))

        ctk.CTkButton(row, text="选择", width=52, height=28, corner_radius=5,
                       fg_color=GOLD, hover_color=BTN_PRI_H,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 11),
                       command=_browse).pack(side="left")

    def _log_widget(self, parent) -> tk.Text:
        frame = ctk.CTkFrame(parent, fg_color=BG_LOG,
                              corner_radius=0, border_width=0)
        frame.pack(fill="both", expand=True, padx=0, pady=0)

        txt = tk.Text(frame, bg=BG_LOG, fg=TXT_LOG, insertbackground=GOLD,
                       font=("Consolas", 11), relief="flat", borderwidth=0,
                       state="disabled", wrap="word",
                       selectbackground="#D4C080", selectforeground=TXT_MAIN)
        sb = tk.Scrollbar(frame, command=txt.yview,
                           bg="#EEE8D8", troughcolor=BG_LOG,
                           activebackground=GOLD_LINE)
        txt.configure(yscrollcommand=sb.set)

        # 颜色标签
        txt.tag_configure("ok",   foreground=C_OK,   font=("Consolas", 11, "bold"))
        txt.tag_configure("err",  foreground=C_ERR,  font=("Consolas", 11, "bold"))
        txt.tag_configure("warn", foreground=C_WARN)
        txt.tag_configure("info", foreground=C_INFO)
        txt.tag_configure("rule", foreground=C_RULE)
        txt.tag_configure("dim",  foreground=TXT_DIM)
        txt.tag_configure("gold", foreground=GOLD,   font=("Consolas", 11, "bold"))
        txt.tag_configure("ts",   foreground="#BBAA88")

        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True, padx=6, pady=4)
        return txt

    # ── 日志 ──────────────────────────────────────────────────────

    def _log(self, msg: str, level: str = "info",
             target: tk.Text | None = None) -> None:
        self._log_q.put((msg, level, target))

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg, level, target = self._log_q.get_nowait()
                self._write_log(msg, level, target)
        except queue.Empty:
            pass
        self.after(50, self._poll_log_queue)

    def _write_log(self, msg: str, level: str,
                   target: tk.Text | None) -> None:
        if target is None:
            cur = self._tab_view.get()
            target = self._gen_log if "生成" in cur else self._cor_log
        target.configure(state="normal")
        target.insert("end", f"[{_ts()}] ", "ts")
        target.insert("end", msg + "\n", level)
        target.see("end")
        target.configure(state="disabled")

    def _clear_log(self, w: tk.Text) -> None:
        w.configure(state="normal")
        w.delete("1.0", "end")
        w.configure(state="disabled")

    # ── 状态栏 ────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = C_OK) -> None:
        self._status_lbl.configure(text=text)
        self._status_dot.configure(text_color=color)

    # ── 配置同步 ──────────────────────────────────────────────────

    def _sync_gen(self) -> None:
        self._cor_input_var.set(self._gen_input_var.get())
        self._cor_rules_var.set(self._gen_rules_var.get())
        self._cor_output_var.set(self._gen_output_var.get())
        self._flush_config()

    def _sync_cor(self) -> None:
        self._gen_input_var.set(self._cor_input_var.get())
        self._gen_rules_var.set(self._cor_rules_var.get())
        self._gen_output_var.set(self._cor_output_var.get())
        self._flush_config()

    def _flush_config(self) -> None:
        self._cfg.update({
            "input_dir":    self._gen_input_var.get(),
            "rules_file":   self._gen_rules_var.get(),
            "output_dir":   self._gen_output_var.get(),
            "year":         self._gen_year_var.get(),
            "expense_only": self._gen_expense_var.get(),
            "income_only":  self._gen_income_var.get(),
            "no_enhance":   self._gen_noenh_var.get(),
        })
        _save_config(self._cfg)

    # ── 执行逻辑 ──────────────────────────────────────────────────

    def _gen_cmd(self) -> list[str]:
        script = str(_SRC / "生成报表.py")
        cmd = [sys.executable, script,
               "--input",  self._gen_input_var.get(),
               "--rules",  self._gen_rules_var.get(),
               "--output", self._gen_output_var.get(),
               "--year",   self._gen_year_var.get()]
        if self._gen_expense_var.get(): cmd.append("--expense-only")
        if self._gen_income_var.get():  cmd.append("--income-only")
        if self._gen_noenh_var.get():   cmd.append("--no-enhance")
        return cmd

    def _cor_cmd(self) -> list[str]:
        script = str(_SRC / "修正补录.py")
        cmd = [sys.executable, script,
               "--output", self._cor_output_var.get(),
               "--rules",  self._cor_rules_var.get()]
        files = [f for f in [self._cor_file1_var.get(),
                              self._cor_file2_var.get()] if f.strip()]
        if files:
            cmd += ["--input"] + files
        if self._cor_norerun_var.get(): cmd.append("--no-rerun")
        if self._cor_dryrun_var.get():  cmd.append("--dry-run")
        return cmd

    def _on_run_generate(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行，请等待完成后再操作。")
            return
        self._flush_config()
        self._run_task(self._gen_cmd(), self._gen_log,
                       self._gen_run_btn, "生成报表", None)

    def _on_run_correct(self) -> None:
        if self._running:
            messagebox.showwarning("请等待", "当前有任务正在执行，请等待完成后再操作。")
            return
        self._flush_config()
        self._run_task(self._cor_cmd(), self._cor_log,
                       self._cor_run_btn, "修正补录", self._on_correct_done)

    def _run_task(self, cmd, log_w, btn, label, on_done) -> None:
        self._running = True
        btn.configure(state="disabled", text=f"⏳  正在{label}...")
        self._set_status(f"正在执行 {label}...", C_WARN)

        collected: list[str] = []

        def _worker():
            self._log("─" * 48, "dim", log_w)
            self._log(f"开始执行：{label}", "gold", log_w)
            self._log(f"命令：{' '.join(cmd)}", "dim", log_w)
            self._log("─" * 48, "dim", log_w)
            rc = -1
            try:
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env)
                for line in proc.stdout:
                    line = line.rstrip()
                    if not line:
                        continue
                    collected.append(line)
                    self._log(line, _lvl(line), log_w)
                proc.wait()
                rc = proc.returncode
            except FileNotFoundError:
                self._log(f"错误：找不到脚本 {cmd[1]}", "err", log_w)
            except Exception as e:
                self._log(f"执行异常：{e}", "err", log_w)
            self.after(0, lambda: _done(rc))

        def _done(rc):
            self._running = False
            sep = "─" * 48
            if rc == 0:
                self._log(sep, "dim", log_w)
                self._log(f"✓  {label} 执行成功", "ok", log_w)
                self._log(sep, "dim", log_w)
                self._set_status(f"{label} 完成  ✓", C_OK)
            else:
                self._log(sep, "dim", log_w)
                self._log(f"✗  {label} 执行失败（退出码 {rc}）", "err", log_w)
                self._log(sep, "dim", log_w)
                self._set_status(f"{label} 失败  ✗", C_ERR)
            btn.configure(state="normal",
                           text="▶   执行生成报表" if label == "生成报表"
                           else "✎   执行修正补录")
            if on_done and rc == 0:
                on_done(collected)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_correct_done(self, lines: list[str]) -> None:
        new_r, upd_r = _parse_rules(lines)
        if new_r or upd_r:
            self._show_rule_summary(new_r, upd_r)

    # ── 弹窗 ──────────────────────────────────────────────────────

    def _show_rule_summary(self, new_r, upd_r) -> None:
        pop = ctk.CTkToplevel(self)
        pop.title("规则更新明细")
        pop.geometry("620x460")
        pop.configure(fg_color=BG_PANEL)
        pop.grab_set()

        ctk.CTkLabel(pop, text="本次规则库更新明细",
                      font=("Microsoft YaHei", 15, "bold"),
                      text_color=GOLD).pack(pady=(18, 2))
        ctk.CTkLabel(pop,
                      text=f"新增  {len(new_r)} 条    更新  {len(upd_r)} 条",
                      font=("Microsoft YaHei", 11),
                      text_color=TXT_SUB).pack(pady=(0, 10))
        ctk.CTkFrame(pop, fg_color=GOLD_LINE, height=1).pack(fill="x", padx=16)

        txt = tk.Text(pop, bg=BG_LOG, fg=TXT_LOG, font=("Consolas", 11),
                       relief="flat", state="normal", wrap="word", padx=10, pady=8)
        txt.tag_configure("new",  foreground=C_OK, font=("Consolas", 11, "bold"))
        txt.tag_configure("upd",  foreground=C_WARN)
        txt.tag_configure("head", foreground=GOLD, font=("Microsoft YaHei", 11, "bold"))
        txt.tag_configure("dim",  foreground=TXT_DIM)

        if new_r:
            txt.insert("end", f"\n  ✚  新增规则（{len(new_r)} 条）\n", "head")
            txt.insert("end", "  " + "─" * 46 + "\n", "dim")
            for r in new_r:
                txt.insert("end", f"  {r}\n", "new")
        if upd_r:
            txt.insert("end", f"\n  ✎  更新规则（{len(upd_r)} 条）\n", "head")
            txt.insert("end", "  " + "─" * 46 + "\n", "dim")
            for r in upd_r:
                txt.insert("end", f"  {r}\n", "upd")
        if not new_r and not upd_r:
            txt.insert("end", "\n  （本次没有规则变更）\n", "dim")

        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=16, pady=(8, 4))
        ctk.CTkButton(pop, text="关闭", width=100, height=32,
                       fg_color=GOLD, hover_color=BTN_PRI_H,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 12),
                       command=pop.destroy).pack(pady=(4, 14))

    def _show_help(self) -> None:
        pop = ctk.CTkToplevel(self)
        pop.title("操作说明")
        pop.geometry("660x580")
        pop.configure(fg_color=BG_PANEL)
        pop.grab_set()

        hdr = ctk.CTkFrame(pop, fg_color=BG_HDR, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"  {APP_NAME}  操作说明",
                      font=("Microsoft YaHei", 14, "bold"),
                      text_color=GOLD_LT, anchor="w").pack(
            side="left", padx=18, fill="y")
        ctk.CTkLabel(hdr, text=APP_VER, font=("Consolas", 11),
                      text_color="#606070").pack(side="right", padx=18)
        ctk.CTkFrame(pop, fg_color=GOLD, height=2, corner_radius=0).pack(fill="x")

        txt = tk.Text(pop, bg=BG_LOG, fg=TXT_LOG,
                       font=("Microsoft YaHei", 11), relief="flat",
                       state="normal", wrap="word", padx=14, pady=10)
        sb = tk.Scrollbar(pop, command=txt.yview,
                           bg="#EEE8D8", troughcolor=BG_LOG)
        txt.configure(yscrollcommand=sb.set)
        txt.insert("end", HELP_TEXT)
        txt.configure(state="disabled")
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)

        ctk.CTkButton(pop, text="关闭", width=100, height=32,
                       fg_color=GOLD, hover_color=BTN_PRI_H,
                       text_color="#FFFFFF", font=("Microsoft YaHei", 12),
                       command=pop.destroy).pack(pady=12)

    # ── 生命周期 ──────────────────────────────────────────────────

    def _on_close(self) -> None:
        self._flush_config()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════════
def _lvl(line: str) -> str:
    lo = line.lower()
    if any(k in lo for k in ("error", "错误", "traceback", "exception",
                               "failed", "失败", "✗")):
        return "err"
    if any(k in lo for k in ("warning", "警告", "warn", "注意")):
        return "warn"
    if any(k in lo for k in ("✓", "完成", "success", "成功", "已保存", "已写入")):
        return "ok"
    if any(k in lo for k in ("新增规则", "更新规则", "added rule")):
        return "rule"
    if any(k in lo for k in ("加载", "读取", "loading", "处理", "匹配", "生成")):
        return "info"
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
# 入口
# ══════════════════════════════════════════════════════════════════
def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
