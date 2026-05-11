#!/usr/bin/env python3
"""
修正补录.py — 银行流水报表系统 v2  入口二
==========================================

功能
----
读取财务人员在 _待完善 报表中填写的修正内容，
自动将修正规则写入 rules/规则库.xlsx，然后重新生成报表。

支持同时处理支出和收入两份报表（可分别提供，也可只提供其中一份）。

工作流
------
  1. 运行 生成报表.py，产生 output/YYYYMMDD_NNN/ 目录
  2. 打开其中的 _待完善 报表，找到标签页"★支出未匹配（可补规则）"
     或"★收入未匹配（可补规则）"
  3. 在黄色列填写正确的费用类型/收入类型/承担部门
  4. 保存并关闭 Excel 文件
  5. 运行本程序（自动检测或手动指定报表路径）

用法示例
--------
  # 自动从最新 output/ 子目录找待完善报表（最常用）
  python src/修正补录.py

  # 手动指定一份报表
  python src/修正补录.py --input output/20260510_001/2026年银行【支出】全年统计_待完善.xlsx

  # 同时指定两份（支出 + 收入）
  python src/修正补录.py \\
      --input output/20260510_001/2026年银行【支出】全年统计_待完善.xlsx \\
              output/20260510_001/2026年银行【收入】全年统计_待完善.xlsx

  # 只更新规则库，不重新生成报表
  python src/修正补录.py --no-rerun

  # 预览将写入的规则，不实际修改
  python src/修正补录.py --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _核心库 import (
    DEFAULT_MAPPING_PATH,
    DEFAULT_OUTPUT_DIR,
    append_expense_rules,
    append_income_rules,
    read_expense_corrections,
    read_income_corrections,
)


# ─────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="修正补录.py：读取已填写修正的报表，更新规则库，重新生成报表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", type=Path, nargs="+", default=None, metavar="XLSX",
        help="待完善报表路径，可同时指定 1-2 份（支出 + 收入）；"
             "不指定时自动从 output/ 最新子目录寻找",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"output 目录（默认：{DEFAULT_OUTPUT_DIR.name}/）",
    )
    parser.add_argument(
        "--rules", type=Path, default=DEFAULT_MAPPING_PATH,
        help=f"规则库路径（默认：{DEFAULT_MAPPING_PATH}）",
    )
    parser.add_argument(
        "--no-rerun", action="store_true",
        help="只更新规则库，不重新生成报表",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预览将写入的规则，不实际修改任何文件",
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
def _auto_find_pending_files(output_dir: Path) -> list[Path]:
    """
    从 output/ 最新子目录（YYYYMMDD_NNN/）中自动找 _待完善.xlsx 文件。
    优先最近修改的子目录。
    """
    subdirs = sorted(
        (p for p in output_dir.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for subdir in subdirs:
        pending = sorted(subdir.glob("*_待完善.xlsx"))
        if pending:
            return pending
    return []


# ─────────────────────────────────────────────────────────────────────────────
def _detect_type(path: Path) -> str:
    """根据文件名判断报表类型：'expense'（支出）或 'income'（收入）。"""
    name = path.name
    if "【支出】" in name:
        return "expense"
    if "【收入】" in name:
        return "income"
    # 无法判断时，尝试读两类 Sheet
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()

    # ── 确定待处理文件列表 ────────────────────────────────────────────────────
    if args.input:
        pending_files = list(args.input)
        for p in pending_files:
            if not p.exists():
                raise SystemExit(f"❌ 文件不存在：{p}")
    else:
        print(f"🔍 自动检测最新 _待完善 报表……")
        pending_files = _auto_find_pending_files(args.output)
        if not pending_files:
            raise SystemExit(
                f"❌ 在 {args.output} 中未找到 _待完善.xlsx 文件。\n"
                f"   请先运行 生成报表.py，或用 --input 手动指定文件路径。"
            )

    print(f"\n📄 待处理文件（共 {len(pending_files)} 份）：")
    for p in pending_files:
        print(f"   • {p.name}")

    # ── 读取修正记录 ──────────────────────────────────────────────────────────
    all_expense_corrections: list[dict] = []
    all_income_corrections:  list[dict] = []

    for path in pending_files:
        ftype = _detect_type(path)

        if ftype == "expense":
            corrections = read_expense_corrections(path)
            print(f"\n📊 {path.name}（支出）：读取到 {len(corrections)} 条修正记录")
            all_expense_corrections.extend(corrections)

        elif ftype == "income":
            corrections = read_income_corrections(path)
            print(f"\n📊 {path.name}（收入）：读取到 {len(corrections)} 条修正记录")
            all_income_corrections.extend(corrections)

        else:
            # 文件名无法判断时，同时尝试两类
            exp_c = read_expense_corrections(path)
            inc_c = read_income_corrections(path)
            if exp_c:
                print(f"\n📊 {path.name}（支出修正）：读取到 {len(exp_c)} 条")
                all_expense_corrections.extend(exp_c)
            if inc_c:
                print(f"\n📊 {path.name}（收入修正）：读取到 {len(inc_c)} 条")
                all_income_corrections.extend(inc_c)
            if not exp_c and not inc_c:
                print(f"\n⚠️  {path.name}：未找到修正 Sheet，请确认已填写黄色列并保存")

    total_corrections = len(all_expense_corrections) + len(all_income_corrections)
    if total_corrections == 0:
        print("\n⚠️  未读取到任何有效修正记录。")
        print("   请确认：")
        print('   1. 已在黄色列填写【修正费用类型】/【修正收入类型】')
        print("   2. Excel 文件已保存并关闭（避免文件锁定）")
        if not args.no_rerun:
            print("\n📋 无修正内容，跳过规则更新和报表重新生成。")
        return

    # ── 预览模式 ──────────────────────────────────────────────────────────────
    if args.dry_run:
        print(f"\n[预览模式] 将写入以下规则（共 {total_corrections} 条）：")
        if all_expense_corrections:
            print(f"\n  支出精确映射（{len(all_expense_corrections)} 条）：")
            for c in all_expense_corrections[:10]:
                print(f"    {c['mapping_key'][:40]:<40} → {c['fee']} / {c.get('department','')}")
            if len(all_expense_corrections) > 10:
                print(f"    … 另有 {len(all_expense_corrections) - 10} 条")
        if all_income_corrections:
            print(f"\n  收入精确映射（{len(all_income_corrections)} 条）：")
            for c in all_income_corrections[:10]:
                print(f"    {c['mapping_key'][:40]:<40} → {c['income_type']}")
            if len(all_income_corrections) > 10:
                print(f"    … 另有 {len(all_income_corrections) - 10} 条")
        print("\n[预览模式] 不实际写入文件，如需执行请去掉 --dry-run 参数")
        return

    # ── 写入规则库 ────────────────────────────────────────────────────────────
    print(f"\n✏️  更新规则库：{args.rules}")

    if all_expense_corrections:
        added, updated = append_expense_rules(all_expense_corrections, args.rules)
        print(f"   支出精确映射：新增 {added} 条 / 更新 {updated} 条")

    if all_income_corrections:
        added, updated = append_income_rules(all_income_corrections, args.rules)
        print(f"   收入精确映射：新增 {added} 条 / 更新 {updated} 条")

    print(f"✅ 规则库已保存：{args.rules}")

    # ── 重新生成报表 ──────────────────────────────────────────────────────────
    if args.no_rerun:
        print("\n📋 已跳过报表重新生成（--no-rerun）")
        print("   如需重新生成，请运行：python src/生成报表.py")
        return

    print(f"\n⚙️  重新生成报表……")
    script = Path(__file__).resolve().parent / "生成报表.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\n❌ 报表生成失败（退出码 {result.returncode}）")
        print(f"   请检查上方错误信息，或手动运行：python src/生成报表.py")
    else:
        print(f"\n🎉 修正补录完成！规则已更新，最新报表已生成。")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
