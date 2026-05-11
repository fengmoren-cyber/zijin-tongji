#!/usr/bin/env python3
"""
生成报表.py — 银行流水报表系统 v2  入口一
==========================================

功能
----
从 input/ 目录读取银行流水，自动加载 rules/规则库.xlsx 中的分类规则，
同时生成：
  ① 支出统计报表（含各账户余额汇总、AutoFilter、完整度状态列）
  ② 收入统计报表（含收支综合对比 Sheet、Sparkline 迷你图）

输出目录结构
-----------
  output/
    YYYYMMDD_NNN/                              ← 本次运行专属子目录
      {year}年银行【支出】全年统计_终稿.xlsx        ← 全部匹配时
      {year}年银行【支出】全年统计_待完善.xlsx       ← 含未匹配记录时
        └─ Sheet "★支出未匹配（可补规则）"          ← 财务人员填写黄色列
      {year}年银行【收入】全年统计_终稿.xlsx
      {year}年银行【收入】全年统计_待完善.xlsx
        └─ Sheet "★收入未匹配（可补规则）"

典型工作流
----------
  第一步：python src/生成报表.py
  第二步（如有未匹配）：
    • 打开 _待完善 报表，在黄色列填写修正类型/部门
    • python src/修正补录.py --input <文件1> [<文件2>]
    • 修正补录 会更新 rules/规则库.xlsx 并重新生成报表

用法示例
--------
  python src/生成报表.py                  # 全年（推荐）
  python src/生成报表.py --year 2026      # 指定年份
  python src/生成报表.py --expense-only   # 仅生成支出报表
  python src/生成报表.py --income-only    # 仅生成收入报表
  python src/生成报表.py --no-enhance     # 跳过增强（快速模式）
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

# 将 src/ 加入搜索路径，支持从项目根目录调用
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _核心库 import (
    DEFAULT_INPUT_DIR,
    DEFAULT_MAPPING_PATH,
    DEFAULT_INCOME_MAPPING_PATH,
    DEFAULT_OUTPUT_DIR,
    build_annual_workbook,
    build_annual_income_workbook,
    build_balance_sheet_monthly,
    classify_expense_records,
    classify_income_records,
    dedupe_records,
    embed_expense_unmatched_sheet,
    embed_income_unmatched_sheet,
    infer_report_year,
    is_intragroup,
    is_unmatched,
    is_income_intragroup,
    is_income_unmatched,
    load_classification_rules,
    load_income_classification_rules,
    next_run_dir,
    read_records,
    save_expense_workbook_v2,
    save_income_workbook_v2,
    build_comparison_sheet,
    apply_autofilter_and_freeze,
    add_balance_status_column,
    prepare_sparkline_specs,
    inject_sparklines,
)


# ─────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成报表.py：读取银行流水，生成支出与收入统计报表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--year", type=int,
        help="全年统计年份（不传时自动从流水中识别最新年份）",
    )
    parser.add_argument(
        "--expense-only", action="store_true",
        help="仅生成支出统计，跳过收入统计",
    )
    parser.add_argument(
        "--income-only", action="store_true",
        help="仅生成收入统计，跳过支出统计",
    )
    parser.add_argument(
        "--no-enhance", action="store_true",
        help="跳过增强功能（收支对比 / AutoFilter / Sparkline），加快运行速度",
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT_DIR,
        help=f"银行流水目录（默认：{DEFAULT_INPUT_DIR.name}/）",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录（默认：{DEFAULT_OUTPUT_DIR.name}/）",
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
def _to_enhance_data(items, amount_attr: str, type_attr: str) -> list[tuple]:
    """将分类结果转换为增强功能所需的 (公司, 月份, 金额, 类型) 格式。"""
    result = []
    for item in items:
        rec = item.record
        amt = float(getattr(rec, amount_attr, 0) or 0)
        if amt <= 0:
            continue
        d = getattr(rec, "trade_date", None) or getattr(rec, "date", None)
        month = d.month if hasattr(d, "month") else 0
        cat   = getattr(item, type_attr, "")
        result.append((rec.company, month, amt, cat))
    return result


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()
    enhance = not args.no_enhance

    # ── 校验输入目录 ──────────────────────────────────────────────────────────
    if not args.input.exists():
        raise SystemExit(f"❌ 输入目录不存在：{args.input}")

    if enhance:
        print("✨ 报表增强：已启用（收支对比 / AutoFilter / Sparkline）")

    # ── 读取流水 ──────────────────────────────────────────────────────────────
    print(f"\n📂 读取银行流水：{args.input}")
    records = read_records(args.input)
    raw_count = len(records)
    records = dedupe_records(records)
    print(f"   共 {raw_count} 条，去重后 {len(records)} 条有效记录")

    if not records:
        raise SystemExit("❌ input/ 目录中未读取到任何流水记录，请检查文件格式")

    # ── 识别年份 ──────────────────────────────────────────────────────────────
    year = infer_report_year(records, args.year)
    source_count = sum(
        1 for p in args.input.iterdir()
        if p.is_file() and not p.name.startswith(".")
    )

    # ── 加载规则 ──────────────────────────────────────────────────────────────
    rules        = None
    income_rules = None

    if not args.income_only:
        print(f"📋 加载支出分类规则：{DEFAULT_MAPPING_PATH.name}")
        if not DEFAULT_MAPPING_PATH.exists():
            print("   ⚠️  规则文件不存在，将使用内置默认关键词规则")
        rules = load_classification_rules(DEFAULT_MAPPING_PATH)
        print(f"   精确映射 {len(rules.exact)} 条 / 关键词规则 {len(rules.keyword)} 条")

    if not args.expense_only:
        print(f"📋 加载收入分类规则：{DEFAULT_INCOME_MAPPING_PATH.name}")
        if not DEFAULT_INCOME_MAPPING_PATH.exists():
            print("   ⚠️  收入规则文件不存在，将使用内置默认关键词规则")
        income_rules = load_income_classification_rules(DEFAULT_INCOME_MAPPING_PATH)
        print(f"   精确映射 {len(income_rules.exact)} 条 / 关键词规则 {len(income_rules.keyword)} 条")

    # ── 预先分类（增强功能与报表共用，避免重复计算）──────────────────────────
    expense_items: list = []
    income_items:  list = []
    expense_edata: list = []
    income_edata:  list = []

    if not args.income_only:
        expense_items = classify_expense_records(records, rules, year)
        if enhance:
            expense_edata = _to_enhance_data(expense_items, "debit", "fee_type")

    if not args.expense_only:
        income_items = classify_income_records(records, income_rules, year)
        if enhance:
            income_edata = _to_enhance_data(income_items, "credit", "income_type")

    # ── 创建本次运行输出目录 ──────────────────────────────────────────────────
    run_dir = next_run_dir(args.output)
    print(f"\n📁 本次输出目录：{run_dir.name}/")

    # ─────────────────────────────────────────────────────────────────────────
    # 生成支出报表
    # ─────────────────────────────────────────────────────────────────────────
    if not args.income_only:
        print(f"\n⚙️  生成 {year} 年支出统计报表……")
        wb_expense = build_annual_workbook(records, rules, year, source_count=source_count)
        build_balance_sheet_monthly(wb_expense, records, year)

        if enhance:
            print("   └ 增强：AutoFilter + 冻结行 + 完整度状态列……")
            apply_autofilter_and_freeze(wb_expense, ("明细",))
            add_balance_status_column(wb_expense)

        # 嵌入未匹配修正 Sheet（_待完善 时才有内容）
        unmatched_cnt = sum(1 for i in expense_items if is_unmatched(i))
        embed_expense_unmatched_sheet(wb_expense, expense_items)

        expense_total  = sum((i.record.debit for i in expense_items), Decimal("0"))
        intragroup_amt = sum((i.record.debit for i in expense_items if is_intragroup(i)), Decimal("0"))
        expense_status = "终稿" if unmatched_cnt == 0 else "待完善"

        expense_path = save_expense_workbook_v2(wb_expense, run_dir, year, expense_status)

        print(f"✅ 支出报表：{expense_path.name}")
        print(f"   流水 {len(expense_items)} 条 / 合计 {expense_total:,.2f} 元")
        print(f"   集团内往来 {intragroup_amt:,.2f} 元 / 净支出 {expense_total - intragroup_amt:,.2f} 元")
        if unmatched_cnt > 0:
            print(f"   ⚠️  未完整匹配 {unmatched_cnt} 条 → 填写报表中黄色列后运行 修正补录.py")
        else:
            print(f"   ✨ 所有记录完整匹配 → 已标注为 [终稿]")

    # ─────────────────────────────────────────────────────────────────────────
    # 生成收入报表
    # ─────────────────────────────────────────────────────────────────────────
    if not args.expense_only:
        print(f"\n⚙️  生成 {year} 年收入统计报表……")
        wb_income = build_annual_income_workbook(
            records, income_rules, year,
            source_count=source_count, input_dir=args.input,
        )

        comp_meta = None
        sp_map: dict = {}

        if enhance:
            if not args.income_only and expense_edata:
                print("   └ 增强：收支综合对比 Sheet……")
                comp_meta = build_comparison_sheet(
                    wb_income, income_edata, expense_edata, year
                )
            print("   └ 增强：AutoFilter + 冻结行 + 完整度状态列……")
            apply_autofilter_and_freeze(wb_income, ("明细",))
            add_balance_status_column(wb_income)
            sp_map = prepare_sparkline_specs(wb_income, comp_meta)

        # 嵌入未匹配修正 Sheet
        income_unm_cnt = sum(1 for i in income_items if is_income_unmatched(i))
        embed_income_unmatched_sheet(wb_income, income_items)

        income_total  = sum((i.record.credit for i in income_items), Decimal("0"))
        income_intra  = sum((i.record.credit for i in income_items if is_income_intragroup(i)), Decimal("0"))
        income_status = "终稿" if income_unm_cnt == 0 else "待完善"

        income_path = save_income_workbook_v2(wb_income, run_dir, year, income_status)

        if enhance and sp_map:
            print("   └ 增强：注入 Sparkline 迷你图……")
            inject_sparklines(income_path, sp_map)

        print(f"✅ 收入报表：{income_path.name}")
        print(f"   流水 {len(income_items)} 条 / 合计 {income_total:,.2f} 元")
        print(f"   集团内往来 {income_intra:,.2f} 元 / 净收入 {income_total - income_intra:,.2f} 元")
        if income_unm_cnt > 0:
            print(f"   ⚠️  未完整匹配 {income_unm_cnt} 条 → 填写报表中黄色列后运行 修正补录.py")
        else:
            print(f"   ✨ 所有记录完整匹配 → 已标注为 [终稿]")

    # ── 汇总提示 ──────────────────────────────────────────────────────────────
    total_unmatched = (
        (sum(1 for i in expense_items if is_unmatched(i)) if not args.income_only else 0) +
        (sum(1 for i in income_items if is_income_unmatched(i)) if not args.expense_only else 0)
    )
    if total_unmatched > 0:
        print(f"\n💡 下一步：在 _待完善 报表的黄色列填写修正类型，然后运行：")
        print(f"          python src/修正补录.py --input <待完善报表路径>")
    print(f"\n🎉 完成！输出目录：output/{run_dir.name}/")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
