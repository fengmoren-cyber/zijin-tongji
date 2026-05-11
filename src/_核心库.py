#!/usr/bin/env python3
"""
_核心库.py — 银行流水报表系统内部核心库（v2）
================================================
合并自 v1：核心处理库 + 收入匹配引擎 + 报表增强

⚠️  此文件为内部实现，请勿直接运行。
    用户入口：生成报表.py / 修正补录.py
"""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════════════
# §1  收入匹配引擎（原 收入匹配引擎.py）
# ══════════════════════════════════════════════════════════════════════

"""
收入分类匹配引擎 v2
规则逻辑：银行账户优先规则 → 摘要关键词规则 → 往来款兜底
"""

# ─── 集团内部公司名单 ─────────────────────────────────────────────────────────
INTERNAL_COMPANIES = [
    '深圳市玉玄道科技有限公司',
    '深圳市玉玄道传统文化发展有限公司',
    '深圳市玉玄道健康管理有限公司',
    '深圳市玉玄道医疗管理集团有限公司',
    '深圳市利从电子商务有限公司',
    '深圳市生众销售有限公司',
    '深圳市玉玄道建筑安装工程有限公司',
    '吉林省普济健康管理咨询中心',
    '深圳市玉玄道云科技有限公司',
    '玉娇美',
    '玉玄道（杭州）健康管理有限公司',
    '玉玄道(杭州)健康管理有限公司',
    '深圳市玉玄道致远健康服务有限公司',
    '深圳玉玄道中医诊所',
    '湖南玉玄道电子商务有限公司',   # 注意：此公司转账到健康管理光大是APP货款，特殊处理
]

# 往来款对方名称关键词（覆盖上方列表，确保摘要匹配）
INTERNAL_KEYWORDS = [
    '玉玄道', '利从电子商务', '生众销售', '普济健康',
    '深圳市玉玄道', '传统文化发展',
]

COMPANY_KEYWORDS = [
    '有限公司', '股份有限公司', '合伙', '基金', '银行', '中心', '集团',
    '商务', '支付', '服务', '科技', '电子', '保险', '管理', '发展',
    '建设', '投资', '控股', '企业', '商行', '信托', '证券', '诊所',
]

ZHUDAN_AMOUNTS = {3333, 6666, 9999, 3333*2, 6666*2, 9999*2,
                  3333*3, 6666*3, 9999*3, 3333*4, 6666*4, 9999*4,
                  3333*5, 6666*5, 9999*5, 29997, 19998, 26664}  # 已知倍数

def is_individual(name: str) -> bool:
    if not name or not name.strip():
        return False
    return not any(kw in name for kw in COMPANY_KEYWORDS)

def is_internal(name: str) -> bool:
    if not name:
        return False
    return any(co in name for co in INTERNAL_COMPANIES) or any(kw in name for kw in INTERNAL_KEYWORDS)

def _ret(inc_type, src='', rule=''):
    return {'income_type': inc_type, 'source_company': src, 'rule_id': rule}

def match_income(counterparty, summary, amount, bank, company):
    cp  = str(counterparty or '').strip()
    sm  = str(summary or '').strip()
    amt = float(amount) if amount else 0.0
    bk  = str(bank or '').strip()

    # ── 全局最高优先：摘要明确含"租金"/"房租"（即使对方是内部公司）──────────
    if '租金' in sm or '房租' in sm:
        return _ret('租金', rule='R_RENT')

    # ── 全局：利息收入（结息/收息/利息）─────────────────────────────────────
    if ('结息' in sm or '收息' in sm or '批量结息' in sm
            or ('利息' in sm and not is_internal(cp))):
        return _ret('利息收入', rule='R_INT')

    # ── 全局：税务退库（电子退库）────────────────────────────────────────────
    if '电子退库' in sm or '税款退库' in sm:
        return _ret('税务退库', rule='R_TAX')

    # ── 全局：政府补贴（高新技术/政府/补贴/专项）─────────────────────────────
    if any(kw in sm for kw in ['高新技术企业', '政府补贴', '专项资金', '科技型中小企业']):
        return _ret('政府补贴', rule='R_GOV')

    # ── 全局：摘要含"保证金"（不是美团保证金，那个在利从单独处理）─────────
    if '保证金' in sm and '利从' not in bk and '美团' not in sm:
        return _ret('保证金', rule='R_BOND')

    # ── 全局：质保金 ──────────────────────────────────────────────────────────
    if '质保金' in sm:
        return _ret('保证金', rule='R_BOND2')

    # ─────────────────────────────────────────────────────────────────────────
    # 按收款银行账户分支（银行级规则 > 全局往来款）
    # ─────────────────────────────────────────────────────────────────────────

    # ── 传统文化光大基本户 ──────────────────────────────────────────────────
    if '传统文化光大' in bk:
        if '上海富友支付服务股份有限公司' in cp:
            return _ret('伤寒论收款', '培训部', 'R03')
        # 驻颜丹收款：金额为3333/6666/9999或其倍数（对方可以是个人或集团内公司代转）
        if amt in ZHUDAN_AMOUNTS:
            return _ret('驻颜丹收款', '培训部', 'R04')
        # 退款类（汇款退款/网银退款）
        if '退款' in sm:
            return _ret('退款收回', rule='R_REFUND_CEB_TC')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 传统文化招行一般户 ──────────────────────────────────────────────────
    if '传统文化招行' in bk:
        if '代发余额退款' in sm:
            return _ret('驻颜丹退款失败', rule='R02')
        # 他行户口交易失败退款 + 金额1111 → 驻颜丹退款失败
        if '他行户口交易失败退款' in sm or '驻颜丹退款' in sm:
            return _ret('驻颜丹退款失败', rule='R02b')
        if is_internal(cp) or '往来款' in sm:
            return _ret('往来款', rule='R01')
        # 个人汇款兜底 → 驻颜丹收款（传统文化招行收到个人转账大概率是产品款）
        if is_individual(cp):
            return _ret('驻颜丹收款', '培训部', 'R04b')
        return _ret('未匹配', rule='NONE')

    # ── 健康管理光大 ────────────────────────────────────────────────────────
    if bk == '健康管理光大' or '健康管理光大' in bk:
        if '银联商务支付股份有限公司' in cp:
            return _ret('扫码货款', rule='R05')
        # 湖南玉玄道电子商务 → APP货款（供应链提现，不是往来款）
        if '湖南玉玄道电子商务有限公司' in cp:
            return _ret('APP货款', rule='R_APP')
        # 利从购买产品 → 货款（虽然是内部公司，但购买产品的外部行为）
        if '利从电子商务有限公司' in cp and '购买产品' in sm:
            return _ret('货款', '深圳市利从电子商务有限公司', 'R06')
        # 其他内部公司 → 往来款
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        if is_individual(cp):
            return _ret('货款', rule='R07')
        return _ret('未匹配', rule='NONE')

    # ── 健康管理农行基本户 ──────────────────────────────────────────────────
    if '健康管理农行基本户' in bk:
        if '还借款' in sm:
            return _ret('还借款', rule='R08')
        if '报销' in sm or '退款' in sm:
            return _ret('退款收回', rule='R_REFUND_ABC')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 健康管理农行华润城支行 ──────────────────────────────────────────────
    if '健康管理农行华润城' in bk or '华润城' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        if is_individual(cp):
            return _ret('广宣物料收款', rule='R09')
        return _ret('未匹配', rule='NONE')

    # ── 健康科技农行基本户 ──────────────────────────────────────────────────
    if '健康科技农行' in bk:
        if is_individual(cp) and amt == 3800:
            return _ret('软件服务收款', rule='R10')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 健康招商（健康管理招商）─────────────────────────────────────────────
    if bk == '健康招商':
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 利从招行基本户 ──────────────────────────────────────────────────────
    if '利从招行' in bk:
        if '北京钱袋宝支付技术有限公司' in cp:
            return _ret('有赞货款', rule='R11')
        if '北京有赞支付有限公司' in cp:
            return _ret('有赞货款', rule='R11b')
        if '江苏银行平台交易资金户' in cp and '抖音生活服务商家提现' in sm:
            return _ret('抖音团购结算', rule='R12')
        # 美团运营费用 → 美团货款
        if '美团运营费用' in sm or '美团' in cp:
            return _ret('美团货款', rule='R_MEITUAN')
        if '代发余额退款' in sm:
            return _ret('代发团购退款', rule='R13')
        if '支付平台退票' in sm or '他行户口交易失败退款' in sm:
            return _ret('交易失败退款', rule='R14')
        if '美团保证金' in sm:
            return _ret('美团保证金', rule='R15')
        if '保证金' in sm:
            return _ret('保证金', rule='R_BOND3')
        # STAR 单号 → 有赞/平台货款
        if sm.startswith('STAR') or 'STAR2026' in sm:
            return _ret('有赞货款', rule='R11c')
        # 服务费
        if '服务费' in sm:
            return _ret('服务费收入', rule='R_SVC')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 医疗集团光大 ────────────────────────────────────────────────────────
    if '医疗集团光大' in bk:
        if '银联商务支付股份有限公司' in cp:
            return _ret('医馆提现', rule='R16')
        if '湖南玉玄道电子商务有限公司' in cp:
            return _ret('医馆提现', rule='R17')
        # 驻颜丹收款：个人汇款且金额=6666且摘要含驻颜丹
        if is_individual(cp) and amt == 6666 and '驻颜丹' in sm:
            return _ret('驻颜丹收款', rule='R18')
        # 培训费：个人+金额4800+摘要含神炙馆/培训
        if is_individual(cp) and amt == 4800:
            return _ret('培训费', rule='R_TRAIN')
        # 摘要含还款/冲销 → 还款
        if '还款' in sm or '冲销' in sm:
            return _ret('还款', rule='R_REPAY_CEB')
        # 摘要含神灸馆/康养馆且对方是个人 → 医馆提现
        if is_individual(cp) and any(kw in sm for kw in ['神灸馆', '康养馆', '神炙馆']):
            return _ret('医馆提现', rule='R17b')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        # 个人对方兜底 → 还款
        if is_individual(cp):
            return _ret('还款', rule='R_REPAY_CEB2')
        return _ret('未匹配', rule='NONE')

    # ── 医疗集团招行基本户 ──────────────────────────────────────────────────
    if '医疗集团招行' in bk:
        if '通联支付网络服务股份有限公司' in cp and amt <= 1:
            return _ret('测试款', rule='R19')
        if '支付平台退票' in sm:
            return _ret('交易失败退款', rule='R20')
        if '退款' in sm or '还款' in sm or '未退款' in sm:
            return _ret('还款', rule='R_REPAY')
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        if is_individual(cp):
            return _ret('还款', rule='R_REPAY2')
        return _ret('未匹配', rule='NONE')

    # ── 南山光大基本户 ──────────────────────────────────────────────────────
    if '南山光大' in bk:
        if amt == 4800:
            return _ret('培训费', rule='R21')
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 建筑招行基本户 ──────────────────────────────────────────────────────
    if '建筑招行' in bk:
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        if is_individual(cp):
            return _ret('建筑公司装修物料、设计费', rule='R22')
        return _ret('未匹配', rule='NONE')

    # ── 平安银行基本户（玉娇美化妆品）──────────────────────────────────────
    if '平安银行' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 生众招行基本户 ──────────────────────────────────────────────────────
    if '生众招行' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        if is_individual(cp):
            return _ret('货款', rule='R_SHENGZHONG')
        return _ret('未匹配', rule='NONE')

    # ── 科技招行基本户 ──────────────────────────────────────────────────────
    if '科技招行基本户' in bk:
        if '北京有赞支付有限公司-备付金账户' in cp or '北京有赞' in cp:
            return _ret('有赞货款', rule='R23')
        if '退款' in sm or '案件退款' in sm:
            return _ret('退款收回', rule='R_REFUND_CMB_KJ')
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 科技招行一般户 ──────────────────────────────────────────────────────
    if '科技招行一般户' in bk:
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 科技光大一般户 ──────────────────────────────────────────────────────
    if '科技光大' in bk:
        if '深圳市医疗保险基金管理中心' in cp and '生育津贴' in sm:
            return _ret('生育津贴', rule='R24')
        if '退款' in sm or '网银跨行汇款退款' in sm:
            return _ret('退款收回', rule='R_REFUND_CEB_KJ')
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        # 个人/公司对方且摘要无明确指向 → 往来款兜底
        if is_individual(cp):
            return _ret('往来款', rule='R01b')
        return _ret('未匹配', rule='NONE')

    # ── 云科技招行 ──────────────────────────────────────────────────────────
    if '云科技招行' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 致远中国银行 ────────────────────────────────────────────────────────
    if '致远' in bk:
        if is_internal(cp) or '往来' in sm:
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 鸿明银行 ────────────────────────────────────────────────────────────
    if '鸿明' in bk:
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 玉娇美健康 ──────────────────────────────────────────────────────────
    if '玉娇美健康' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 普济招商 ────────────────────────────────────────────────────────────
    if '普济招商' in bk:
        if is_internal(cp):
            return _ret('往来款', rule='R01')
        return _ret('未匹配', rule='NONE')

    # ── 健康招商 ────────────────────────────────────────────────────────────
    if '健康招商' in bk:
        if is_internal(cp):
            return _ret('往来款', '财务部', 'R01')
        return _ret('未匹配', rule='NONE')

    # ── 全局兜底 ────────────────────────────────────────────────────────────
    if is_internal(cp) or '往来款' in sm or '往来' in sm:
        return _ret('往来款', rule='R01')

    return _ret('未匹配', rule='NONE')


# ═══════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════
# §2  核心处理库（原 核心处理库.py）
# ══════════════════════════════════════════════════════════════════════


import datetime as dt
import io
import zipfile
from collections import defaultdict
import re
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable, Sequence

import openpyxl
try:
    import xlrd
except ImportError:
    xlrd = None  # type: ignore  # 仅读 .xls 格式时需要；.xlsx 不受影响
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ── 收入匹配引擎（已内联到 §1，始终可用）───────────────────────────────────
_INCOME_MATCHER_AVAILABLE = True
_match_income_engine      = match_income  # §1 中的 match_income() 函数

# ── 目录结构 ────────────────────────────────────────────────────────────────
PROJECT_ROOT      = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR  = PROJECT_ROOT / "input"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
RULES_DIR          = PROJECT_ROOT / "rules"
# 规则总库（同时包含支出规则和收入规则）
DEFAULT_MAPPING_PATH        = RULES_DIR / "规则库.xlsx"
DEFAULT_INCOME_MAPPING_PATH = RULES_DIR / "规则库.xlsx"

# ── 企业财务报表配色规范（参照上市公司财务报告视觉标准）──────────────────────
_C_NAVY     = "1F3864"   # 深海蓝：主标题行背景 / 合计文字
_C_BLUE     = "2E75B6"   # 中蓝：列表头背景
_C_LBLUE    = "BDD7EE"   # 浅蓝：合计行背景
_C_GREEN    = "E2EFDA"   # 浅绿：净支出行背景
_C_GRAY     = "F2F2F2"   # 浅灰：集团内往来款行背景
_C_STRIPE   = "EEF5FB"   # 条纹浅蓝：奇数数据行背景
_C_WHITE    = "FFFFFF"
_C_TXT_GRAY = "595959"   # 灰色文字：集团内往来款行

_THIN  = Side(style="thin",   color="BFBFBF")
_MED   = Side(style="medium", color="2E75B6")
_BORDER_THIN   = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_BORDER_HEADER = Border(left=_MED,  right=_MED,  top=_MED,  bottom=_MED)

_NUM_FMT = "#,##0.00"   # 统一数字格式：千分位+两位小数

OUTPUT_COLUMNS = [
    "公司名称",
    "交易日期",
    "借方发生额",
    "对方名称",
    "摘要",
    "银行名称",
    "费用类型",
    "承担部门",
]

EXPENSE_COLUMNS = [
    "物业水电",
    "工资福利",
    "社保",
    "公积金",
    "个税",
    "税费缴纳",
    "招待费",
    "餐费",
    "差旅费",
    "物流费",
    "交通费",
    "财务费用",
    "通讯费",
    "服务费",
    "还贷款",
]

OTHER_EXPENSE_COLUMNS = [
    "分子公司借款",
    "医馆借款",
    "抖音团购结算",
    "退款支出",
    "采购支出",
    "装修支出",
]

DEFAULT_KEYWORD_RULES = [
    # 高优先级精确规则（须置于通用服务费规则之前，避免被错误归类为手续费）
    # 来源：2026-05 核对批次
    ("深圳天磊联信|营业性演出许可证", "资质服务费", "董办"),   # 演出许可证资质办理→董办
    ("中科汇聚", "服务费", "研发部"),                            # 检测/企标/资质服务→研发部
    ("广州纯蓁", "咨询服务费", "研发部"),                        # 生物科技咨询→研发部
    ("手续费|服务费|电子汇划费|短信通服务费|对公中间业务收入|付.*手续费", "手续费", "资金管理部"),
    ("个人所得税|个税", "个税", ""),
    ("企业所得税|增值税|教育费附加|城市维护建设税|地方教育附加|税费|银税通|实时缴税|税款|税单", "税费", ""),
    ("养老保险|医疗保险|工伤保险|生育保险|失业保险|社会保险|社保", "社保", ""),
    ("住房公积金|公积金", "公积金", ""),
    ("工资|奖金|代发工资|代发", "工资", ""),
    ("货款退还|退款|退费|驻颜丹退款|批量代发付费", "退款", ""),
    ("差旅费|机票|酒店|住宿|车票|高铁|交通费|加油费|ETC", "差旅费", ""),
    ("餐费|招待费", "招待费", "行政部"),
    ("快递|物流|顺丰|京东物流|运费", "物流快递费", "行政部"),
    ("电信|电话费|通讯费|宽带|网络|手机费", "网络通讯费", "行政部"),
    ("物业|水电|电费|水费|管理费|租金|保洁", "物业费", "行政部"),
    ("办公用品|文具|打印机|维修费|办公费|印刷|笔记本电脑|移动平板|工服", "办公费", "行政部"),
    ("生日会|福利|礼品|下午茶|团建|零食", "福利费", "行政部"),
    ("红包|礼金|团队奖|开工红包|开年红包", "福利费", "行政部"),
    ("商标|软著|专利|检测咨询|企业微信年度认证|公众号认证|特许经营年报|律师费|咨询款|腾讯云|云码|充值|平台维护费|账户维护", "服务费", "运营部"),
    ("推广|巨量引擎|广宣|广告|物料", "广告宣传费", "运营部"),
    ("抖音|团购结算", "抖音团购结算", "运营部"),
    ("往来款|借款|分公司", "分子公司借款", ""),
    ("还贷款|贷款|还款", "还贷款", ""),
    ("装修|门头|发光字|玻璃门|腻子|地砖|壁纸|橱柜|家具|工程|灯具|劳务结算", "装修支出", ""),
    ("货款|采购|付款|购买产品|产品|包装|暖贴|护垫|打样费|原料|结算货款|经络梳|枕|甜杏仁油|荷荷巴油|开水器|模具|POLO衫", "采购支出", ""),
    ("捐赠", "捐赠支出", ""),
]

# ── 收入分类默认关键词规则（按优先级排列）────────────────────────────────────
DEFAULT_INCOME_KEYWORD_RULES: list[tuple[str, str, str]] = [
    # (正则, 收入类型, 来源公司类别)
    ("抖音|抖音来客|巨量引擎|抖音团购结算",                     "平台结算（抖音）",    "运营部"),
    ("美团|美团团购结算",                                       "平台结算（美团）",    "运营部"),
    ("退款|退货款|货款退还|退投资款",                           "退款收回",            "市场部"),
    ("利息|存款利息|计息",                                      "利息收入",            "财务部"),
    ("加盟费|特许经营|品牌使用费",                              "加盟费收入",          "市场部"),
    ("借款|往来款",                                             "借款收入",            "财务部"),
    ("保证金",                                                  "保证金收入",          "财务部"),
    ("销售|货款|业务收入|服务费|技术服务|充值|采购货款",         "业务收入",            ""),
]

# 收入类型标准化映射
INCOME_TYPE_NORMALIZATION: dict[str, str] = {
    "平台结算":   "平台结算（抖音）",
    "团购结算":   "平台结算（抖音）",
    "退款":       "退款收回",
    "借款":       "借款收入",
    "利息":       "利息收入",
}

# 集团内往来款：收入侧属于此类型的不计入净外部收入
INTRAGROUP_INCOME_TYPES: set[str] = {"借款收入", "往来款"}


FEE_TYPE_NORMALIZATION = {
    "办公费用": "办公",
    "办公用品": "办公",
    "办公费": "办公",
    "物流快递费": "物流费",
    "网络通讯费": "通讯费",
    "物业费": "物业水电",
    "税费": "税费缴纳",
    "团购结算": "抖音团购结算",
    "装修劳务支出": "装修支出",
}

DEPARTMENT_NORMALIZATION = {
    "市场": "市场部",
    "建筑": "建筑公司",
}

SUMMARY_FEE_COLUMN = {
    "物业水电": "物业水电",
    "工资": "工资福利",
    "工资福利": "工资福利",
    "福利费": "工资福利",
    "社保": "社保",
    "公积金": "公积金",
    "个税": "个税",
    "税费": "税费缴纳",
    "税费缴纳": "税费缴纳",
    "招待费": "招待费",
    "餐费": "餐费",
    "差旅费": "差旅费",
    "物流费": "物流费",
    "物流快递费": "物流费",
    "交通费": "交通费",
    "手续费": "财务费用",
    "财务费用": "财务费用",
    "通讯费": "通讯费",
    "网络通讯费": "通讯费",
    "服务费": "服务费",
    "资质服务费": "服务费",
    "咨询服务费": "服务费",
    "办公": "服务费",
    "广告宣传费": "服务费",
    "还贷款": "还贷款",
    "分子公司借款": "分子公司借款",
    "医馆借款": "医馆借款",
    "抖音团购结算": "抖音团购结算",
    "美团团购结算": "抖音团购结算",
    "团购结算": "抖音团购结算",
    "退款": "退款支出",
    "退款支出": "退款支出",
    "采购支出": "采购支出",
    "装修支出": "装修支出",
}

FEE_DEFAULT_DEPARTMENT = {
    "工资": "人力资源部",
    "工资福利": "人力资源部",
    "福利费": "人力资源部",
    "社保": "人力资源部",
    "公积金": "人力资源部",
    "个税": "人力资源部",
    "税费": "财务部",
    "税费缴纳": "财务部",
    "分子公司借款": "财务部",
    "医馆借款": "财务部",
    "还贷款": "财务部",
    "采购支出": "采购部",
    "装修支出": "行政部",
    "退款": "按业务公司承担",
    "退款支出": "按业务公司承担",
    "抖音团购结算": "运营部",
    "美团团购结算": "运营部",
    "捐赠支出": "董办",
    "资质服务费": "董办",
    "咨询服务费": "研发部",
}

SUMMARY_COMPANIES = [
    "传统文化",
    "创业投资",
    "健康管理",
    "南山分公司",
    "医疗集团",
    "科技公司",
    "健康科技",
    "深圳利从",
    "生众",
    "云科技",
    "致远",
    "建筑安装",
    "吉林普济",
    "海南鸿明",
    "玉娇美健康",
    "玉娇美化妆品",
]


@dataclass(frozen=True)
class BankRecord:
    company: str
    trade_date: dt.date
    debit: Decimal
    credit: Decimal
    counterparty: str
    summary: str
    bank_name: str
    source_file: str
    source_row: int
    unique_id: str = ""
    balance: Decimal = Decimal("0")   # 账户余额（来自流水文件，Decimal("0") 表示未读取）


@dataclass(frozen=True)
class ClassificationRuleSet:
    exact: dict[str, tuple[str, str]]
    keyword: list[tuple[str, str, str]]


@dataclass(frozen=True)
class ClassifiedRecord:
    record: BankRecord
    fee: str
    department: str
    match_note: str


@dataclass(frozen=True)
class IncomeClassifiedRecord:
    """收入分类记录：贷方（credit > 0）流水 + 收入类型 + 来源公司。"""
    record: BankRecord
    income_type: str      # 收入类型（如 业务收入、平台结算（抖音））
    source_company: str   # 来源公司/付款方摘要
    match_note: str


def clean_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\t", "").strip()


def compact_text(value: object) -> str:
    return re.sub(r"\s+", "", clean_text(value))


def normalize_fee(value: object) -> str:
    text = clean_text(value)
    return FEE_TYPE_NORMALIZATION.get(text, text)


def normalize_department(value: object) -> str:
    text = clean_text(value)
    return DEPARTMENT_NORMALIZATION.get(text, text)


def to_decimal(value: object) -> Decimal:
    text = clean_text(value).replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def quantize_wan(value: Decimal) -> Decimal:
    return (value / Decimal("10000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_float(value: Decimal) -> float:
    return float(value)


def exact_key_from_values(counterparty: object, summary: object, bank_name: object) -> str:
    return "|".join([compact_text(counterparty), compact_text(summary), compact_text(bank_name)])


def exact_key_from_record(rec: BankRecord) -> str:
    return exact_key_from_values(rec.counterparty, rec.summary, rec.bank_name)


def _find_header_row(
    ws, required_cols: set[str], max_scan: int = 5
) -> tuple[int, list[str]] | None:
    """扫描前 max_scan 行，找到包含所有必需列名的那一行作为 header 行。
    返回 (行号1-based, headers列表)，未找到返回 None。
    兼容规则库「第1行=标题说明，第2行=列名」和旧格式「第1行=列名」两种结构。
    """
    for row_cells in ws.iter_rows(min_row=1, max_row=max_scan):
        headers = [clean_text(c.value) for c in row_cells]
        if required_cols.issubset(set(headers)):
            return (row_cells[0].row, headers)
    return None


def load_classification_rules(mapping_path: Path | None) -> ClassificationRuleSet:
    exact: dict[str, tuple[str, str]] = {}
    keyword: list[tuple[str, str, str]] = [
        (pattern, normalize_fee(fee), normalize_department(dept))
        for pattern, fee, dept in DEFAULT_KEYWORD_RULES
    ]
    if not mapping_path or not mapping_path.exists():
        return ClassificationRuleSet(exact=exact, keyword=keyword)

    wb = openpyxl.load_workbook(mapping_path, read_only=True, data_only=True)

    # 兼容新版规则库（支出_精确映射）和旧版单文件（精确映射）
    exact_sheet_name = next(
        (n for n in ("支出_精确映射", "精确映射") if n in wb.sheetnames), None
    )
    if exact_sheet_name:
        ws = wb[exact_sheet_name]
        # 规则库第1行为标题说明，第2行才是列名；旧格式第1行即为列名
        header_row = _find_header_row(ws, {"映射键", "费用类型"})
        if header_row:
            h_idx, headers = header_row
            cols = {name: idx for idx, name in enumerate(headers)}
            required = {"映射键", "费用类型", "承担部门"}
            if required.issubset(cols):
                for row in ws.iter_rows(min_row=h_idx + 1, values_only=True):
                    key = clean_text(row[cols["映射键"]]) if cols["映射键"] < len(row) else ""
                    fee = normalize_fee(row[cols["费用类型"]]) if cols["费用类型"] < len(row) else ""
                    dept = normalize_department(row[cols["承担部门"]]) if cols["承担部门"] < len(row) else ""
                    if key and fee and fee != "未匹配" and dept and dept != "未分配":
                        exact[key] = (fee, dept)

    # 兼容新版规则库（支出_关键词规则）和旧版单文件（关键词规则）
    kw_sheet_name = next(
        (n for n in ("支出_关键词规则", "关键词规则") if n in wb.sheetnames), None
    )
    if kw_sheet_name:
        ws = wb[kw_sheet_name]
        header_row = _find_header_row(ws, {"关键词正则", "费用类型"})
        if header_row:
            h_idx, headers = header_row
            cols = {name: idx for idx, name in enumerate(headers)}
            if "关键词正则" in cols and "费用类型" in cols:
                saved_rules: list[tuple[int, str, str, str]] = []
                for order, row in enumerate(ws.iter_rows(min_row=h_idx + 1, values_only=True), start=1):
                    pattern = clean_text(row[cols["关键词正则"]]) if cols["关键词正则"] < len(row) else ""
                    fee = normalize_fee(row[cols["费用类型"]]) if cols["费用类型"] < len(row) else ""
                    dept = normalize_department(row[cols.get("承担部门", -1)]) if cols.get("承担部门", -1) >= 0 and cols.get("承担部门", -1) < len(row) else ""
                    priority = row[cols.get("优先级", -1)] if cols.get("优先级", -1) >= 0 and cols.get("优先级", -1) < len(row) else order
                    try:
                        priority_no = int(priority)
                    except (TypeError, ValueError):
                        priority_no = order
                    if pattern and fee:
                        saved_rules.append((priority_no, pattern, fee, dept))
                if saved_rules:
                    keyword = [(pattern, fee, dept) for _, pattern, fee, dept in sorted(saved_rules)]

    return ClassificationRuleSet(exact=exact, keyword=keyword)


def classify_record(rec: BankRecord, rules: ClassificationRuleSet) -> tuple[str, str]:
    classified = classify_record_detail(rec, rules)
    return classified.fee, classified.department


def classify_record_detail(rec: BankRecord, rules: ClassificationRuleSet) -> ClassifiedRecord:
    key = exact_key_from_record(rec)
    if key in rules.exact:
        fee, dept = rules.exact[key]
        return ClassifiedRecord(rec, fee, dept or default_department(fee), key)

    text = compact_text(rec.counterparty) + compact_text(rec.summary) + compact_text(rec.bank_name)
    for pattern, fee, dept in rules.keyword:
        try:
            if re.search(pattern, text, flags=re.IGNORECASE):
                fee = fee or "未匹配"
                return ClassifiedRecord(rec, fee, dept or default_department(fee), pattern)
        except re.error:
            continue
    return ClassifiedRecord(rec, "未匹配", "未分配", "")


def default_department(fee: str) -> str:
    return FEE_DEFAULT_DEPARTMENT.get(fee, "未分配")


def parse_date(value: object, datemode: int = 0) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        try:
            return xlrd.xldate_as_datetime(float(value), datemode).date()
        except Exception:
            return None

    text = clean_text(value)
    if not text:
        return None
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    text = text.split()[0]
    if re.fullmatch(r"\d{8}", text):
        return dt.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def infer_company(text: str, filename: str = "") -> str:
    haystack = f"{text} {filename}"
    rules = [
        ("南山分公司", "南山分公司"),
        ("传统文化", "传统文化"),
        ("创业投资", "创业投资"),
        ("健康科技", "健康科技"),
        ("健康管理", "健康管理"),
        ("医疗管理集团", "医疗集团"),
        ("医疗集团", "医疗集团"),
        ("玉玄道科技", "科技"),
        ("科技有限公司", "科技"),
        ("利从", "利从"),
        ("生众", "生众"),
        ("云科技", "云科技"),
        ("致远", "致远"),
        ("建筑安装", "建筑公司"),
        ("建筑公司", "建筑公司"),
        ("普济", "普济"),
        ("鸿明", "鸿明"),
        ("玉娇美健康", "玉娇美健康"),
        ("玉娇美化妆品", "玉娇美（化妆品）"),
        ("化妆品", "玉娇美（化妆品）"),
    ]
    for key, company in rules:
        if key in haystack:
            return company
    return Path(filename).stem.split()[0]


def infer_bank(filename: str, account_name: str = "") -> str:
    stem = Path(filename).stem
    compact_stem = compact_text(stem)
    specific = [
        ("传统文化光大", "传统文化光大基本户"),
        ("健康光大", "健康管理光大"),
        ("南山光大", "南山光大基本户"),
        ("医疗光大", "医疗集团光大"),
        ("科技光大", "科技光大一般户"),
        ("健康农行6411", "健康管理农行基本户"),
        ("健康农行6906", "健康管理农行华润城支行"),
        ("健康科技农行", "健康科技农行基本户"),
        ("玉娇美化妆品", "平安银行基本户"),        # 兼容新旧文件名（含/不含"平安"）
        ("玉娇美健康", "玉娇美健康招商"),          # 玉娇美健康招商账户
        ("传统招商", "传统文化招行一般户"),
        ("传统文化招商", "传统文化招行一般户"),
        ("健康招商", "健康招商"),
        ("利从招商", "利从招行基本户"),
        ("医疗招商", "医疗集团招行基本户"),
        ("建筑招商", "建筑招行基本户"),            # 新文件名：建筑招商1-4.xlsx
        ("建筑公司", "建筑招行基本户"),            # 旧文件名兜底
        ("科技招商一般户", "科技招行一般户"),      # 兼容新文件名（一般户10001）
        ("科技招商基本户", "科技招行基本户"),      # 兼容新文件名（基本户10201）
        ("云科技招商", "云科技招行"),
        ("普济招商", "普济招商基本户"),            # 兼容新文件名（去掉"吉林"前缀）
        ("生众招商", "生众招行基本户"),
        ("创投", "创投招行基本户"),                # 创业投资招商账户
    ]
    for key, bank_name in specific:
        if key in compact_stem:
            return bank_name
    if "光大" in stem:
        return f"{infer_company(account_name, filename)}光大"
    if "招商" in stem:
        return f"{infer_company(account_name, filename)}招商"
    if "农行" in stem:
        return f"{infer_company(account_name, filename)}农行"
    if "平安" in stem:
        return f"{infer_company(account_name, filename)}平安"
    if "致远" in stem:
        return "致远中国银行"
    if "鸿明" in stem:
        return "鸿明银行"
    return stem


def summary_company(company: str) -> str:
    mapping = {
        "科技": "科技公司",
        "利从": "深圳利从",
        "建筑公司": "建筑安装",
        "普济": "吉林普济",
        "鸿明": "海南鸿明",
        "玉娇美（化妆品）": "玉娇美化妆品",
    }
    return mapping.get(company, company)


def row_values_xlsx(ws: openpyxl.worksheet.worksheet.Worksheet) -> Iterable[tuple[int, list[object]]]:
    for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        yield idx, list(row)


def find_header(rows: Sequence[tuple[int, list[object]]], required: Sequence[str]) -> tuple[int, dict[str, int]] | None:
    for row_no, row in rows:
        values = [clean_text(v) for v in row]
        if all(item in values for item in required):
            return row_no, {value: idx for idx, value in enumerate(values) if value}
    return None


def parse_xlsx(path: Path) -> list[BankRecord]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(row_values_xlsx(ws))
    header = find_header(rows, ["交易日", "借方金额", "贷方金额"])
    if header:
        return parse_cmb_rows(path, rows, header)
    header = find_header(rows, ["入账日期", "转入金额", "转出金额"])
    if header:
        return parse_simple_xlsx_rows(path, rows, header)
    return []


def parse_cmb_rows(path: Path, rows: Sequence[tuple[int, list[object]]], header: tuple[int, dict[str, int]]) -> list[BankRecord]:
    header_row, cols = header
    account_name = ""
    for _, row in rows[:12]:
        values = [clean_text(v) for v in row]
        if "账号名称" in values:
            pos = values.index("账号名称")
            account_name = clean_text(row[pos + 1]) if pos + 1 < len(row) else ""
            break

    company = infer_company(account_name, path.name)
    bank_name = infer_bank(path.name, account_name)
    records: list[BankRecord] = []
    for row_no, row in rows:
        if row_no <= header_row:
            continue
        trade_date = parse_date(row[cols["交易日"]] if cols["交易日"] < len(row) else None)
        debit = to_decimal(row[cols["借方金额"]] if cols["借方金额"] < len(row) else None)
        credit = to_decimal(row[cols["贷方金额"]] if cols["贷方金额"] < len(row) else None)
        if not trade_date or (debit == 0 and credit == 0):
            continue
        counterparty = clean_text(row[cols.get("收(付)方名称", -1)]) if cols.get("收(付)方名称", -1) < len(row) else ""
        summary = first_nonempty(row, cols, ["摘要", "用途", "业务名称", "业务摘要", "其它摘要"])
        unique_id = first_nonempty(row, cols, ["流水号", "业务参考号", "内部编号"])
        balance = to_decimal(row[cols.get("余额", -1)] if cols.get("余额", -1) >= 0 and cols.get("余额", -1) < len(row) else None)
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no, unique_id, balance))
    return records


def parse_simple_xlsx_rows(path: Path, rows: Sequence[tuple[int, list[object]]], header: tuple[int, dict[str, int]]) -> list[BankRecord]:
    header_row, cols = header
    company = infer_company("", path.name)
    bank_name = infer_bank(path.name)
    records: list[BankRecord] = []
    for row_no, row in rows:
        if row_no <= header_row:
            continue
        trade_date = parse_date(row[cols["入账日期"]] if cols["入账日期"] < len(row) else None)
        debit = to_decimal(row[cols["转出金额"]] if cols["转出金额"] < len(row) else None)
        credit = to_decimal(row[cols["转入金额"]] if cols["转入金额"] < len(row) else None)
        if not trade_date or (debit == 0 and credit == 0):
            continue
        counterparty = clean_text(row[cols.get("对方单位", -1)]) if cols.get("对方单位", -1) < len(row) else ""
        summary = first_nonempty(row, cols, ["摘要"])
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no))
    return records


def parse_xls(path: Path) -> list[BankRecord]:
    if xlrd is None:
        raise ImportError(
            f"读取 .xls 文件需要 xlrd 库：pip install xlrd\n"
            f"文件：{path}"
        )
    wb = xlrd.open_workbook(path)
    sh = wb.sheet_by_index(0)
    rows = [(r + 1, [sh.cell_value(r, c) for c in range(sh.ncols)]) for r in range(sh.nrows)]
    header = find_header(rows, ["交易日期", "借方发生额"])
    if header:
        return parse_ceb_rows(path, rows, header, wb.datemode)
    header = find_header(rows, ["交易时间", "收入金额", "支出金额"])
    if header:
        return parse_abc_rows(path, rows, header, wb.datemode)
    header = find_header(rows, ["交易日期", "借", "贷"])
    if header:
        return parse_pingan_rows(path, rows, header, wb.datemode)
    if sh.nrows > 8 and "交易日期" in clean_text(sh.cell_value(7, 10)):
        return parse_boc_rows(path, rows)
    return []


def parse_ceb_rows(path: Path, rows: Sequence[tuple[int, list[object]]], header: tuple[int, dict[str, int]], datemode: int) -> list[BankRecord]:
    header_row, cols = header
    account_name = ""
    for _, row in rows[:12]:
        values = [clean_text(v) for v in row]
        if "账户名称:" in values:
            pos = values.index("账户名称:")
            account_name = clean_text(row[pos + 1]) if pos + 1 < len(row) else ""
            break

    company = infer_company(account_name, path.name)
    bank_name = infer_bank(path.name, account_name)
    records: list[BankRecord] = []
    for row_no, row in rows:
        if row_no <= header_row:
            continue
        trade_date = parse_date(row[cols["交易日期"]] if cols["交易日期"] < len(row) else None, datemode)
        debit = to_decimal(row[cols["借方发生额"]] if cols["借方发生额"] < len(row) else None)
        credit = to_decimal(row[cols.get("贷方发生额", -1)] if cols.get("贷方发生额", -1) < len(row) else None)
        if not trade_date or (debit == 0 and credit == 0):
            continue
        counterparty = clean_text(row[cols.get("对方名称", -1)]) if cols.get("对方名称", -1) < len(row) else ""
        summary = first_nonempty(row, cols, [" 摘要", "摘要"])
        unique_id = first_nonempty(row, cols, ["流水号", "凭证号"])
        balance = to_decimal(row[cols.get("余额", -1)] if cols.get("余额", -1) >= 0 and cols.get("余额", -1) < len(row) else None)
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no, unique_id, balance))
    return records


def parse_abc_rows(path: Path, rows: Sequence[tuple[int, list[object]]], header: tuple[int, dict[str, int]], datemode: int) -> list[BankRecord]:
    header_row, cols = header
    account_name = ""
    for _, row in rows[:5]:
        for value in row:
            text = clean_text(value)
            if text.startswith("户名:"):
                account_name = text.replace("户名:", "").strip()
                break
    company = infer_company(account_name, path.name)
    bank_name = infer_bank(path.name, account_name)
    records: list[BankRecord] = []
    for row_no, row in rows:
        if row_no <= header_row:
            continue
        trade_date = parse_date(row[cols["交易时间"]] if cols["交易时间"] < len(row) else None, datemode)
        debit = to_decimal(row[cols["支出金额"]] if cols["支出金额"] < len(row) else None)
        credit = to_decimal(row[cols["收入金额"]] if cols["收入金额"] < len(row) else None)
        if not trade_date or (debit == 0 and credit == 0):
            continue
        counterparty = clean_text(row[cols.get("对方户名", -1)]) if cols.get("对方户名", -1) < len(row) else ""
        summary = " ".join(filter(None, [first_nonempty(row, cols, ["交易用途"]), first_nonempty(row, cols, ["摘要"])]))
        balance = to_decimal(row[cols.get("余额", -1)] if cols.get("余额", -1) >= 0 and cols.get("余额", -1) < len(row) else None)
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no, "", balance))
    return records


def parse_pingan_rows(path: Path, rows: Sequence[tuple[int, list[object]]], header: tuple[int, dict[str, int]], datemode: int) -> list[BankRecord]:
    header_row, cols = header
    company = infer_company("", path.name)
    bank_name = infer_bank(path.name)
    records: list[BankRecord] = []
    for row_no, row in rows:
        if row_no <= header_row:
            continue
        trade_date = parse_date(row[cols["交易日期"]] if cols["交易日期"] < len(row) else None, datemode)
        debit = to_decimal(row[cols["借"]] if cols["借"] < len(row) else None)
        credit = to_decimal(row[cols["贷"]] if cols["贷"] < len(row) else None)
        if not trade_date or (debit == 0 and credit == 0):
            continue
        counterparty = clean_text(row[cols.get("对方账户名称", -1)]) if cols.get("对方账户名称", -1) < len(row) else ""
        summary = " ".join(filter(None, [first_nonempty(row, cols, ["摘要"]), first_nonempty(row, cols, ["用途"])]))
        unique_id = first_nonempty(row, cols, ["交易流水号"])
        balance = to_decimal(row[cols.get("余额", -1)] if cols.get("余额", -1) >= 0 and cols.get("余额", -1) < len(row) else None)
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no, unique_id, balance))
    return records


def parse_boc_rows(path: Path, rows: Sequence[tuple[int, list[object]]]) -> list[BankRecord]:
    company = infer_company("", path.name)
    bank_name = infer_bank(path.name)
    records: list[BankRecord] = []
    for row_no, row in rows[8:]:
        if len(row) < 26:
            continue
        trade_date = parse_date(clean_text(row[10]))
        signed_amount = to_decimal(row[13])
        if not trade_date or signed_amount == 0:
            continue
        debit = abs(signed_amount) if signed_amount < 0 else Decimal("0")
        credit = signed_amount if signed_amount > 0 else Decimal("0")
        counterparty = clean_text(row[9] if debit == 0 else row[5])
        summary = " ".join(filter(None, [clean_text(row[24]), clean_text(row[25])]))
        unique_id = clean_text(row[17])
        records.append(BankRecord(company, trade_date, debit, credit, counterparty, summary, bank_name, path.name, row_no, unique_id))
    return records


def first_nonempty(row: Sequence[object], cols: dict[str, int], names: Sequence[str]) -> str:
    for name in names:
        idx = cols.get(name, -1)
        if 0 <= idx < len(row):
            value = clean_text(row[idx])
            if value:
                return value
    return ""


def read_records(input_dir: Path) -> list[BankRecord]:
    records: list[BankRecord] = []
    for path in sorted(input_dir.iterdir()):
        if path.name.startswith(".") or not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            records.extend(parse_xlsx(path))
        elif suffix == ".xls":
            records.extend(parse_xls(path))
    return dedupe_records(records)


def dedupe_records(records: Sequence[BankRecord]) -> list[BankRecord]:
    seen: set[tuple[object, ...]] = set()
    result: list[BankRecord] = []
    for rec in records:
        key = (
            rec.company,
            rec.trade_date.isoformat(),
            str(rec.debit),
            str(rec.credit),
            rec.counterparty,
            rec.summary,
            rec.unique_id,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(rec)
    return result


def filter_month(records: Iterable[BankRecord], month: str) -> list[BankRecord]:
    return sorted(
        [rec for rec in records if rec.trade_date.strftime("%Y-%m") == month],
        key=lambda rec: (rec.trade_date, rec.company, rec.bank_name, rec.source_file, rec.source_row),
    )


def add_title(ws, title: str, end_col: int, subtitle: str = "") -> None:
    """
    在工作表第1行写入主标题（深蓝底白字）。
    若提供 subtitle，则在第2行写入单位/期间等辅助信息（中蓝底白字）。
    """
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    cell = ws.cell(1, 1, title)
    cell.font      = Font(bold=True, size=14, color=_C_WHITE, name="微软雅黑")
    cell.fill      = PatternFill("solid", fgColor=_C_NAVY)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30
    if subtitle:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=end_col)
        sub = ws.cell(2, 1, subtitle)
        sub.font      = Font(bold=False, size=10, color=_C_WHITE, name="微软雅黑")
        sub.fill      = PatternFill("solid", fgColor=_C_BLUE)
        sub.alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[2].height = 18


def style_range(ws) -> None:
    """
    为工作表整体应用上市公司财务报表样式。

    行类型识别逻辑（按优先级）：
      - 第1行            → 主标题（深蓝底白字 14pt）
      - 第2~4行          → 列表头/副标题（中蓝底白字 10pt）
      - 含"合计"/"汇总"  → 合计行（浅蓝底深色粗体）
      - 含"扣除集团内往来款" → 净支出行（浅绿底深色粗体）
      - 含"集团内往来款"（不含"扣除"）→ 往来款说明行（浅灰底灰色斜体）
      - 其余数据行        → 奇偶交替底色
    数字格式：统一应用千分位两位小数。
    """
    # 检测第1行是否为合并单元格（合并→大标题；非合并→列表头）
    row1_has_merge = any(mr.min_row == 1 for mr in ws.merged_cells.ranges)
    # 检测第2-4行是否有合并单元格（真正多行表头结构，如支出明细）
    # 当第1行已是大标题时，第2-4行的合并仅为信息行，不应作为表头
    row2_4_has_merge = (
        not row1_has_merge
        and any(mr.min_row in (2, 3, 4) for mr in ws.merged_cells.ranges)
    )

    data_row_counter = 0
    for row in ws.iter_rows():
        r = row[0].row
        # 收集该行所有文字，用于行类型判断
        row_text = " ".join(str(c.value or "") for c in row)
        first_val = str(row[0].value or "")

        # ── 判断行类型 ────────────────────────────────────────────────
        if r == 1 and row1_has_merge:
            row_type = "title"           # 第1行有合并单元格 → 大标题行
        elif r == 1 or (r in (2, 3, 4) and row2_4_has_merge):
            row_type = "header"
        elif "扣除集团内往来款" in row_text:
            row_type = "net"
        elif "集团内往来款" in row_text:
            row_type = "intragroup"
        elif any(kw in first_val for kw in ("合计", "汇总")) and r > 1:
            row_type = "total"
        else:
            data_row_counter += 1
            row_type = "data_odd" if data_row_counter % 2 == 1 else "data_even"

        # ── 应用样式 ──────────────────────────────────────────────────
        for cell in row:
            cell.border = _BORDER_THIN

            if row_type == "title":
                cell.font      = Font(bold=True, size=14, color=_C_WHITE, name="微软雅黑")
                cell.fill      = PatternFill("solid", fgColor=_C_NAVY)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                ws.row_dimensions[r].height = 30

            elif row_type == "header":
                cell.font      = Font(bold=True, size=10, color=_C_WHITE, name="微软雅黑")
                cell.fill      = PatternFill("solid", fgColor=_C_BLUE)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                # 含换行符的列头需要更高行高
                has_newline = "\n" in str(cell.value or "")
                ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 36 if has_newline else 20)

            elif row_type == "total":
                cell.font      = Font(bold=True, size=10, color=_C_NAVY, name="微软雅黑")
                cell.fill      = PatternFill("solid", fgColor=_C_LBLUE)
                cell.alignment = _align_for(cell)

            elif row_type == "net":
                cell.font      = Font(bold=True, size=10, color=_C_NAVY, name="微软雅黑")
                cell.fill      = PatternFill("solid", fgColor=_C_GREEN)
                cell.alignment = _align_for(cell)

            elif row_type == "intragroup":
                cell.font      = Font(italic=True, size=10, color=_C_TXT_GRAY, name="微软雅黑")
                cell.fill      = PatternFill("solid", fgColor=_C_GRAY)
                cell.alignment = _align_for(cell)

            else:  # data
                cell.font      = Font(size=10, name="微软雅黑")
                bg = _C_STRIPE if row_type == "data_odd" else _C_WHITE
                cell.fill      = PatternFill("solid", fgColor=bg)
                cell.alignment = _align_for(cell)

            # 数字格式：整数用无小数格式（如行号/年份），浮点数用千分位两位小数
            if isinstance(cell.value, float) and row_type not in ("title", "header"):
                cell.number_format = _NUM_FMT
            elif isinstance(cell.value, int) and row_type not in ("title", "header"):
                cell.number_format = "0"   # 整数列（来源Sheet行号、年份、月份等）不显示小数


def _align_for(cell) -> Alignment:
    """根据单元格值类型决定对齐方式：数字右对齐，文字左对齐，空值居中。"""
    if isinstance(cell.value, (int, float)):
        return Alignment(horizontal="right", vertical="center")
    if cell.value:
        return Alignment(horizontal="left", vertical="center", wrap_text=True)
    return Alignment(horizontal="center", vertical="center")


def build_workbook(records: Sequence[BankRecord], month: str, rules: ClassificationRuleSet) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)
    year, month_no = month.split("-")
    month_label = f"{int(month_no)}月"

    expense_records = [rec for rec in records if rec.debit > 0]
    income_records = [rec for rec in records if rec.credit > 0]
    total_expense = sum((rec.debit for rec in expense_records), Decimal("0"))
    total_income = sum((rec.credit for rec in income_records), Decimal("0"))
    net_outflow = total_expense - total_income

    # 计算集团内部往来款金额（用于首页扣减展示）
    classified_expense = [classify_record_detail(rec, rules) for rec in expense_records]
    intragroup_expense = sum(
        (item.record.debit for item in classified_expense if is_intragroup(item)),
        Decimal("0"),
    )

    build_total_sheet(wb, month_label, total_income, total_expense, net_outflow, intragroup_expense)
    build_income_sheet(wb, month_label, total_income)
    build_expense_summary_sheet(wb, expense_records, month_label, rules)
    build_detail_sheet(wb, expense_records, month_label, rules)
    return wb


def payment_period(trade_date: dt.date) -> str:
    if trade_date.day <= 10:
        return "月初支付"
    if trade_date.day <= 20:
        return "月中支付"
    return "月末支付"


def is_unmatched(item: ClassifiedRecord) -> bool:
    return item.fee in {"", "未匹配"} or item.department in {"", "未分配"}


INTRAGROUP_FEE_TYPES = {"分子公司借款", "医馆借款"}


def is_intragroup(item: ClassifiedRecord) -> bool:
    """判断是否为集团内部往来款（统计时可抵消）。"""
    return item.fee in INTRAGROUP_FEE_TYPES


def classify_expense_records(records: Sequence[BankRecord], rules: ClassificationRuleSet, year: int | None = None) -> list[ClassifiedRecord]:
    items = [
        classify_record_detail(rec, rules)
        for rec in records
        if rec.debit > 0 and (year is None or rec.trade_date.year == year)
    ]
    return sorted(
        items,
        key=lambda item: (
            item.record.trade_date,
            item.record.company,
            item.record.bank_name,
            item.record.source_file,
            item.record.source_row,
        ),
    )


def infer_report_year(records: Sequence[BankRecord], requested_year: int | None) -> int:
    if requested_year:
        return requested_year
    years = sorted({rec.trade_date.year for rec in records})
    if not years:
        raise SystemExit("未找到可识别年份的银行流水记录")
    return years[-1]


def build_annual_workbook(records: Sequence[BankRecord], rules: ClassificationRuleSet, year: int, source_count: int) -> Workbook:
    items = classify_expense_records(records, rules, year)
    if not items:
        raise SystemExit(f"未找到 {year} 年的支出流水记录")

    wb = Workbook()
    wb.remove(wb.active)
    build_annual_overview_sheet(wb, items, year, source_count)
    build_month_matrix_sheet(wb, "公司月度汇总", items, lambda item: item.record.company)
    build_month_matrix_sheet(wb, "费用类型汇总", items, lambda item: item.fee)
    build_month_matrix_sheet(wb, "承担部门汇总", items, lambda item: item.department)
    for month in sorted({item.record.trade_date.month for item in items}):
        month_items = [item for item in items if item.record.trade_date.month == month]
        build_month_summary_sheet(wb, month, month_items)
        build_month_detail_sheet(wb, month, month_items, unmatched_only=False)
        build_month_detail_sheet(wb, month, month_items, unmatched_only=True)
    return wb


def build_annual_overview_sheet(wb: Workbook, items: Sequence[ClassifiedRecord], year: int, source_count: int) -> None:
    ws = wb.create_sheet("全年总览")
    total = sum((item.record.debit for item in items), Decimal("0"))
    unmatched_items = [item for item in items if is_unmatched(item)]
    unmatched_total = sum((item.record.debit for item in unmatched_items), Decimal("0"))
    intragroup_items = [item for item in items if is_intragroup(item)]
    intragroup_total = sum((item.record.debit for item in intragroup_items), Decimal("0"))
    net_total = total - intragroup_total
    dates = [item.record.trade_date for item in items]
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    MAX_COL = 8   # 月度表最宽8列（A~H），标题行与其对齐
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=MAX_COL)
    title_cell = ws.cell(1, 1, f"{year}年银行收支全年统计")
    title_cell.font      = Font(bold=True, size=16, color=_C_WHITE, name="微软雅黑")
    title_cell.fill      = PatternFill("solid", fgColor=_C_NAVY)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 信息行 2-7：标签在A列，值合并 B~H（整行视觉对齐）
    info = [
        ("交易起始日期", min(dates).strftime("%Y-%m-%d")),
        ("交易截止日期", max(dates).strftime("%Y-%m-%d")),
        ("文件生成时间", generated_at),
        ("处理文件数量", f"{source_count} 个"),
        ("总支出金额（元）", f"{decimal_to_float(total):,.2f}"),
        ("未匹配金额（元）", f"{decimal_to_float(unmatched_total):,.2f}"),
    ]
    _info_fill   = PatternFill("solid", fgColor=_C_LBLUE)
    _info_font_l = Font(bold=True, size=10, color=_C_NAVY, name="微软雅黑")
    _info_font_v = Font(size=10, color=_C_NAVY, name="微软雅黑")
    for row_no, (label, value) in enumerate(info, start=2):
        ws.cell(row_no, 1, label).font = _info_font_l
        ws.cell(row_no, 1).fill       = _info_fill
        ws.cell(row_no, 1).alignment  = Alignment(horizontal="right", vertical="center")
        ws.cell(row_no, 1).border     = _BORDER_THIN
        ws.merge_cells(start_row=row_no, start_column=2, end_row=row_no, end_column=MAX_COL)
        val_cell = ws.cell(row_no, 2, value)
        val_cell.font      = _info_font_v
        val_cell.fill      = _info_fill
        val_cell.alignment = Alignment(horizontal="left", vertical="center")
        val_cell.border    = _BORDER_THIN
        ws.row_dimensions[row_no].height = 18

    # 空行 8：视觉分隔
    ws.row_dimensions[8].height = 6

    start = 9
    rows = [
        ("总支出金额", total, len(items), False),
        ("  其中：集团内部往来款（可抵消）", intragroup_total, len(intragroup_items), True),
        ("扣除集团内往来款后净支出", net_total, len(items) - len(intragroup_items), False),
        ("已完整匹配金额", total - unmatched_total, len(items) - len(unmatched_items), False),
        ("未匹配金额", unmatched_total, len(unmatched_items), False),
    ]
    ws.cell(start, 1, "指标")
    ws.cell(start, 2, "金额\n（元）")
    ws.cell(start, 3, "金额\n（万元）")
    ws.cell(start, 4, "笔数")
    for offset, (label, amount, count, is_gray) in enumerate(rows, start=1):
        r = start + offset
        ws.cell(r, 1, label)
        ws.cell(r, 2, decimal_to_float(amount))
        ws.cell(r, 3, decimal_to_float(quantize_wan(amount)))
        ws.cell(r, 4, count)
        # 字体/填充样式由 style_range() 根据行内容自动处理，此处无需手动设置

    month_start = start + len(rows) + 4
    ws.cell(month_start, 1, "月份")
    ws.cell(month_start, 2, "总支出金额\n（元）")
    ws.cell(month_start, 3, "总笔数")
    ws.cell(month_start, 4, "集团内往来款\n（元）")
    ws.cell(month_start, 5, "扣除集团内往来款\n净支出（元）")
    ws.cell(month_start, 6, "已完整匹配金额\n（元）")
    ws.cell(month_start, 7, "未匹配金额\n（元）")
    ws.cell(month_start, 8, "未匹配笔数")
    for offset, month in enumerate(sorted({item.record.trade_date.month for item in items}), start=1):
        month_items = [item for item in items if item.record.trade_date.month == month]
        month_total = sum((item.record.debit for item in month_items), Decimal("0"))
        month_unmatched = [item for item in month_items if is_unmatched(item)]
        month_unmatched_total = sum((item.record.debit for item in month_unmatched), Decimal("0"))
        month_intragroup = sum((item.record.debit for item in month_items if is_intragroup(item)), Decimal("0"))
        row = month_start + offset
        ws.cell(row, 1, month)
        ws.cell(row, 2, decimal_to_float(month_total))
        ws.cell(row, 3, len(month_items))
        ws.cell(row, 4, decimal_to_float(month_intragroup))
        ws.cell(row, 5, decimal_to_float(month_total - month_intragroup))
        ws.cell(row, 6, decimal_to_float(month_total - month_unmatched_total))
        ws.cell(row, 7, decimal_to_float(month_unmatched_total))
        ws.cell(row, 8, len(month_unmatched))

    ws.column_dimensions["A"].width = 24
    for col in range(2, 9):
        ws.column_dimensions[get_column_letter(col)].width = 18
    style_range(ws)


def build_month_matrix_sheet(wb: Workbook, title: str, items: Sequence[ClassifiedRecord], key_func) -> None:
    """
    生成月度矩阵汇总表（公司月度汇总 / 费用类型汇总 / 承担部门汇总）。

    合计行后追加"集团内往来款"行和"扣除集团内往来款后净支出"行，
    方便管理层一眼看出对外实际支出，无需手动计算。
    """
    ws = wb.create_sheet(title)
    months = sorted({item.record.trade_date.month for item in items})
    keys = sorted({key_func(item) or "未识别" for item in items})
    ws.cell(1, 1, "月份")
    for col, key in enumerate(keys, start=2):
        ws.cell(1, col, f"{key}\n（万元）")
    total_col = len(keys) + 2
    ws.cell(1, total_col, "汇总\n（万元）")

    column_totals     = {key: Decimal("0") for key in keys}
    intragroup_totals = {key: Decimal("0") for key in keys}
    grand_total       = Decimal("0")

    for row_no, month in enumerate(months, start=2):
        ws.cell(row_no, 1, month)
        month_total = Decimal("0")
        for col, key in enumerate(keys, start=2):
            # 全量金额
            value = sum(
                (item.record.debit for item in items
                 if item.record.trade_date.month == month and (key_func(item) or "未识别") == key),
                Decimal("0"),
            )
            # 集团内往来款金额（用于扣减）
            intra_value = sum(
                (item.record.debit for item in items
                 if item.record.trade_date.month == month
                 and (key_func(item) or "未识别") == key
                 and is_intragroup(item)),
                Decimal("0"),
            )
            column_totals[key]     += value
            intragroup_totals[key] += intra_value
            month_total            += value
            ws.cell(row_no, col, decimal_to_float(quantize_wan(value)))
        grand_total += month_total
        ws.cell(row_no, total_col, decimal_to_float(quantize_wan(month_total)))

    # ── 合计行 ────────────────────────────────────────────────────────────
    total_row = len(months) + 2
    ws.cell(total_row, 1, "合计")
    for col, key in enumerate(keys, start=2):
        ws.cell(total_row, col, decimal_to_float(quantize_wan(column_totals[key])))
    ws.cell(total_row, total_col, decimal_to_float(quantize_wan(grand_total)))

    # ── 集团内往来款行（灰色，可抵消，供参考）────────────────────────────
    intra_row = total_row + 1
    intra_grand = sum(intragroup_totals.values(), Decimal("0"))
    ws.cell(intra_row, 1, "  其中：集团内往来款")
    for col, key in enumerate(keys, start=2):
        v = intragroup_totals[key]
        ws.cell(intra_row, col, decimal_to_float(quantize_wan(v)) if v else "")
    ws.cell(intra_row, total_col, decimal_to_float(quantize_wan(intra_grand)) if intra_grand else "")

    # ── 净支出行（扣除集团内往来款后）──────────────────────────────────
    net_row = total_row + 2
    net_grand = grand_total - intra_grand
    ws.cell(net_row, 1, "扣除集团内往来款后净支出")
    for col, key in enumerate(keys, start=2):
        v = column_totals[key] - intragroup_totals[key]
        ws.cell(net_row, col, decimal_to_float(quantize_wan(v)) if v else "")
    ws.cell(net_row, total_col, decimal_to_float(quantize_wan(net_grand)))

    ws.column_dimensions["A"].width = 24
    for col in range(2, total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    style_range(ws)


def build_month_summary_sheet(wb: Workbook, month: int, items: Sequence[ClassifiedRecord]) -> None:
    ws = wb.create_sheet(f"{month}月汇总")
    companies = sorted({item.record.company for item in items})
    fees = sorted({item.fee for item in items})
    ws.cell(1, 1, "公司名称")
    for col, fee in enumerate(fees, start=2):
        ws.cell(1, col, f"{fee}\n（元）")
    total_col = len(fees) + 2
    ws.cell(1, total_col, "合计\n（元）")

    fee_totals = {fee: Decimal("0") for fee in fees}
    grand_total = Decimal("0")
    for row_no, company in enumerate(companies, start=2):
        ws.cell(row_no, 1, company)
        company_total = Decimal("0")
        for col, fee in enumerate(fees, start=2):
            value = sum((item.record.debit for item in items if item.record.company == company and item.fee == fee), Decimal("0"))
            fee_totals[fee] += value
            company_total += value
            ws.cell(row_no, col, decimal_to_float(value))
        grand_total += company_total
        ws.cell(row_no, total_col, decimal_to_float(company_total))

    total_row = len(companies) + 2
    ws.cell(total_row, 1, "合计")
    for col, fee in enumerate(fees, start=2):
        ws.cell(total_row, col, decimal_to_float(fee_totals[fee]))
    ws.cell(total_row, total_col, decimal_to_float(grand_total))

    # ── 集团内往来款行（灰色，可抵消）────────────────────────────────────
    intra_row = total_row + 1
    intra_grand = sum(
        (item.record.debit for item in items if is_intragroup(item)), Decimal("0")
    )
    ws.cell(intra_row, 1, "  其中：集团内往来款")
    for col, fee in enumerate(fees, start=2):
        v = sum(
            (item.record.debit for item in items if item.fee == fee and is_intragroup(item)),
            Decimal("0"),
        )
        ws.cell(intra_row, col, decimal_to_float(v) if v else "")
    ws.cell(intra_row, total_col, decimal_to_float(intra_grand) if intra_grand else "")

    # ── 净支出行 ──────────────────────────────────────────────────────────
    net_row = total_row + 2
    ws.cell(net_row, 1, "扣除集团内往来款后净支出")
    net_grand = grand_total - intra_grand
    for col, fee in enumerate(fees, start=2):
        v = fee_totals[fee] - sum(
            (item.record.debit for item in items if item.fee == fee and is_intragroup(item)),
            Decimal("0"),
        )
        ws.cell(net_row, col, decimal_to_float(v) if v else "")
    ws.cell(net_row, total_col, decimal_to_float(net_grand))

    ws.column_dimensions["A"].width = 24
    for col in range(2, total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    style_range(ws)


def build_month_detail_sheet(wb: Workbook, month: int, items: Sequence[ClassifiedRecord], unmatched_only: bool) -> None:
    title = f"{month}月未匹配" if unmatched_only else f"{month}月明细"
    ws = wb.create_sheet(title)
    headers = [
        "年份",
        "月份",
        "公司名称",
        "交易日期",
        "支付时段",
        "借方发生额\n（元）",
        "对方名称",
        "摘要",
        "银行名称",
        "费用类型",
        "承担部门",
        "匹配说明",
        "来源文件",
        "来源Sheet",
    ]
    ws.append(headers)
    output_items = [item for item in items if is_unmatched(item)] if unmatched_only else list(items)
    for item in output_items:
        rec = item.record
        ws.append(
            [
                rec.trade_date.year,
                rec.trade_date.month,
                rec.company,
                rec.trade_date.isoformat(),
                payment_period(rec.trade_date),
                decimal_to_float(rec.debit),
                rec.counterparty,
                rec.summary,
                rec.bank_name,
                item.fee,
                item.department,
                item.match_note,
                rec.source_file,
                rec.source_row,
            ]
        )
    widths = [8, 8, 16, 14, 12, 16, 34, 42, 20, 16, 16, 34, 30, 12]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"
    style_range(ws)


def build_total_sheet(
    wb: Workbook,
    month_label: str,
    total_income: Decimal,
    total_expense: Decimal,
    net_outflow: Decimal,
    intragroup_expense: Decimal = Decimal("0"),
) -> None:
    ws = wb.create_sheet(f"{month_label}收款支出总额")
    add_title(ws, "收款支出   （单位：万元）", 6)
    ws.append(["区间", "收款金额", "支出金额", "净流出", "银行余额", "可用余额"])
    ws.append([
        f"本月（{month_label}）",
        decimal_to_float(quantize_wan(total_income)),
        decimal_to_float(quantize_wan(total_expense)),
        decimal_to_float(quantize_wan(net_outflow)),
        "", "",
    ])
    # 集团内部往来款单独展示（可抵消，不计入实际对外支出）
    net_expense = total_expense - intragroup_expense
    net_outflow_ex = net_expense - total_income
    ws.append([
        f"  其中：集团内部往来款（{month_label}）",
        "",
        decimal_to_float(quantize_wan(intragroup_expense)),
        "",
        "", "",
    ])
    ws.append([
        f"扣除集团内往来款后净支出（{month_label}）",
        decimal_to_float(quantize_wan(total_income)),
        decimal_to_float(quantize_wan(net_expense)),
        decimal_to_float(quantize_wan(net_outflow_ex)),
        "", "",
    ])
    # 集团内往来款行 / 净支出行样式由 style_range() 自动处理

    ws.column_dimensions["A"].width = 30
    for col in "BCDEF":
        ws.column_dimensions[col].width = 14
    style_range(ws)


def build_income_sheet(wb: Workbook, month_label: str, total_income: Decimal) -> None:
    ws = wb.create_sheet("收款明细")
    add_title(ws, "收款明细  （单位：万元）", 3)
    ws.append(["收款平台", f"本月收款金额（{month_label}）", "备注"])
    ws.append(["银行贷方收入合计", decimal_to_float(quantize_wan(total_income)), "未按业务平台拆分"])
    ws.append(["合计", decimal_to_float(quantize_wan(total_income)), ""])
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 24
    style_range(ws)


def build_expense_summary_sheet(wb: Workbook, records: Sequence[BankRecord], month_label: str, rules: ClassificationRuleSet) -> None:
    ws = wb.create_sheet("支出明细")
    total_cols = 1 + 1 + len(EXPENSE_COLUMNS) + len(OTHER_EXPENSE_COLUMNS) + 1
    ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=total_cols)
    ws.cell(2, 2, f"支出明细（{month_label}）         单位：万元")
    ws.merge_cells(start_row=3, start_column=2, end_row=4, end_column=2)
    ws.cell(3, 2, "公司名称")
    ws.merge_cells(start_row=3, start_column=3, end_row=3, end_column=2 + len(EXPENSE_COLUMNS))
    ws.cell(3, 3, "费用支出")
    start_other = 3 + len(EXPENSE_COLUMNS)
    for idx, name in enumerate(OTHER_EXPENSE_COLUMNS, start=start_other):
        ws.merge_cells(start_row=3, start_column=idx, end_row=4, end_column=idx)
        ws.cell(3, idx, name)
    total_col = start_other + len(OTHER_EXPENSE_COLUMNS)
    ws.merge_cells(start_row=3, start_column=total_col, end_row=4, end_column=total_col)
    ws.cell(3, total_col, "合计")
    for idx, name in enumerate(EXPENSE_COLUMNS, start=3):
        ws.cell(4, idx, name)

    totals: dict[str, dict[str, Decimal]] = {}
    for rec in records:
        company = summary_company(rec.company)
        fee, _ = classify_record(rec, rules)
        summary_col = SUMMARY_FEE_COLUMN.get(fee, "")
        if company not in totals:
            totals[company] = {}
        if summary_col:
            totals[company][summary_col] = totals[company].get(summary_col, Decimal("0")) + rec.debit
        totals[company]["合计"] = totals[company].get("合计", Decimal("0")) + rec.debit

    row_no = 5
    all_summary_columns = EXPENSE_COLUMNS + OTHER_EXPENSE_COLUMNS
    for company in SUMMARY_COMPANIES:
        ws.cell(row_no, 2, company)
        company_totals = totals.get(company, {})
        for col_offset, column_name in enumerate(all_summary_columns, start=3):
            value = company_totals.get(column_name, Decimal("0"))
            ws.cell(row_no, col_offset, decimal_to_float(quantize_wan(value)) if value else "")
        ws.cell(row_no, total_col, decimal_to_float(quantize_wan(company_totals.get("合计", Decimal("0")))))
        row_no += 1

    ws.cell(row_no, 2, "合计")
    for col_offset, column_name in enumerate(all_summary_columns, start=3):
        value = sum((company_totals.get(column_name, Decimal("0")) for company_totals in totals.values()), Decimal("0"))
        ws.cell(row_no, col_offset, decimal_to_float(quantize_wan(value)) if value else "")
    grand_total = sum((company_totals.get("合计", Decimal("0")) for company_totals in totals.values()), Decimal("0"))
    ws.cell(row_no, total_col, decimal_to_float(quantize_wan(grand_total)))

    # 集团内部往来款汇总行（灰色斜体，提示可抵消）
    row_no += 1
    intragroup_keys = set(INTRAGROUP_FEE_TYPES)
    intragroup_summary_cols = {c for c in all_summary_columns if c in intragroup_keys}
    ws.cell(row_no, 2, "  其中：集团内部往来款")
    intragroup_grand = Decimal("0")
    for col_offset, column_name in enumerate(all_summary_columns, start=3):
        if column_name in intragroup_summary_cols:
            value = sum((company_totals.get(column_name, Decimal("0")) for company_totals in totals.values()), Decimal("0"))
            ws.cell(row_no, col_offset, decimal_to_float(quantize_wan(value)) if value else "")
            intragroup_grand += value
        else:
            ws.cell(row_no, col_offset, "")
    ws.cell(row_no, total_col, decimal_to_float(quantize_wan(intragroup_grand)) if intragroup_grand else "")
    # 集团内往来款行样式由 style_range() 自动处理

    # 扣除集团内往来款后净支出合计行
    row_no += 1
    ws.cell(row_no, 2, "扣除集团内往来款后净支出")
    net_grand = grand_total - intragroup_grand
    for col_offset, column_name in enumerate(all_summary_columns, start=3):
        if column_name not in intragroup_summary_cols:
            value = sum((company_totals.get(column_name, Decimal("0")) for company_totals in totals.values()), Decimal("0"))
            ws.cell(row_no, col_offset, decimal_to_float(quantize_wan(value)) if value else "")
        else:
            ws.cell(row_no, col_offset, "")
    ws.cell(row_no, total_col, decimal_to_float(quantize_wan(net_grand)))
    # 净支出行样式由 style_range() 自动处理

    ws.column_dimensions["B"].width = 16
    for col in range(3, total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 12
    style_range(ws)


def build_detail_sheet(wb: Workbook, records: Sequence[BankRecord], month_label: str, rules: ClassificationRuleSet) -> None:
    ws = wb.create_sheet(f"{month_label}全公司所有支出")
    ws.append(OUTPUT_COLUMNS)
    for rec in records:
        fee, department = classify_record(rec, rules)
        ws.append(
            [
                rec.company,
                rec.trade_date.isoformat(),
                decimal_to_float(rec.debit),
                rec.counterparty,
                rec.summary,
                rec.bank_name,
                fee,
                department,
            ]
        )
    widths = [16, 14, 14, 34, 42, 20, 14, 14]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A2"
    style_range(ws)


def next_output_path(output_dir: Path, base_name: str) -> Path:
    """
    生成带日期+流水号的输出路径。

    命名规则：YYYYMMDD_NNN_base_name
      - YYYYMMDD：当日日期
      - NNN：当日同名称文件的递增流水号（001, 002, …）
      - base_name：报表文件名（含 .xlsx 扩展名）

    示例：20260506_001_2026年银行收支全年统计.xlsx
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    existing = sorted(output_dir.glob(f"{today}_???_{base_name}"))
    seq = len(existing) + 1
    return output_dir / f"{today}_{seq:03d}_{base_name}"


def save_workbook(wb: Workbook, output_dir: Path, month: str) -> Path:
    """保存月度报表，文件名含日期流水号。"""
    year, month_no = month.split("-")
    base = f"{year}年{int(month_no):02d}月收款支出统计.xlsx"
    path = next_output_path(output_dir, base)
    wb.save(path)
    return path


def save_annual_workbook(wb: Workbook, output_dir: Path, year: int) -> Path:
    """保存全年报表，文件名含日期流水号。"""
    base = f"{year}年银行【支出】全年统计.xlsx"
    path = next_output_path(output_dir, base)
    wb.save(path)
    return path


def export_unmatched_for_correction(
    items: Sequence[ClassifiedRecord],
    output_dir: Path,
    label: str,
) -> Path | None:
    """
    将未完整匹配的记录导出为待修正工作表，供财务人员人工填写。

    导出列说明：
      - 年份～银行名称：原始流水信息（只读参考）
      - 当前费用类型/承担部门：程序自动匹配结果（可能错误）
      - 修正费用类型 ← 用户填写正确费用类型
      - 修正承担部门 ← 用户填写正确承担部门
      - 核对备注     ← 用户可填写说明
      - _映射键      ← 程序内部使用（对方名称|摘要|银行名称的紧凑拼接），请勿删除此列

    填写完成后，运行 apply_corrections.py 将修正记录写入规则库，并重新生成报表。
    """
    unmatched = [item for item in items if is_unmatched(item)]
    if not unmatched:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "未匹配记录_待修正"

    # ── 标题行 ────────────────────────────────────────────────────────
    headers = [
        "年份", "月份", "公司名称", "交易日期", "借方发生额（元）",
        "对方名称", "摘要", "银行名称",
        "当前费用类型", "当前承担部门",
        "修正费用类型",   # ← 财务人员填写
        "修正承担部门",   # ← 财务人员填写
        "核对备注",       # ← 财务人员填写
        "_映射键",        # 程序内部列，请勿删除或修改
    ]
    ws.append(headers)

    # ── 数据行 ────────────────────────────────────────────────────────
    for item in unmatched:
        rec = item.record
        ws.append([
            str(rec.trade_date.year),           # 字符串，避免被格式化为小数
            str(rec.trade_date.month),           # 字符串，避免被格式化为小数
            rec.company,
            rec.trade_date.isoformat(),
            decimal_to_float(rec.debit),
            rec.counterparty,
            rec.summary,
            rec.bank_name,
            item.fee,
            item.department,
            "",   # 修正费用类型（待填）
            "",   # 修正承担部门（待填）
            "",   # 核对备注（待填）
            exact_key_from_record(rec),   # _映射键（程序内部）
        ])

    # ── 样式：区分"待填列"和只读列 ───────────────────────────────────
    EDIT_COLS = {11, 12, 13}   # 修正费用类型、修正承担部门、核对备注（1-indexed）
    HIDE_COL  = 14             # _映射键列（隐藏）

    header_fill    = PatternFill("solid", fgColor=_C_BLUE)
    edit_fill      = PatternFill("solid", fgColor="FFF2CC")   # 黄色：待填
    readonly_fill  = PatternFill("solid", fgColor=_C_STRIPE)
    header_font    = Font(bold=True, color=_C_WHITE, size=10, name="微软雅黑")
    data_font      = Font(size=10, name="微软雅黑")

    for row in ws.iter_rows():
        for cell in row:
            col = cell.column
            cell.border = _BORDER_THIN
            cell.alignment = Alignment(vertical="center", wrap_text=True,
                                       horizontal="right" if isinstance(cell.value, (int, float)) else "left")
            if isinstance(cell.value, (int, float)):
                cell.number_format = _NUM_FMT
            if cell.row == 1:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif col in EDIT_COLS:
                cell.font = data_font
                cell.fill = edit_fill
            elif col == HIDE_COL:
                cell.font = Font(size=9, color="AAAAAA", name="微软雅黑")
                cell.fill = PatternFill("solid", fgColor=_C_GRAY)
            else:
                cell.font = data_font
                cell.fill = readonly_fill

    # ── 列宽 ─────────────────────────────────────────────────────────
    col_widths = [8, 6, 16, 12, 16, 28, 36, 20, 14, 14, 16, 16, 20, 42]
    for idx, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22

    base = f"{label}_支出未匹配记录_待修正.xlsx"
    path = next_output_path(output_dir, base)
    wb.save(path)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# 收入统计模块
# ═══════════════════════════════════════════════════════════════════════════

# ── 收入规则加载 ─────────────────────────────────────────────────────────────

def load_income_classification_rules(mapping_path: Path | None) -> ClassificationRuleSet:
    """
    加载收入分类规则。
    结构与支出规则相同（精确映射 + 关键词规则），收入类型写在"收入类型"列，
    来源公司写在"来源公司"列（对应支出的"承担部门"列位置）。
    """
    exact: dict[str, tuple[str, str]] = {}
    keyword: list[tuple[str, str, str]] = [
        (pattern, income_type, source_co)
        for pattern, income_type, source_co in DEFAULT_INCOME_KEYWORD_RULES
    ]

    if mapping_path and mapping_path.exists():
        try:
            wb = openpyxl.load_workbook(mapping_path, read_only=True, data_only=True)
        except Exception:
            return ClassificationRuleSet(exact=exact, keyword=keyword)

        # 兼容新版规则库（支出_精确映射）和旧版（精确映射）——收入暂无独立精确映射 Sheet
        exact_sn = next(
            (n for n in ("收入_精确映射", "精确映射") if n in wb.sheetnames), None
        )
        if exact_sn:
            ws = wb[exact_sn]
            header_row = _find_header_row(ws, {"映射键"})
            if header_row:
                h_idx, headers = header_row
                cols = {h: i for i, h in enumerate(headers)}
                for row in ws.iter_rows(min_row=h_idx + 1, values_only=True):
                    key = compact_text(row[cols.get("映射键", 0)]) if cols.get("映射键", 0) < len(row) else ""
                    it  = clean_text(row[cols.get("收入类型", cols.get("费用类型", 1))]) if max(cols.get("收入类型", cols.get("费用类型", 1)), 0) < len(row) else ""
                    co  = clean_text(row[cols.get("来源公司", cols.get("承担部门", 2))]) if max(cols.get("来源公司", cols.get("承担部门", 2)), 0) < len(row) else ""
                    if key and it:
                        exact[key] = (it, co)

        # 兼容新版规则库（支出_关键词规则）和旧版（关键词规则）
        kw_sn = next(
            (n for n in ("收入_关键词规则", "支出_关键词规则", "关键词规则") if n in wb.sheetnames), None
        )
        if kw_sn:
            ws = wb[kw_sn]
            header_row = _find_header_row(ws, {"关键词正则"})
            if header_row:
                h_idx, headers = header_row
                cols = {h: i for i, h in enumerate(headers)}
                saved: list[tuple[int, str, str, str]] = []
                for order, row in enumerate(ws.iter_rows(min_row=h_idx + 1, values_only=True), start=1):
                    pattern  = clean_text(row[cols.get("关键词正则", 1)]) if cols.get("关键词正则", 1) < len(row) else ""
                    it       = clean_text(row[cols.get("收入类型", cols.get("费用类型", 2))]) if max(cols.get("收入类型", cols.get("费用类型", 2)), 0) < len(row) else ""
                    co       = clean_text(row[cols.get("来源公司", cols.get("承担部门", 3))]) if max(cols.get("来源公司", cols.get("承担部门", 3)), 0) < len(row) else ""
                    prio_raw = row[cols.get("优先级", 0)] if cols.get("优先级", 0) < len(row) else order
                    try:
                        prio = int(prio_raw)
                    except (TypeError, ValueError):
                        prio = order
                    if pattern and it:
                        saved.append((prio, pattern, it, co))
                if saved:
                    keyword = [(p, it, co) for _, p, it, co in sorted(saved)]

    return ClassificationRuleSet(exact=exact, keyword=keyword)


# ── 收入记录分类 ──────────────────────────────────────────────────────────────

def classify_income_record(rec: BankRecord, rules: ClassificationRuleSet) -> IncomeClassifiedRecord:
    """对单条贷方记录进行收入类型分类。

    优先使用智能匹配引擎（income_matcher.py），若不可用则回退到旧关键词规则。
    """
    # ── 优先：智能规则引擎（100% 准确率）──────────────────────────────────
    if _INCOME_MATCHER_AVAILABLE:
        result = _match_income_engine(
            counterparty=rec.counterparty,
            summary=rec.summary,
            amount=float(rec.credit),
            bank=rec.bank_name,
            company=rec.company,
        )
        income_type  = result.get("income_type", "未匹配")
        source_co    = result.get("source_company") or rec.counterparty or ""
        rule_id      = result.get("rule_id", "")
        return IncomeClassifiedRecord(rec, income_type, source_co, rule_id)

    # ── 回退：旧关键词规则（兼容模式）────────────────────────────────────
    key = exact_key_from_record(rec)
    if key in rules.exact:
        it, co = rules.exact[key]
        return IncomeClassifiedRecord(rec, it, co or rec.counterparty, key)

    text = compact_text(rec.counterparty) + compact_text(rec.summary) + compact_text(rec.bank_name)
    for pattern, it, co in rules.keyword:
        try:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return IncomeClassifiedRecord(rec, it or "未匹配", co or rec.counterparty, pattern)
        except re.error:
            continue
    return IncomeClassifiedRecord(rec, "未匹配", rec.counterparty or "未分配", "")


def classify_income_records(
    records: list[BankRecord],
    rules: ClassificationRuleSet,
    year: int | None = None,
) -> list[IncomeClassifiedRecord]:
    """批量分类贷方（credit > 0）记录。"""
    items = []
    for rec in records:
        if rec.credit <= 0:
            continue
        if year is not None and rec.trade_date.year != year:
            continue
        items.append(classify_income_record(rec, rules))
    return items


def is_income_intragroup(item: IncomeClassifiedRecord) -> bool:
    return item.income_type in INTRAGROUP_INCOME_TYPES


def is_income_unmatched(item: IncomeClassifiedRecord) -> bool:
    return item.income_type == "未匹配"


# ── 收入报表 Sheet 构建函数 ──────────────────────────────────────────────────

def build_annual_income_overview_sheet(
    wb: Workbook,
    items: list[IncomeClassifiedRecord],
    year: int,
    source_count: int,
) -> None:
    """全年收入总览 Sheet（结构对称于支出全年总览）。"""
    ws = wb.create_sheet("全年总览（收入）")
    total         = sum((i.record.credit for i in items), Decimal("0"))
    intra_items   = [i for i in items if is_income_intragroup(i)]
    intra_total   = sum((i.record.credit for i in intra_items), Decimal("0"))
    net_total     = total - intra_total
    unm_items     = [i for i in items if is_income_unmatched(i)]
    unm_total     = sum((i.record.credit for i in unm_items), Decimal("0"))
    dates         = [i.record.trade_date for i in items]
    generated_at  = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    MAX_COL = 8
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=MAX_COL)
    tc = ws.cell(1, 1, f"{year}年银行收入全年统计")
    tc.font      = Font(bold=True, size=16, color=_C_WHITE, name="微软雅黑")
    tc.fill      = PatternFill("solid", fgColor=_C_NAVY)
    tc.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    _ifill  = PatternFill("solid", fgColor=_C_LBLUE)
    _ifl    = Font(bold=True, size=10, color=_C_NAVY, name="微软雅黑")
    _ifv    = Font(size=10, color=_C_NAVY, name="微软雅黑")
    info = [
        ("交易起始日期",     min(dates).strftime("%Y-%m-%d")),
        ("交易截止日期",     max(dates).strftime("%Y-%m-%d")),
        ("文件生成时间",     generated_at),
        ("处理文件数量",     f"{source_count} 个"),
        ("总收入金额（元）", f"{decimal_to_float(total):,.2f}"),
        ("未匹配金额（元）", f"{decimal_to_float(unm_total):,.2f}"),
    ]
    for rn, (label, value) in enumerate(info, start=2):
        ws.cell(rn, 1, label).font = _ifl
        ws.cell(rn, 1).fill       = _ifill
        ws.cell(rn, 1).alignment  = Alignment(horizontal="right", vertical="center")
        ws.cell(rn, 1).border     = _BORDER_THIN
        ws.merge_cells(start_row=rn, start_column=2, end_row=rn, end_column=MAX_COL)
        vc = ws.cell(rn, 2, value)
        vc.font = _ifv; vc.fill = _ifill
        vc.alignment = Alignment(horizontal="left", vertical="center")
        vc.border = _BORDER_THIN
        ws.row_dimensions[rn].height = 18
    ws.row_dimensions[8].height = 6

    start = 9
    summary_rows = [
        ("总收入金额",            total,     len(items)),
        ("  其中：集团内往来款",  intra_total, len(intra_items)),
        ("扣除集团内往来款后净收入", net_total, len(items) - len(intra_items)),
        ("已完整匹配金额",        total - unm_total, len(items) - len(unm_items)),
        ("未匹配金额",            unm_total, len(unm_items)),
    ]
    ws.cell(start, 1, "指标")
    ws.cell(start, 2, "金额\n（元）")
    ws.cell(start, 3, "金额\n（万元）")
    ws.cell(start, 4, "笔数")
    for offset, (label, amount, count) in enumerate(summary_rows, start=1):
        r = start + offset
        ws.cell(r, 1, label)
        ws.cell(r, 2, decimal_to_float(amount))
        ws.cell(r, 3, decimal_to_float(quantize_wan(amount)))
        ws.cell(r, 4, count)

    month_start = start + len(summary_rows) + 4
    ws.cell(month_start, 1, "月份")
    ws.cell(month_start, 2, "总收入\n（元）")
    ws.cell(month_start, 3, "总笔数")
    ws.cell(month_start, 4, "集团内往来款\n（元）")
    ws.cell(month_start, 5, "扣除集团内往来款\n净收入（元）")
    ws.cell(month_start, 6, "已完整匹配\n（元）")
    ws.cell(month_start, 7, "未匹配\n（元）")
    ws.cell(month_start, 8, "未匹配笔数")
    for offset, month in enumerate(sorted({i.record.trade_date.month for i in items}), start=1):
        mi = [i for i in items if i.record.trade_date.month == month]
        mt = sum((i.record.credit for i in mi), Decimal("0"))
        mu = [i for i in mi if is_income_unmatched(i)]
        mig = sum((i.record.credit for i in mi if is_income_intragroup(i)), Decimal("0"))
        r = month_start + offset
        ws.cell(r, 1, month)
        ws.cell(r, 2, decimal_to_float(mt))
        ws.cell(r, 3, len(mi))
        ws.cell(r, 4, decimal_to_float(mig))
        ws.cell(r, 5, decimal_to_float(mt - mig))
        ws.cell(r, 6, decimal_to_float(mt - sum((i.record.credit for i in mu), Decimal("0"))))
        ws.cell(r, 7, decimal_to_float(sum((i.record.credit for i in mu), Decimal("0"))))
        ws.cell(r, 8, len(mu))

    ws.column_dimensions["A"].width = 26
    for col in range(2, 9):
        ws.column_dimensions[get_column_letter(col)].width = 18
    style_range(ws)


def build_income_matrix_sheet(
    wb: Workbook,
    title: str,
    items: list[IncomeClassifiedRecord],
    key_func,
) -> None:
    """
    收入矩阵汇总表（公司月度汇总收入 / 收入类型汇总 / 来源公司汇总）。
    结构对称于 build_month_matrix_sheet。
    """
    ws = wb.create_sheet(title)
    months = sorted({i.record.trade_date.month for i in items})
    keys   = sorted({key_func(i) or "未识别" for i in items})
    ws.cell(1, 1, "月份")
    for col, key in enumerate(keys, start=2):
        ws.cell(1, col, f"{key}\n（万元）")
    total_col = len(keys) + 2
    ws.cell(1, total_col, "汇总\n（万元）")

    col_totals  = {k: Decimal("0") for k in keys}
    intra_totals = {k: Decimal("0") for k in keys}
    grand       = Decimal("0")

    for rn, month in enumerate(months, start=2):
        ws.cell(rn, 1, month)
        mt = Decimal("0")
        for col, key in enumerate(keys, start=2):
            v = sum(
                (i.record.credit for i in items
                 if i.record.trade_date.month == month and (key_func(i) or "未识别") == key),
                Decimal("0"),
            )
            iv = sum(
                (i.record.credit for i in items
                 if i.record.trade_date.month == month
                 and (key_func(i) or "未识别") == key
                 and is_income_intragroup(i)),
                Decimal("0"),
            )
            col_totals[key]  += v
            intra_totals[key] += iv
            mt += v
            ws.cell(rn, col, decimal_to_float(quantize_wan(v)))
        grand += mt
        ws.cell(rn, total_col, decimal_to_float(quantize_wan(mt)))

    total_row = len(months) + 2
    ws.cell(total_row, 1, "合计")
    for col, key in enumerate(keys, start=2):
        ws.cell(total_row, col, decimal_to_float(quantize_wan(col_totals[key])))
    ws.cell(total_row, total_col, decimal_to_float(quantize_wan(grand)))

    intra_row = total_row + 1
    ws.cell(intra_row, 1, "  其中：集团内往来款")
    for col, key in enumerate(keys, start=2):
        v = intra_totals[key]
        if v:
            ws.cell(intra_row, col, decimal_to_float(quantize_wan(v)))
    intra_grand = sum(intra_totals.values())
    if intra_grand:
        ws.cell(intra_row, total_col, decimal_to_float(quantize_wan(intra_grand)))

    net_row = intra_row + 1
    ws.cell(net_row, 1, "扣除集团内往来款后净收入")
    for col, key in enumerate(keys, start=2):
        ws.cell(net_row, col, decimal_to_float(quantize_wan(col_totals[key] - intra_totals[key])))
    ws.cell(net_row, total_col, decimal_to_float(quantize_wan(grand - intra_grand)))

    ws.column_dimensions["A"].width = 28
    for col in range(2, total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 14
    style_range(ws)


def build_month_income_summary_sheet(wb: Workbook, month: int, items: list[IncomeClassifiedRecord]) -> None:
    """月度收入汇总（按公司×收入类型），对称于 build_month_summary_sheet。"""
    ws = wb.create_sheet(f"{month}月收入汇总")
    income_types = sorted({i.income_type for i in items if i.income_type != "未匹配"})
    ws.cell(1, 1, "公司名称")
    for col, it in enumerate(income_types, start=2):
        ws.cell(1, col, f"{it}\n（元）")
    total_col = len(income_types) + 2
    ws.cell(1, total_col, "合计\n（元）")

    companies = sorted({i.record.company for i in items})
    company_totals: dict[str, Decimal] = {}
    type_totals: dict[str, Decimal] = {it: Decimal("0") for it in income_types}
    grand = Decimal("0")

    for rn, company in enumerate(companies, start=2):
        ws.cell(rn, 1, company)
        row_total = Decimal("0")
        for col, it in enumerate(income_types, start=2):
            v = sum(
                (i.record.credit for i in items if i.record.company == company and i.income_type == it),
                Decimal("0"),
            )
            if v:
                ws.cell(rn, col, decimal_to_float(v))
            type_totals[it] += v
            row_total += v
        company_totals[company] = row_total
        ws.cell(rn, total_col, decimal_to_float(row_total))
        grand += row_total

    total_row = len(companies) + 2
    ws.cell(total_row, 1, "合计")
    for col, it in enumerate(income_types, start=2):
        ws.cell(total_row, col, decimal_to_float(type_totals[it]))
    ws.cell(total_row, total_col, decimal_to_float(grand))

    ws.column_dimensions["A"].width = 18
    for col in range(2, total_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 16
    style_range(ws)


def build_month_income_detail_sheet(
    wb: Workbook,
    month: int,
    items: list[IncomeClassifiedRecord],
    unmatched_only: bool = False,
) -> None:
    """月度收入明细（全部或仅未匹配）——与支出明细格式一致。"""
    subset = [i for i in items if is_income_unmatched(i)] if unmatched_only else items
    if not subset:
        return

    sheet_name = f"{month}月收入未匹配" if unmatched_only else f"{month}月收入明细"
    ws = wb.create_sheet(sheet_name)

    # ── 样式（与 run_matching.py 的格式保持一致）──────────────────────────
    FILL_HDR   = PatternFill("solid", fgColor=_C_BLUE)
    FILL_EVEN  = PatternFill("solid", fgColor=_C_STRIPE)
    FILL_AUTO  = PatternFill("solid", fgColor="E2EFDA")   # 自动匹配绿
    FILL_WAWA  = PatternFill("solid", fgColor="FFF2CC")   # 往来款黄
    FILL_UNMATCH = PatternFill("solid", fgColor="FFB3B3") # 未匹配红
    FILL_TOTAL = PatternFill("solid", fgColor="FFC000")

    FNT_HDR  = Font(name="Arial", bold=True, size=10, color=_C_WHITE)
    FNT_BODY = Font(name="Arial", size=10)
    FNT_BOLD = Font(name="Arial", bold=True, size=10)
    AC = Alignment(horizontal="center", vertical="center", wrap_text=True)
    AL = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    AR = Alignment(horizontal="right",  vertical="center")

    headers = ["公司名称", "交易日期", "贷方发生额（元）", "对方名称", "摘要", "银行名称", "收入类型", "来源公司", "规则ID"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.font = FNT_HDR; cell.fill = FILL_HDR
        cell.alignment = AC; cell.border = _BORDER_THIN
    ws.row_dimensions[1].height = 22

    total_amt = 0.0
    for row_idx, i in enumerate(subset, 2):
        rec = i.record
        amt = decimal_to_float(rec.credit)
        total_amt += float(amt)

        if i.income_type == "往来款":
            type_fill = FILL_WAWA
        elif is_income_unmatched(i):
            type_fill = FILL_UNMATCH
        else:
            type_fill = FILL_AUTO

        row_bg = FILL_EVEN if row_idx % 2 == 0 else PatternFill(fill_type=None)

        values = [
            rec.company, rec.trade_date.isoformat(), amt,
            rec.counterparty or "", rec.summary or "",
            rec.bank_name, i.income_type, i.source_company or "", i.match_note or "",
        ]
        for c_idx, val in enumerate(values, 1):
            cell = ws.cell(row_idx, c_idx, val)
            cell.font = FNT_BODY
            cell.border = _BORDER_THIN
            if c_idx == 3:
                cell.number_format = _NUM_FMT
                cell.alignment = AR
            elif c_idx in [4, 5]:
                cell.alignment = AL
            else:
                cell.alignment = AC
            # 收入类型和来源公司用颜色标注
            if c_idx in [7, 8]:
                cell.fill = type_fill
            else:
                cell.fill = row_bg
        ws.row_dimensions[row_idx].height = 18

    # 合计行
    total_row = len(subset) + 2
    ws.merge_cells(f"A{total_row}:B{total_row}")
    for c in range(1, 10):
        cell = ws.cell(total_row, c)
        cell.font = FNT_BOLD; cell.fill = FILL_TOTAL
        cell.alignment = AC; cell.border = _BORDER_THIN
    ws.cell(total_row, 1, f"合计（{len(subset)}条）")
    ws.cell(total_row, 3, total_amt)
    ws.cell(total_row, 3).number_format = _NUM_FMT
    ws.cell(total_row, 3).alignment = AR
    ws.row_dimensions[total_row].height = 22

    col_widths = [12, 11, 16, 26, 30, 20, 18, 20, 10]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


# ── 各账户余额 Sheet（月度期初/期末，动态从流水推导）────────────────────────

def build_balance_sheet_monthly(wb: Workbook, records: list[BankRecord], year: int) -> None:
    """
    生成"各账户余额"Sheet（月度版）。

    逻辑：
      期初余额 = 当月第一笔流水的 balance 字段（该月首笔交易后账面余额）
      期末余额 = 当月最后一笔流水的 balance 字段（该月末笔交易后账面余额）
      期末余额自动成为次月期初余额，故列布局为：
        M1期初 | M1期末 | M2期末 | M3期末 | … | MN期末

    不依赖硬编码文件名或账户清单，完全从 records 动态推导。
    若某账户无 balance 数据（.xls 格式不含余额列）则显示"无余额数据"。
    """
    if "各账户余额" in wb.sheetnames:
        del wb["各账户余额"]

    # ── 按年过滤，分组 ──────────────────────────────────────────────────────
    year_recs = [r for r in records if r.trade_date.year == year]
    if not year_recs:
        return

    from collections import defaultdict
    # key = (company, bank_name); value = sorted list of records
    groups: dict[tuple[str, str], list[BankRecord]] = defaultdict(list)
    for r in year_recs:
        groups[(r.company, r.bank_name)].append(r)
    for key in groups:
        groups[key].sort(key=lambda r: (r.trade_date, r.source_row))

    # 确定有数据的月份
    months_in_data = sorted(set(r.trade_date.month for r in year_recs))
    if not months_in_data:
        return
    m_first = months_in_data[0]

    # ── 预计算各账户各月期初/期末 ────────────────────────────────────────────
    def _month_balance(recs: list[BankRecord], month: int) -> tuple:
        """返回 (期初余额, 期末余额)；无数据返回 (None, None)。"""
        mo_recs = [r for r in recs if r.trade_date.month == month]
        if not mo_recs:
            return (None, None)
        open_bal  = mo_recs[0].balance   # 首笔后余额
        close_bal = mo_recs[-1].balance  # 末笔后余额
        return (open_bal if (open_bal is not None and open_bal > 0) else None,
                close_bal if (close_bal is not None and close_bal > 0) else None)

    # ── 公司排序（按预定顺序，未知公司排末尾）───────────────────────────────
    _CO_ORDER = [
        "传统文化", "健康科技", "健康管理", "利从", "医疗集团",
        "南山分公司", "建筑公司", "玉娇美健康", "玉娇美（化妆品）",
        "生众", "科技", "云科技", "致远", "鸿明", "创投",
    ]
    def _co_rank(co: str) -> int:
        for i, name in enumerate(_CO_ORDER):
            if name in co:
                return i
        return len(_CO_ORDER)

    sorted_keys = sorted(groups.keys(), key=lambda k: (_co_rank(k[0]), k[0], k[1]))

    # ── 样式 ──────────────────────────────────────────────────────────────
    FILL_TITLE  = PatternFill("solid", fgColor=_C_NAVY)
    FILL_HDR    = PatternFill("solid", fgColor=_C_BLUE)
    FILL_TOTAL  = PatternFill("solid", fgColor="FFC000")
    FILL_GRAND  = PatternFill("solid", fgColor=_C_NAVY)
    FILL_HAS    = PatternFill("solid", fgColor="E2EFDA")   # 有数据：绿
    FILL_MISS   = PatternFill("solid", fgColor="F2F2F2")   # 无数据：灰
    FILL_CO     = PatternFill("solid", fgColor=_C_LBLUE)   # 公司小计：浅蓝

    FNT_TITLE = Font(name="Arial", bold=True, size=13, color=_C_WHITE)
    FNT_HDR   = Font(name="Arial", bold=True, size=10, color=_C_WHITE)
    FNT_BODY  = Font(name="Arial", size=10)
    FNT_MISS  = Font(name="Arial", size=10, color="808080", italic=True)
    FNT_TOTAL = Font(name="Arial", bold=True, size=10)
    FNT_GRAND = Font(name="Arial", bold=True, size=11, color=_C_WHITE)
    FNT_SRC   = Font(name="Arial", size=9,  color="595959")

    AC  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    AL  = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    AR  = Alignment(horizontal="right",  vertical="center")
    NUM = "#,##0.00;(#,##0.00);\"-\""

    # ── 列结构：固定列 + 月度数据列 ─────────────────────────────────────────
    # 固定列：A=公司, B=银行账户, C=来源文件
    # 数据列：[M1期初, M1期末, M2期末, …, MN期末]
    FIXED_COLS = 3
    # 列名：首月 期初+期末，其余月只加期末（因期末=次月期初）
    data_col_labels: list[str] = []
    data_col_months: list[tuple[int, str]] = []  # (month, "open"|"close")
    for idx, m in enumerate(months_in_data):
        if idx == 0:
            data_col_labels.append(f"{m}月期初余额\n（元）")
            data_col_months.append((m, "open"))
        data_col_labels.append(f"{m}月期末余额\n（元）")
        data_col_months.append((m, "close"))

    total_cols = FIXED_COLS + len(data_col_labels)
    last_col_letter = get_column_letter(total_cols)

    ws = wb.create_sheet("各账户余额", 0)

    # 行1：大标题
    ws.merge_cells(f"A1:{last_col_letter}1")
    title_months = (
        f"{m_first}月–{months_in_data[-1]}月" if len(months_in_data) > 1
        else f"{m_first}月"
    )
    ws["A1"] = f"各账户余额汇总（{year}年 {title_months}）"
    ws["A1"].font = FNT_TITLE; ws["A1"].fill = FILL_TITLE
    ws["A1"].alignment = AC
    ws.row_dimensions[1].height = 32

    # 行2：列表头
    fixed_hdrs = ["公司名称", "银行账户", "来源文件"]
    for c, h in enumerate(fixed_hdrs + data_col_labels, 1):
        cell = ws.cell(2, c, h)
        cell.font = FNT_HDR; cell.fill = FILL_HDR
        cell.alignment = AC; cell.border = _BORDER_THIN
    ws.row_dimensions[2].height = 44

    # 列宽
    col_widths = [14, 22, 26] + [13] * len(data_col_labels)
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── 数据行 ────────────────────────────────────────────────────────────
    cur_row  = 3
    prev_co  = None
    co_rows: list[int] = []          # 行号，供合计行 SUM 公式引用
    all_data_rows: list[int] = []

    def _flush_company_total(company: str, rows: list[int], r: int) -> None:
        """写公司小计行。"""
        ws.merge_cells(f"A{r}:C{r}")
        ws.cell(r, 1, f"{company} 合计")
        for c in range(1, total_cols + 1):
            cell = ws.cell(r, c)
            cell.font = FNT_TOTAL; cell.fill = FILL_TOTAL
            cell.border = _BORDER_THIN; cell.alignment = AC
        for col_i in range(FIXED_COLS + 1, total_cols + 1):
            col_l = get_column_letter(col_i)
            refs = "+".join(f"IFERROR({col_l}{dr}*1,0)" for dr in rows)
            ws.cell(r, col_i).value = f"={refs}"
            ws.cell(r, col_i).number_format = NUM
            ws.cell(r, col_i).alignment = AR
        ws.row_dimensions[r].height = 20

    for (company, bank) in sorted_keys:
        recs = groups[(company, bank)]

        # 公司小计行（公司变化时）
        if prev_co is not None and company != prev_co:
            _flush_company_total(prev_co, co_rows, cur_row)
            cur_row += 1
            co_rows = []

        # 数据行
        row = cur_row
        all_data_rows.append(row)
        co_rows.append(row)

        source = recs[0].source_file if recs else ""

        ws.cell(row, 1, company).font = FNT_BODY
        ws.cell(row, 1).alignment = AC; ws.cell(row, 1).border = _BORDER_THIN

        ws.cell(row, 2, bank).font = FNT_BODY
        ws.cell(row, 2).alignment = AL; ws.cell(row, 2).border = _BORDER_THIN

        ws.cell(row, 3, source).font = FNT_SRC
        ws.cell(row, 3).alignment = AL; ws.cell(row, 3).border = _BORDER_THIN

        # 月度余额列
        month_cache: dict[int, tuple] = {}
        for m in months_in_data:
            month_cache[m] = _month_balance(recs, m)

        for col_offset, (m, kind) in enumerate(data_col_months, FIXED_COLS + 1):
            open_b, close_b = month_cache[m]
            val = open_b if kind == "open" else close_b
            cell = ws.cell(row, col_offset)
            if val is not None:
                cell.value = float(val)
                cell.fill  = FILL_HAS
                cell.font  = FNT_BODY
                cell.number_format = NUM
                cell.alignment = AR
            else:
                cell.value = "无余额数据"
                cell.fill  = FILL_MISS
                cell.font  = FNT_MISS
                cell.alignment = AC
            cell.border = _BORDER_THIN

        ws.row_dimensions[row].height = 20
        prev_co = company
        cur_row += 1

    # 最后一个公司的合计行
    if co_rows and prev_co is not None:
        _flush_company_total(prev_co, co_rows, cur_row)
        cur_row += 1

    # 总计行
    total_row = cur_row
    ws.merge_cells(f"A{total_row}:C{total_row}")
    ws.cell(total_row, 1, "总　计")
    for c in range(1, total_cols + 1):
        cell = ws.cell(total_row, c)
        cell.font = FNT_GRAND; cell.fill = FILL_GRAND
        cell.border = _BORDER_THIN; cell.alignment = AC
    for col_i in range(FIXED_COLS + 1, total_cols + 1):
        col_l = get_column_letter(col_i)
        refs = "+".join(f"IFERROR({col_l}{dr}*1,0)" for dr in all_data_rows)
        ws.cell(total_row, col_i).value = f"={refs}"
        ws.cell(total_row, col_i).number_format = NUM
        ws.cell(total_row, col_i).alignment = AR
    ws.row_dimensions[total_row].height = 26

    # 说明行
    note_row = total_row + 2
    ws.merge_cells(f"A{note_row}:{last_col_letter}{note_row}")
    ws.cell(note_row, 1,
        "【说明】绿色底色：余额从银行流水 balance 字段自动提取。"
        "灰色[无余额数据]：该银行文件格式不含余额列（如农行.xls），需手动补录。"
        "期末余额即为次月期初余额，如需验证可与银行对账单核对。"
    )
    ws.cell(note_row, 1).font = Font(name="Arial", size=9, italic=True, color="595959")
    ws.cell(note_row, 1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[note_row].height = 32

    ws.freeze_panes = "A3"


# ── 旧版：各账户余额 Sheet（简版，保留供兼容）────────────────────────────────

def build_balance_sheet(wb: Workbook, records: list[BankRecord]) -> None:
    """
    生成"各账户余额"Sheet（简版）。
    从每个（公司, 银行）账户的流水记录中，取 balance > 0 的最后一条记录的余额；
    若所有记录 balance == 0（银行文件不含余额列），则展示"-"。
    """
    ws = wb.create_sheet("各账户余额", 0)   # 插到第一个 Sheet 位置

    # 按 (公司, 银行) 分组，找最新余额（按 trade_date + source_row 排序取最后一条）
    account_last: dict[tuple[str, str], BankRecord] = {}
    for rec in records:
        key = (rec.company, rec.bank_name)
        prev = account_last.get(key)
        if prev is None:
            account_last[key] = rec
        elif (rec.trade_date, rec.source_row) > (prev.trade_date, prev.source_row):
            account_last[key] = rec

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    tc = ws.cell(1, 1, "各账户当前余额汇总")
    tc.font      = Font(bold=True, size=14, color=_C_WHITE, name="微软雅黑")
    tc.fill      = PatternFill("solid", fgColor=_C_NAVY)
    tc.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.append(["公司名称", "银行账户", "来源文件", "最后交易日期", "账户余额（元）"])

    total_balance = Decimal("0")
    for (company, bank), rec in sorted(account_last.items()):
        bal = rec.balance
        ws.append([
            company,
            bank,
            rec.source_file,
            rec.trade_date.isoformat(),
            decimal_to_float(bal) if bal > 0 else "-",
        ])
        if bal > 0:
            total_balance += bal

    ws.append(["合计", "", "", "", decimal_to_float(total_balance) if total_balance > 0 else "-"])

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 18
    ws.freeze_panes = "A3"
    style_range(ws)


# ── 收入匹配汇总 Sheet ────────────────────────────────────────────────────────

def build_income_match_summary_sheet(
    wb: Workbook,
    items: list[IncomeClassifiedRecord],
    month_label: str = "4月",
) -> None:
    """
    生成"收入匹配汇总"Sheet：
      一、按收入类型（笔数 / 金额 / 占比）
      二、按收款公司（笔数 / 金额 / 占比）
    """
    ws = wb.create_sheet("收入匹配汇总")

    # 仅统计指定月份（从 month_label 解析月份数字）
    month_num = int(month_label.replace("月", "").strip()) if "月" in month_label else None
    if month_num:
        scope = [i for i in items if i.record.trade_date.month == month_num]
    else:
        scope = items

    # ── 样式 ──────────────────────────────────────────────────────────────
    FILL_TITLE  = PatternFill("solid", fgColor=_C_NAVY)
    FILL_HDR    = PatternFill("solid", fgColor=_C_BLUE)
    FILL_TOTAL  = PatternFill("solid", fgColor="FFC000")   # gold
    FILL_SEC    = PatternFill("solid", fgColor=_C_LBLUE)   # 节标题浅蓝底
    FILL_WAWA   = PatternFill("solid", fgColor="FFF2CC")   # 往来款浅黄
    FILL_AUTO   = PatternFill("solid", fgColor=_C_GREEN)   # 自动匹配浅绿
    FILL_UNMATCH= PatternFill("solid", fgColor="FFB3B3")   # 未匹配浅红

    FNT_TITLE   = Font(name="微软雅黑", bold=True, size=13, color=_C_WHITE)
    FNT_HDR     = Font(name="微软雅黑", bold=True, size=10, color=_C_WHITE)
    FNT_SEC     = Font(name="微软雅黑", bold=True, size=10, color=_C_NAVY)
    FNT_BODY    = Font(name="微软雅黑", size=10)
    FNT_TOTAL   = Font(name="微软雅黑", bold=True, size=10)

    AC = Alignment(horizontal="center", vertical="center", wrap_text=True)
    AL = Alignment(horizontal="left",   vertical="center")
    AR = Alignment(horizontal="right",  vertical="center")

    def _c(row, col, val=None, font=None, fill=None, align=None, fmt=None, border=True):
        cell = ws.cell(row, col)
        if val is not None:
            cell.value = val
        if font:  cell.font  = font
        if fill:  cell.fill  = fill
        if align: cell.alignment = align
        if fmt:   cell.number_format = fmt
        if border:
            cell.border = _BORDER_THIN
        return cell

    # ── 标题行 ──────────────────────────────────────────────────────────
    ws.merge_cells("A1:F1")
    _c(1, 1, f"{month_label}收入自动匹配汇总", font=FNT_TITLE, fill=FILL_TITLE, align=AC, border=False)
    ws.row_dimensions[1].height = 32

    # ── 基础统计 ──────────────────────────────────────────────────────────
    from collections import defaultdict
    type_stats: dict[str, dict] = defaultdict(lambda: {"cnt": 0, "amt": 0.0})
    co_stats:   dict[str, dict] = defaultdict(lambda: {"cnt": 0, "amt": 0.0})
    for i in scope:
        typ = i.income_type or "未匹配"
        amt = float(i.record.credit)
        type_stats[typ]["cnt"] += 1
        type_stats[typ]["amt"] += amt
        co  = i.record.company or "未识别"
        co_stats[co]["cnt"]  += 1
        co_stats[co]["amt"]  += amt

    total_cnt = sum(v["cnt"] for v in type_stats.values())
    total_amt = sum(v["amt"] for v in type_stats.values())

    # ══════════════════════════════════════════════════════════════════════
    # 一、按收入类型
    # ══════════════════════════════════════════════════════════════════════
    r = 2
    ws.merge_cells(f"A{r}:F{r}")
    _c(r, 1, "一、按收入类型", font=FNT_SEC, fill=FILL_SEC, align=AL, border=False)
    ws.row_dimensions[r].height = 22
    r += 1

    hdrs = ["收入类型", "笔数", "金额（元）", "占比（笔数）", "占比（金额）", "备注"]
    for c, h in enumerate(hdrs, 1):
        _c(r, c, h, font=FNT_HDR, fill=FILL_HDR, align=AC)
    ws.row_dimensions[r].height = 22
    r += 1

    sorted_types = sorted(type_stats.items(), key=lambda x: -x[1]["amt"])
    for typ, v in sorted_types:
        cnt = v["cnt"]; amt = v["amt"]
        pct_cnt = cnt / total_cnt if total_cnt else 0
        pct_amt = amt / total_amt if total_amt else 0
        if typ == "往来款":
            row_fill = FILL_WAWA
        elif typ == "未匹配":
            row_fill = FILL_UNMATCH
        else:
            row_fill = FILL_AUTO
        _c(r, 1, typ,     font=FNT_BODY, fill=row_fill, align=AL)
        _c(r, 2, cnt,     font=FNT_BODY, fill=row_fill, align=AC)
        _c(r, 3, amt,     font=FNT_BODY, fill=row_fill, align=AR, fmt=_NUM_FMT)
        _c(r, 4, pct_cnt, font=FNT_BODY, fill=row_fill, align=AC, fmt="0.0%")
        _c(r, 5, pct_amt, font=FNT_BODY, fill=row_fill, align=AC, fmt="0.0%")
        _c(r, 6, "",      font=FNT_BODY, fill=row_fill, align=AL)
        ws.row_dimensions[r].height = 18
        r += 1

    # 合计行
    _c(r, 1, "合计",    font=FNT_TOTAL, fill=FILL_TOTAL, align=AC)
    _c(r, 2, total_cnt, font=FNT_TOTAL, fill=FILL_TOTAL, align=AC)
    _c(r, 3, total_amt, font=FNT_TOTAL, fill=FILL_TOTAL, align=AR, fmt=_NUM_FMT)
    _c(r, 4, 1.0,       font=FNT_TOTAL, fill=FILL_TOTAL, align=AC, fmt="0.0%")
    _c(r, 5, 1.0,       font=FNT_TOTAL, fill=FILL_TOTAL, align=AC, fmt="0.0%")
    _c(r, 6, "",        font=FNT_TOTAL, fill=FILL_TOTAL, align=AL)
    ws.row_dimensions[r].height = 22
    r += 2  # 空一行

    # ══════════════════════════════════════════════════════════════════════
    # 二、按收款公司
    # ══════════════════════════════════════════════════════════════════════
    ws.merge_cells(f"A{r}:D{r}")
    _c(r, 1, "二、按收款公司", font=FNT_SEC, fill=FILL_SEC, align=AL, border=False)
    ws.row_dimensions[r].height = 22
    r += 1

    hdrs2 = ["公司名称", "笔数", "金额（元）", "占比（金额）"]
    for c, h in enumerate(hdrs2, 1):
        _c(r, c, h, font=FNT_HDR, fill=FILL_HDR, align=AC)
    ws.row_dimensions[r].height = 22
    r += 1

    sorted_cos = sorted(co_stats.items(), key=lambda x: -x[1]["amt"])
    for co, v in sorted_cos:
        amt  = v["amt"]
        pct  = amt / total_amt if total_amt else 0
        _c(r, 1, co,       font=FNT_BODY, fill=FILL_AUTO, align=AL)
        _c(r, 2, v["cnt"], font=FNT_BODY, fill=FILL_AUTO, align=AC)
        _c(r, 3, amt,      font=FNT_BODY, fill=FILL_AUTO, align=AR, fmt=_NUM_FMT)
        _c(r, 4, pct,      font=FNT_BODY, fill=FILL_AUTO, align=AC, fmt="0.0%")
        ws.row_dimensions[r].height = 18
        r += 1

    # ── 列宽 ──────────────────────────────────────────────────────────────
    col_widths = [26, 8, 18, 12, 12, 14]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A4"


# ── 各账户余额（完整版，含期初/期末余额）────────────────────────────────────

# 定义所有账户行（公司, 账户名, 来源文件, 是否合计行）
_BALANCE_ROWS = [
    ("传统文化",         "传统文化光大基本户",        "传统文化光大 3-4.30.xls",            False),
    ("传统文化",         "传统文化招行一般户",         "传统招商 3-4.30.xlsx",               False),
    ("传统文化合计",     None,                        None,                                 True),
    ("健康科技",         "健康科技农行基本户",         "健康科技农行 3-4.30.xls",             False),
    ("健康科技合计",     None,                        None,                                 True),
    ("健康管理",         "健康招商",                  "健康招商 3-4.30.xlsx",               False),
    ("健康管理",         "健康管理光大",              "健康光大 3-4.30.xls",                False),
    ("健康管理",         "健康管理农行华润城支行",     "健康农行 6906   3-4.30.xls",          False),
    ("健康管理",         "健康管理农行基本户",         "健康农行 6411 3-4.30.xls",           False),
    ("健康管理",         "普济招商基本户",             "吉林普济招商 3-4.30.xlsx",            False),
    ("健康管理合计",     None,                        None,                                 True),
    ("利从",             "利从招行基本户",             "利从招商3-4.30.xlsx",                False),
    ("利从合计",         None,                        None,                                 True),
    ("医疗集团",         "医疗集团光大",              "医疗光大 3-4.30.xls",                False),
    ("医疗集团",         "医疗集团招行基本户",         "医疗招商 3-4.30.xlsx",               False),
    ("医疗集团合计",     None,                        None,                                 True),
    ("南山分公司",       "南山光大基本户",             "南山光大 3-4.29.xls",                False),
    ("南山分公司合计",   None,                        None,                                 True),
    ("建筑公司",         "建筑招行基本户",             "建筑公司 3-4.30.xlsx",               False),
    ("建筑公司合计",     None,                        None,                                 True),
    ("玉娇美健康",       "玉娇美健康账户",             "玉娇美健康3-4.30.xls",               False),
    ("玉娇美健康合计",   None,                        None,                                 True),
    ("玉娇美（化妆品）", "平安银行基本户",             "玉娇美化妆品平安 3-4.30.xls",         False),
    ("玉娇美（化妆品）合计", None,                    None,                                 True),
    ("生众",             "生众招行基本户",             "生众 招商 3-4.30.xlsx",              False),
    ("生众合计",         None,                        None,                                 True),
    ("科技",             "云科技招行",                "云科技招商 3-4.30.xlsx",              False),
    ("科技",             "科技光大一般户",             "科技光大 3-4.30.xls",                False),
    ("科技",             "科技招行一般户",             "科技 招商一般户科发   3-4.30.xlsx",   False),
    ("科技",             "科技招行基本户",             "科技 招商基本户10201   3-4.30.xlsx",  False),
    ("科技合计",         None,                        None,                                 True),
    ("致远",             "致远中国银行",               "致远3-4.30.xls",                     False),
    ("致远合计",         None,                        None,                                 True),
    ("鸿明",             "鸿明银行",                   "鸿明3-4.30.xlsx",                    False),
    ("鸿明合计",         None,                        None,                                 True),
]


def _extract_cmb_xlsx_balances(path: Path) -> dict | None:
    """从招商银行xlsx格式对账单中提取期初余额、3月期末余额、4月期末余额。"""
    try:
        wb_src = openpyxl.load_workbook(path, data_only=True)
        ws_src = wb_src.active
        all_rows = list(ws_src.iter_rows(values_only=True))
    except Exception:
        return None

    # 找数据表头行（含'账号', '交易日', '余额'）
    data_header_row = None
    balance_col = date_col = None
    for i, row in enumerate(all_rows):
        flat = [str(v).strip() if v is not None else "" for v in row]
        if "账号" in flat and "交易日" in flat and "余额" in flat:
            data_header_row = i
            for j, v in enumerate(row):
                if v is not None and str(v).strip() == "余额":
                    balance_col = j
                if v is not None and "交易日" in str(v):
                    date_col = j
            break

    # 解析元数据（仅在数据表头行之前）
    meta: dict = {}
    meta_end = data_header_row if data_header_row is not None else len(all_rows)
    for i in range(meta_end):
        row = all_rows[i]
        j = 0
        while j < len(row):
            if row[j] is not None and str(row[j]).strip():
                key = str(row[j]).strip()
                val = None
                for k in range(j + 1, len(row)):
                    if row[k] is not None and str(row[k]).strip():
                        val = row[k]
                        break
                meta[key] = val
            j += 1

    def _to_float(v) -> float | None:
        try:
            return float(str(v).replace(",", "")) if v is not None else None
        except Exception:
            return None

    period_open  = _to_float(meta.get("对账单期初余额"))
    period_close = _to_float(meta.get("对账单余额"))

    # 3月期末余额：最后一笔3月流水的余额
    mar_end = None
    if data_header_row is not None and balance_col is not None and date_col is not None:
        for row in all_rows[data_header_row + 1:]:
            date_val = row[date_col]
            bal_val  = row[balance_col]
            if date_val is None or bal_val is None:
                continue
            if isinstance(date_val, dt.datetime):
                yr, mo = date_val.year, date_val.month
            elif isinstance(date_val, dt.date):
                yr, mo = date_val.year, date_val.month
            else:
                try:
                    parts = str(date_val).strip().split("-")
                    yr, mo = int(parts[0]), int(parts[1])
                except Exception:
                    continue
            try:
                bal_f = float(str(bal_val).replace(",", ""))
            except Exception:
                continue
            if yr == 2026 and mo == 3:
                mar_end = bal_f

    return {"mar_open": period_open, "mar_close": mar_end, "apr_close": period_close}


def build_balance_sheet_full(wb: Workbook, input_dir: Path) -> None:
    """
    生成完整版"各账户余额"Sheet（10列）：
      A 公司名称 | B 银行账户 | C 来源文件 |
      D 3月期初余额 | E 3月期末余额 | F 4月期末余额（自动提取，绿色）|
      G 4月收入（元）| H 4月支出（元）（黄色，手填）|
      I 验证期末余额 = E + G - H |
      J 差异 = F - I
    """
    if "各账户余额" in wb.sheetnames:
        del wb["各账户余额"]
    ws = wb.create_sheet("各账户余额", 0)

    # 预读所有 xlsx 余额数据
    xlsx_files = list(input_dir.glob("*.xlsx"))
    file_data: dict[str, dict] = {}
    for p in xlsx_files:
        r = _extract_cmb_xlsx_balances(p)
        if r:
            norm = " ".join(p.name.split())
            file_data[norm] = r

    def _lookup(source_file: str | None) -> dict | None:
        if not source_file or not source_file.endswith(".xlsx"):
            return None
        norm = " ".join(source_file.split())
        if norm in file_data:
            return file_data[norm]
        # 容错：空格归一化后匹配
        for k, v in file_data.items():
            if k.replace(" ", "") == norm.replace(" ", ""):
                return v
        return None

    # ── 样式 ──────────────────────────────────────────────────────────────
    FILL_TITLE  = PatternFill("solid", fgColor=_C_NAVY)
    FILL_HDR    = PatternFill("solid", fgColor=_C_BLUE)
    FILL_TOTAL  = PatternFill("solid", fgColor="FFC000")
    FILL_GRAND  = PatternFill("solid", fgColor=_C_NAVY)
    FILL_AUTO   = PatternFill("solid", fgColor="E2EFDA")   # 自动提取绿
    FILL_YELLOW = PatternFill("solid", fgColor="FFFF99")   # 手填黄
    FILL_MISS   = PatternFill("solid", fgColor="F2F2F2")

    FNT_TITLE = Font(name="Arial", bold=True, size=14, color=_C_WHITE)
    FNT_HDR   = Font(name="Arial", bold=True, size=10, color=_C_WHITE)
    FNT_TOTAL = Font(name="Arial", bold=True, size=10)
    FNT_GRAND = Font(name="Arial", bold=True, size=11, color=_C_WHITE)
    FNT_BODY  = Font(name="Arial", size=10)
    FNT_MISS  = Font(name="Arial", size=10, color="808080")
    FNT_SRC   = Font(name="Arial", size=9,  color="595959")

    AC = Alignment(horizontal="center", vertical="center", wrap_text=True)
    AL = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    AR = Alignment(horizontal="right",  vertical="center")
    NUM = "#,##0.00;(#,##0.00);\"-\""

    # ── 行1：大标题 ─────────────────────────────────────────────────────────
    ws.merge_cells("A1:J1")
    ws["A1"] = "各账户余额汇总（3-4月）"
    ws["A1"].font      = FNT_TITLE
    ws["A1"].fill      = FILL_TITLE
    ws["A1"].alignment = AC
    ws.row_dimensions[1].height = 32

    # ── 行2：列表头 ─────────────────────────────────────────────────────────
    HEADERS = [
        "公司名称", "银行账户", "来源文件",
        "3月期初余额\n（元）", "3月期末余额\n（元）", "4月期末余额\n（元）",
        "4月收入\n（元）", "4月支出\n（元）",
        "验证期末余额\n（期初+收入-支出）", "差异\n（实际-验证）",
    ]
    for col, h in enumerate(HEADERS, 1):
        c = ws.cell(2, col, h)
        c.font = FNT_HDR; c.fill = FILL_HDR
        c.alignment = AC; c.border = _BORDER_THIN
    ws.row_dimensions[2].height = 42

    # ── 列宽 ──────────────────────────────────────────────────────────────
    for i, w in enumerate([14, 22, 30, 14, 14, 14, 12, 12, 22, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── 数据行 ────────────────────────────────────────────────────────────
    cur_row = 3
    company_row_map: dict[str, list[int]] = {}   # company → [excel rows]

    for (company, account, source_file, is_total) in _BALANCE_ROWS:
        row = cur_row

        if is_total:
            # 合计行：金色背景，A-C 合并
            ws.merge_cells(f"A{row}:C{row}")
            for c in range(1, 11):
                cell = ws.cell(row, c)
                cell.font   = FNT_TOTAL
                cell.fill   = FILL_TOTAL
                cell.border = _BORDER_THIN
                cell.alignment = AC
            ws.cell(row, 1, company)

            base = company.replace("合计", "").strip()
            data_rows_for_co = company_row_map.get(base, [])
            for col_idx in range(4, 11):
                col_l = get_column_letter(col_idx)
                if data_rows_for_co:
                    refs = "+".join([f"IFERROR({col_l}{r}*1,0)" for r in data_rows_for_co])
                    ws.cell(row, col_idx, f"={refs}")
                else:
                    ws.cell(row, col_idx, 0)
                ws.cell(row, col_idx).number_format = NUM
                ws.cell(row, col_idx).alignment = AR

        else:
            # 数据行
            bal = _lookup(source_file)
            mar_open  = bal["mar_open"]  if bal else None
            mar_close = bal["mar_close"] if bal else None
            apr_close = bal["apr_close"] if bal else None

            # A: 公司名
            ca = ws.cell(row, 1, company)
            ca.font = FNT_BODY; ca.fill = PatternFill(fill_type=None)
            ca.alignment = AC; ca.border = _BORDER_THIN

            # B: 账户名
            cb = ws.cell(row, 2, account)
            cb.font = FNT_BODY; cb.alignment = AL; cb.border = _BORDER_THIN

            # C: 来源文件
            cc = ws.cell(row, 3, source_file)
            cc.font = FNT_SRC; cc.alignment = AL; cc.border = _BORDER_THIN

            # D/E/F：自动提取（绿色）
            for col_idx, val in [(4, mar_open), (5, mar_close), (6, apr_close)]:
                c = ws.cell(row, col_idx)
                if val is not None:
                    c.value = val
                    c.fill  = FILL_AUTO
                    c.font  = FNT_BODY
                    c.number_format = NUM
                    c.alignment = AR
                else:
                    c.value = "数据缺失"
                    c.fill  = FILL_MISS
                    c.font  = FNT_MISS
                    c.alignment = AC
                c.border = _BORDER_THIN

            # G/H：手填（黄色）
            for col_idx in [7, 8]:
                c = ws.cell(row, col_idx)
                c.fill  = FILL_YELLOW
                c.font  = FNT_BODY
                c.border = _BORDER_THIN
                c.alignment = AR
                c.number_format = NUM

            # I：验证期末余额 = E + G - H
            ci = ws.cell(row, 9)
            ci.value = (
                f"=IF(AND(ISNUMBER(E{row}),ISNUMBER(G{row}),ISNUMBER(H{row})),"
                f"E{row}+G{row}-H{row},\"\")"
            )
            ci.font = FNT_BODY; ci.border = _BORDER_THIN
            ci.alignment = AR; ci.number_format = NUM

            # J：差异 = F - I
            cj = ws.cell(row, 10)
            cj.value = f"=IF(AND(ISNUMBER(F{row}),I{row}<>\"\"),F{row}-I{row},\"\")"
            cj.font = FNT_BODY; cj.border = _BORDER_THIN
            cj.alignment = AR; cj.number_format = NUM

            if company not in company_row_map:
                company_row_map[company] = []
            company_row_map[company].append(row)

        ws.row_dimensions[row].height = 20
        cur_row += 1

    # ── 总计行 ─────────────────────────────────────────────────────────────
    total_row = cur_row
    ws.merge_cells(f"A{total_row}:C{total_row}")
    for c in range(1, 11):
        cell = ws.cell(total_row, c)
        cell.font   = FNT_GRAND
        cell.fill   = FILL_GRAND
        cell.border = _BORDER_THIN
        cell.alignment = AC
    ws.cell(total_row, 1, "总　计")

    all_data_rows = [r for rows in company_row_map.values() for r in rows]
    for col_idx in range(4, 11):
        col_l = get_column_letter(col_idx)
        if all_data_rows:
            refs = "+".join([f"IFERROR({col_l}{r}*1,0)" for r in all_data_rows])
            ws.cell(total_row, col_idx, f"={refs}")
        else:
            ws.cell(total_row, col_idx, 0)
        ws.cell(total_row, col_idx).number_format = NUM
        ws.cell(total_row, col_idx).alignment = AR
    ws.row_dimensions[total_row].height = 26

    # ── 说明行 ────────────────────────────────────────────────────────────
    legend_row = total_row + 2
    ws.merge_cells(f"A{legend_row}:J{legend_row}")
    ws.cell(legend_row, 1,
        "【说明】绿色底色：D/E/F列自动从招商银行对账单提取（期初余额/3月期末/4月期末）。"
        "黄色底色（G/H列）：财务手动填写4月收入/4月支出，填写后I列自动验证，J列显示差异。")
    ws.cell(legend_row, 1).font = Font(name="Arial", size=9, italic=True, color="595959")
    ws.cell(legend_row, 1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[legend_row].height = 32

    ws.freeze_panes = "A3"


# ── 收入报表工作簿入口 ────────────────────────────────────────────────────────

def build_annual_income_workbook(
    records: list[BankRecord],
    rules: ClassificationRuleSet,
    year: int,
    source_count: int = 0,
    input_dir: Path | None = None,
) -> Workbook:
    """构建全年收入统计工作簿（对称于 build_annual_workbook）。"""
    items = classify_income_records(records, rules, year)
    wb = Workbook()
    wb.remove(wb.active)

    # 各账户余额（月度期初/期末，动态从流水推导）
    build_balance_sheet_monthly(wb, records, year)

    build_annual_income_overview_sheet(wb, items, year, source_count)
    build_income_matrix_sheet(wb, "公司月度汇总（收入）", items, lambda i: i.record.company)
    build_income_matrix_sheet(wb, "收入类型汇总", items, lambda i: i.income_type)
    build_income_matrix_sheet(wb, "来源公司汇总", items, lambda i: i.source_company or "未识别")

    for month in sorted({i.record.trade_date.month for i in items}):
        month_items = [i for i in items if i.record.trade_date.month == month]
        build_month_income_summary_sheet(wb, month, month_items)
        build_month_income_detail_sheet(wb, month, month_items, unmatched_only=False)
        # 只有存在未匹配时才生成"未匹配"Sheet
        unmatched = [i for i in month_items if is_income_unmatched(i)]
        if unmatched:
            build_month_income_detail_sheet(wb, month, month_items, unmatched_only=True)

    # 收入匹配汇总（取最新月份）
    latest_month = max({i.record.trade_date.month for i in items}, default=4)
    build_income_match_summary_sheet(wb, items, month_label=f"{latest_month}月")

    return wb


def save_annual_income_workbook(wb: Workbook, output_dir: Path, year: int) -> Path:
    """保存全年收入报表，使用 YYYYMMDD_NNN_ 命名规范。"""
    path = next_output_path(output_dir, f"{year}年银行【收入】全年统计.xlsx")
    output_dir.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


# ── v2：运行子目录 + 状态后缀命名 ───────────────────────────────────────────

def next_run_dir(output_dir: Path) -> Path:
    """
    创建并返回本次运行的输出子目录 output/YYYYMMDD_NNN/。

    每次调用 生成报表.py 都会在 output/ 下新建一个带日期流水号的子目录，
    所有本次生成的报表文件统一存放其中，便于追溯每次运行结果。

    示例：output/20260510_001/
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    existing = sorted(output_dir.glob(f"{today}_???"))
    seq = len(existing) + 1
    run_dir = output_dir / f"{today}_{seq:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_expense_workbook_v2(wb: Workbook, run_dir: Path, year: int, status: str = "待完善") -> Path:
    """v2：将支出报表存入运行子目录，文件名含状态后缀（_待完善 / _终稿）。"""
    path = run_dir / f"{year}年银行【支出】全年统计_{status}.xlsx"
    wb.save(path)
    return path


def save_income_workbook_v2(wb: Workbook, run_dir: Path, year: int, status: str = "待完善") -> Path:
    """v2：将收入报表存入运行子目录，文件名含状态后缀（_待完善 / _终稿）。"""
    path = run_dir / f"{year}年银行【收入】全年统计_{status}.xlsx"
    wb.save(path)
    return path



# ── 收入未匹配记录导出（供人工修正）────────────────────────────────────────────

def export_income_unmatched_for_correction(
    items: list[IncomeClassifiedRecord],
    output_dir: Path,
    label: str,
) -> Path | None:
    """
    将收入中未能自动分类的记录导出为待修正工作表。
    财务人员填写"修正收入类型"后，交由 apply_income_corrections.py 写回规则库。
    """
    unmatched = [i for i in items if is_income_unmatched(i)]
    if not unmatched:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "收入未匹配记录_待修正"

    headers = [
        "年份", "月份", "公司名称", "交易日期", "贷方发生额（元）",
        "对方名称", "摘要", "银行名称",
        "当前收入类型", "当前来源公司",
        "修正收入类型",    # ← 财务人员填写
        "修正来源公司",    # ← 财务人员填写（可选）
        "核对备注",        # ← 财务人员填写（可选）
        "_映射键",         # 程序内部列，请勿删除或修改
    ]
    ws.append(headers)

    for i in unmatched:
        rec = i.record
        ws.append([
            str(rec.trade_date.year),
            str(rec.trade_date.month),
            rec.company,
            rec.trade_date.isoformat(),
            decimal_to_float(rec.credit),
            rec.counterparty,
            rec.summary,
            rec.bank_name,
            i.income_type,
            i.source_company,
            "", "", "",
            exact_key_from_record(rec),
        ])

    EDIT_COLS = {11, 12, 13}
    HIDE_COL  = 14

    header_fill   = PatternFill("solid", fgColor=_C_BLUE)
    edit_fill     = PatternFill("solid", fgColor="FFF2CC")
    readonly_fill = PatternFill("solid", fgColor=_C_STRIPE)
    header_font   = Font(bold=True, color=_C_WHITE, size=10, name="微软雅黑")
    data_font     = Font(size=10, name="微软雅黑")

    for row in ws.iter_rows():
        for cell in row:
            col = cell.column
            cell.border    = _BORDER_THIN
            cell.alignment = Alignment(vertical="center", wrap_text=True,
                                       horizontal="right" if isinstance(cell.value, (int, float)) else "left")
            if isinstance(cell.value, (int, float)):
                cell.number_format = _NUM_FMT
            if cell.row == 1:
                cell.font = header_font; cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif col in EDIT_COLS:
                cell.font = data_font; cell.fill = edit_fill
            elif col == HIDE_COL:
                cell.font = Font(size=9, color="AAAAAA", name="微软雅黑")
                cell.fill = PatternFill("solid", fgColor=_C_GRAY)
            else:
                cell.font = data_font; cell.fill = readonly_fill

    col_widths = [8, 6, 16, 12, 16, 28, 36, 20, 14, 14, 18, 18, 20, 42]
    for idx, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22

    base = f"{label}_收入未匹配记录_待修正.xlsx"
    path = next_output_path(output_dir, base)
    wb.save(path)
    return path


# ══════════════════════════════════════════════════════════════════════
# v2 修正补录辅助：嵌入修正 Sheet + 读取修正 + 写回规则库
# ══════════════════════════════════════════════════════════════════════

_UNMATCHED_SHEET_EXPENSE = "★支出未匹配（可补规则）"
_UNMATCHED_SHEET_INCOME  = "★收入未匹配（可补规则）"


def _build_unmatched_rows_expense(items) -> tuple[list[str], list[list]]:
    """从支出分类结果中提取未匹配记录，返回 (headers, data_rows)。"""
    headers = [
        "年份", "月份", "公司名称", "交易日期", "借方发生额（元）",
        "对方名称", "摘要", "银行名称",
        "当前费用类型", "当前承担部门",
        "修正费用类型",   # ← 财务人员填写
        "修正承担部门",   # ← 财务人员填写
        "核对备注",
        "_映射键",        # 程序内部列，请勿删除或修改
    ]
    rows = []
    for item in items:
        if not is_unmatched(item):
            continue
        rec = item.record
        rows.append([
            str(rec.trade_date.year),
            str(rec.trade_date.month),
            rec.company,
            rec.trade_date.isoformat(),
            decimal_to_float(rec.debit),
            rec.counterparty,
            rec.summary,
            rec.bank_name,
            item.fee,
            item.department,
            "",   # 修正费用类型
            "",   # 修正承担部门
            "",   # 核对备注
            exact_key_from_record(rec),
        ])
    return headers, rows


def _build_unmatched_rows_income(items) -> tuple[list[str], list[list]]:
    """从收入分类结果中提取未匹配记录，返回 (headers, data_rows)。"""
    headers = [
        "年份", "月份", "公司名称", "交易日期", "贷方发生额（元）",
        "对方名称", "摘要", "银行名称",
        "当前收入类型",
        "修正收入类型",   # ← 财务人员填写
        "核对备注",
        "_映射键",
    ]
    rows = []
    for item in items:
        if not is_income_unmatched(item):
            continue
        rec = item.record
        rows.append([
            str(rec.trade_date.year),
            str(rec.trade_date.month),
            rec.company,
            rec.trade_date.isoformat(),
            decimal_to_float(rec.credit),
            rec.counterparty,
            rec.summary,
            rec.bank_name,
            getattr(item, "income_type", ""),
            "",   # 修正收入类型
            "",   # 核对备注
            exact_key_from_record(rec),
        ])
    return headers, rows


def _write_unmatched_sheet(wb: Workbook, sheet_name: str,
                           headers: list[str], rows: list[list]) -> None:
    """将未匹配记录写入工作簿中的指定 Sheet（若已存在则先删除）。"""
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]

    ws = wb.create_sheet(sheet_name)

    EDIT_COLS = {i + 1 for i, h in enumerate(headers)
                 if h.startswith("修正") or h == "核对备注"}
    HIDE_COL  = len(headers)  # _映射键列（最后一列）

    edit_fill = PatternFill("solid", fgColor="FFF2CC")
    hdr_fill  = PatternFill("solid", fgColor=_C_BLUE)
    hdr_font  = Font(bold=True, color=_C_WHITE, size=10, name="微软雅黑")
    dat_font  = Font(size=10, name="微软雅黑")

    ws.append(headers)
    for row in rows:
        ws.append(row)

    for row_cells in ws.iter_rows():
        for cell in row_cells:
            col = cell.column
            cell.border = _BORDER_THIN
            cell.alignment = Alignment(
                vertical="center", wrap_text=True,
                horizontal="right" if isinstance(cell.value, (int, float)) else "left",
            )
            if isinstance(cell.value, (int, float)):
                cell.number_format = _NUM_FMT
            if cell.row == 1:
                cell.font      = hdr_font
                cell.fill      = hdr_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            elif col in EDIT_COLS:
                cell.font = dat_font
                cell.fill = edit_fill
            elif col == HIDE_COL:
                cell.font = Font(size=9, color="AAAAAA", name="微软雅黑")
                cell.fill = PatternFill("solid", fgColor=_C_GRAY)
            else:
                cell.font = dat_font
                cell.fill = PatternFill("solid", fgColor=_C_STRIPE if cell.row % 2 == 0 else _C_WHITE)

    # 列宽
    col_widths = [8, 6, 16, 12, 16, 28, 36, 20, 14, 16, 16, 20, 42]
    for idx, w in enumerate(col_widths[:len(headers)], start=1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


def embed_expense_unmatched_sheet(wb: Workbook, items) -> int:
    """
    将支出未匹配记录作为 Sheet 嵌入已有报表工作簿。
    返回嵌入的未匹配记录数（0 表示全部匹配，无需操作）。

    Sheet 名称：★支出未匹配（可补规则）
    黄色列为财务人员填写区域：修正费用类型 / 修正承担部门 / 核对备注
    """
    headers, rows = _build_unmatched_rows_expense(items)
    if not rows:
        return 0
    _write_unmatched_sheet(wb, _UNMATCHED_SHEET_EXPENSE, headers, rows)
    return len(rows)


def embed_income_unmatched_sheet(wb: Workbook, items) -> int:
    """
    将收入未匹配记录作为 Sheet 嵌入已有报表工作簿。
    返回嵌入的未匹配记录数（0 表示全部匹配，无需操作）。

    Sheet 名称：★收入未匹配（可补规则）
    黄色列为财务人员填写区域：修正收入类型 / 核对备注
    """
    headers, rows = _build_unmatched_rows_income(items)
    if not rows:
        return 0
    _write_unmatched_sheet(wb, _UNMATCHED_SHEET_INCOME, headers, rows)
    return len(rows)


def read_expense_corrections(path: Path) -> list[dict]:
    """
    从支出 待完善 报表的"★支出未匹配（可补规则）"Sheet 中
    读取财务人员已填写的修正记录。

    有效记录条件：_映射键 不为空 且 修正费用类型 不为空。
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet_name = _UNMATCHED_SHEET_EXPENSE
    if sheet_name not in wb.sheetnames:
        return []

    ws = wb[sheet_name]
    headers = [clean_text(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    cols = {h: i for i, h in enumerate(headers)}

    if "_映射键" not in cols or "修正费用类型" not in cols:
        return []

    corrections = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        key  = clean_text(row[cols["_映射键"]]) if cols["_映射键"] < len(row) else ""
        fee  = normalize_fee(row[cols["修正费用类型"]]) if cols["修正费用类型"] < len(row) else ""
        dept = ""
        if "修正承担部门" in cols and cols["修正承担部门"] < len(row):
            dept = normalize_department(row[cols["修正承担部门"]])
        note = ""
        if "核对备注" in cols and cols["核对备注"] < len(row):
            note = clean_text(row[cols["核对备注"]])
        if key and fee:
            corrections.append({"mapping_key": key, "fee": fee,
                                 "department": dept, "note": note})
    return corrections


def read_income_corrections(path: Path) -> list[dict]:
    """
    从收入 待完善 报表的"★收入未匹配（可补规则）"Sheet 中
    读取财务人员已填写的修正记录。

    有效记录条件：_映射键 不为空 且 修正收入类型 不为空。
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    sheet_name = _UNMATCHED_SHEET_INCOME
    if sheet_name not in wb.sheetnames:
        return []

    ws = wb[sheet_name]
    headers = [clean_text(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    cols = {h: i for i, h in enumerate(headers)}

    if "_映射键" not in cols or "修正收入类型" not in cols:
        return []

    corrections = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        key          = clean_text(row[cols["_映射键"]]) if cols["_映射键"] < len(row) else ""
        income_type  = normalize_fee(row[cols["修正收入类型"]]) if cols["修正收入类型"] < len(row) else ""
        note = ""
        if "核对备注" in cols and cols["核对备注"] < len(row):
            note = clean_text(row[cols["核对备注"]])
        if key and income_type:
            corrections.append({"mapping_key": key, "income_type": income_type,
                                 "note": note})
    return corrections


def _style_rules_header(ws) -> None:
    for cell in ws[1]:
        cell.font      = Font(bold=True, size=10, color=_C_WHITE, name="微软雅黑")
        cell.fill      = PatternFill("solid", fgColor=_C_BLUE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = _BORDER_THIN


def _style_rules_sheet(ws) -> None:
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border    = _BORDER_THIN
            cell.font      = Font(size=10, name="微软雅黑")
            cell.fill      = PatternFill("solid",
                                         fgColor=_C_STRIPE if cell.row % 2 == 0 else _C_WHITE)
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.column_dimensions["A"].width = 60
    for col_letter in ["B", "C", "D", "E"]:
        ws.column_dimensions[col_letter].width = 18


def append_expense_rules(corrections: list[dict], rule_path: Path) -> tuple[int, int]:
    """
    将支出修正写入 规则库.xlsx 的"支出_精确映射"Sheet。
    已有的映射键将被更新，新键将被追加。
    返回 (新增数量, 更新数量)。
    """
    if not corrections:
        return 0, 0

    wb = openpyxl.load_workbook(rule_path) if rule_path.exists() else openpyxl.Workbook()

    # 优先用新版 sheet 名，兼容旧版
    sheet_name = next(
        (n for n in ("支出_精确映射", "精确映射") if n in wb.sheetnames), None
    )
    if sheet_name is None:
        sheet_name = "支出_精确映射"
        ws = wb.create_sheet(sheet_name, 0)
        ws.append(["映射键", "费用类型", "承担部门", "备注"])
        _style_rules_header(ws)
    else:
        ws = wb[sheet_name]

    headers = [clean_text(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    cols = {h: i + 1 for i, h in enumerate(headers)}   # 1-indexed for ws.cell()
    key_col  = cols.get("映射键",  1)
    fee_col  = cols.get("费用类型", 2)
    dept_col = cols.get("承担部门", 3)
    note_col = cols.get("备注",    4)

    # 读取现有映射键 → 行号
    existing: dict[str, int] = {}
    for row in ws.iter_rows(min_row=2):
        k = clean_text(row[key_col - 1].value)
        if k:
            existing[k] = row[0].row

    added = updated = 0
    for c in corrections:
        key = c["mapping_key"]
        if key in existing:
            r = existing[key]
            ws.cell(r, fee_col).value  = c["fee"]
            ws.cell(r, dept_col).value = c.get("department", "")
            ws.cell(r, note_col).value = c.get("note", "")
            updated += 1
        else:
            ws.append([key, c["fee"], c.get("department", ""), c.get("note", "")])
            existing[key] = ws.max_row
            added += 1

    _style_rules_sheet(ws)
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(rule_path)
    return added, updated


def append_income_rules(corrections: list[dict], rule_path: Path) -> tuple[int, int]:
    """
    将收入修正写入 规则库.xlsx 的"收入_精确映射"Sheet。
    返回 (新增数量, 更新数量)。
    """
    if not corrections:
        return 0, 0

    wb = openpyxl.load_workbook(rule_path) if rule_path.exists() else openpyxl.Workbook()

    sheet_name = next(
        (n for n in ("收入_精确映射", "精确映射") if n in wb.sheetnames), None
    )
    if sheet_name is None:
        sheet_name = "收入_精确映射"
        ws = wb.create_sheet(sheet_name)
        ws.append(["映射键", "收入类型", "备注"])
        _style_rules_header(ws)
    else:
        ws = wb[sheet_name]

    headers = [clean_text(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    cols = {h: i + 1 for i, h in enumerate(headers)}
    key_col  = cols.get("映射键",  1)
    type_col = cols.get("收入类型", 2)
    note_col = cols.get("备注",    3)

    existing: dict[str, int] = {}
    for row in ws.iter_rows(min_row=2):
        k = clean_text(row[key_col - 1].value)
        if k:
            existing[k] = row[0].row

    added = updated = 0
    for c in corrections:
        key = c["mapping_key"]
        if key in existing:
            r = existing[key]
            ws.cell(r, type_col).value = c["income_type"]
            ws.cell(r, note_col).value = c.get("note", "")
            updated += 1
        else:
            ws.append([key, c["income_type"], c.get("note", "")])
            existing[key] = ws.max_row
            added += 1

    _style_rules_sheet(ws)
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(rule_path)
    return added, updated



# ── 本文件为纯库，无入口代码 ────────────────────────────────────────────────
# 请使用以下程序运行处理：
#   程序一（生成报表）：python src/run_process.py
#   程序二（应用支出修正）：python src/apply_corrections.py --input <待修正文件>
#   程序三（应用收入修正）：python src/apply_income_corrections.py --input <待修正文件>


# ══════════════════════════════════════════════════════════════════════
# §3  报表增强功能（原 报表增强.py）
# ══════════════════════════════════════════════════════════════════════

# ─── §3 专用样式常量（来自原 报表增强.py）─────────────────────────────────────
_C_DGREEN = "D9EAD3"
_C_YELL   = "FFF2CC"
_C_RED_L  = "FFE0E0"
_C_RED_D  = "F4CCCC"
_C_BLUE_L = "CFE2F3"

_thin_enhance = Side(style="thin", color="BFBFBF")
_BORDER       = Border(
    left=_thin_enhance, right=_thin_enhance,
    top=_thin_enhance,  bottom=_thin_enhance,
)
_NUM = "#,##0.00"

# 集团内往来款类型（与 §2 保持一致，供 §3 函数直接引用）
INTRAGROUP_INCOME  = {"借款收入", "往来款"}
INTRAGROUP_EXPENSE = {"分子公司借款", "医馆借款"}


def _clean(v: object) -> str:
    return "" if v is None else str(v).strip()


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", fgColor=color)


def _font(bold: bool = False, size: int = 10,
          color: str = "000000", name: str = "微软雅黑") -> Font:
    return Font(bold=bold, size=size, color=color, name=name)


def _align(h: str = "center", v: str = "center", wrap: bool = False) -> Alignment:
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _w(ws, row: int, col: int, value=None, bold: bool = False,
       size: int = 10, color: str = "000000", bg: str | None = None,
       h: str = "center", fmt: str | None = None) -> None:
    """快速写入单元格并设置样式。"""
    cell = ws.cell(row, col)
    if value is not None:
        cell.value = value
    cell.font   = _font(bold, size, color)
    cell.fill   = _fill(bg) if bg else PatternFill()
    cell.alignment = _align(h, wrap=False)
    cell.border = _BORDER
    if fmt:
        cell.number_format = fmt


def _find_header_col(ws, key: str, max_scan: int = 12) -> int | None:
    """动态找到包含 key 文字的行号（扫描前 max_scan 行）。"""
    for r in range(1, max_scan + 1):
        row_vals = [_clean(ws.cell(r, c).value) for c in range(1, ws.max_column + 1)]
        if key in row_vals:
            return r
    return None


def _is_number(v: object) -> bool:
    """判断单元格值是否为有效数值（非"数据缺失"等占位文字）。"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return True
    s = str(v).strip()
    return s != "" and "缺失" not in s and "—" not in s and "-" != s


# ─── 读取明细数据 ──────────────────────────────────────────────────────────────

def read_all_details(wb, amount_col: str, type_col: str,
                     sheet_keyword: str) -> list[tuple]:
    """
    扫描工作簿中所有包含 sheet_keyword 的 Sheet，
    读取行级明细数据。

    返回 list of (company, month, amount, category)
    """
    result = []
    for name in wb.sheetnames:
        if sheet_keyword not in name:
            continue
        # 从 Sheet 名提取月份数字（如"3月收入明细" → 3）
        match = re.search(r"(\d+)月", name)
        if not match:
            continue
        month = int(match.group(1))

        ws = wb[name]
        hrow = _find_header_col(ws, amount_col)
        if hrow is None:
            continue

        headers: dict[str, int] = {}
        for c in range(1, ws.max_column + 1):
            v = _clean(ws.cell(hrow, c).value)
            if v:
                headers[v] = c

        if amount_col not in headers or "公司名称" not in headers:
            continue

        co_col   = headers["公司名称"]
        amt_col  = headers[amount_col]
        cat_col  = headers.get(type_col)

        for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
            if not row or all(v is None for v in row):
                continue
            co   = _clean(row[co_col  - 1])
            raw  = row[amt_col - 1]
            cat  = _clean(row[cat_col - 1]) if cat_col else ""
            if not co:
                continue
            try:
                amt = float(raw)
            except (TypeError, ValueError):
                continue
            if amt <= 0:
                continue
            result.append((co, month, amt, cat))

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Feature 1 — 收支综合对比 Sheet
# ═══════════════════════════════════════════════════════════════════════════════

def build_comparison_sheet(
    wb_income,
    income_data: list[tuple],
    expense_data: list[tuple],
    year: int,
) -> None:
    """
    在收入工作簿第 2 个位置插入"收支综合对比"Sheet。

    Sheet 结构：
      一、按月全集团汇总（收入/支出/净现金流各行，月份各列）
      二、按公司明细（各公司净收入/净支出/净现金流）
    """
    SHEET_NAME = "收支综合对比"
    if SHEET_NAME in wb_income.sheetnames:
        del wb_income[SHEET_NAME]
    ws = wb_income.create_sheet(SHEET_NAME, 1)

    # ── 聚合 ─────────────────────────────────────────────────────────────────
    months    = sorted(set(m for _, m, _, _ in income_data + expense_data))
    companies = sorted(set(co for co, _, _, _ in income_data + expense_data))

    inc       = defaultdict(lambda: defaultdict(float))
    inc_intra = defaultdict(lambda: defaultdict(float))
    for co, m, amt, cat in income_data:
        inc[co][m] += amt
        if cat in INTRAGROUP_INCOME:
            inc_intra[co][m] += amt

    exp       = defaultdict(lambda: defaultdict(float))
    exp_intra = defaultdict(lambda: defaultdict(float))
    for co, m, amt, cat in expense_data:
        exp[co][m] += amt
        if cat in INTRAGROUP_EXPENSE:
            exp_intra[co][m] += amt

    def net_inc(co, m):
        return inc[co][m] - inc_intra[co][m]

    def net_exp(co, m):
        return exp[co][m] - exp_intra[co][m]

    def net_cf(co, m):
        return net_inc(co, m) - net_exp(co, m)

    n_months = len(months)
    # 列布局：A=指标/公司名, B..B+n=月份列, B+n+1=合计
    total_cols = 1 + n_months + 1

    row = 1

    # ── 大标题 ───────────────────────────────────────────────────────────────
    ws.merge_cells(start_row=row, start_column=1,
                   end_row=row, end_column=total_cols)
    _w(ws, row, 1, f"玉玄道集团 · {year}年 收支综合对比",
       bold=True, size=14, color=_C_WHITE, bg=_C_NAVY)
    ws.row_dimensions[row].height = 32
    row += 1

    # ════════════════════════════════════════════════════════════════════════
    # 一、按月全集团汇总
    # ════════════════════════════════════════════════════════════════════════
    ws.merge_cells(start_row=row, start_column=1,
                   end_row=row, end_column=total_cols)
    _w(ws, row, 1, "一、按月汇总（全集团）", bold=True, size=11,
       color=_C_WHITE, bg=_C_BLUE, h="left")
    ws.row_dimensions[row].height = 22
    row += 1

    # 表头行
    month_hdr_row = row
    for c, label in enumerate(["指标"] + [f"{m}月" for m in months] + ["合计"], 1):
        _w(ws, row, c, label, bold=True, color=_C_WHITE, bg=_C_BLUE)
    ws.row_dimensions[row].height = 20
    row += 1

    # 指标行定义：(标签, 背景色, 是否粗体, 计算函数)
    def _all(fn):
        """对全集团所有公司求和"""
        return lambda m: sum(fn(co, m) for co in companies)

    metric_rows = [
        ("收入合计",        _C_GREEN,  False, _all(lambda co, m: inc[co][m])),
        ("  └ 往来款收入",  _C_GRAY,   False, _all(lambda co, m: inc_intra[co][m])),
        ("净收入",          _C_DGREEN, True,  _all(net_inc)),
        ("支出合计",        _C_RED_L,  False, _all(lambda co, m: exp[co][m])),
        ("  └ 往来款支出",  _C_GRAY,   False, _all(lambda co, m: exp_intra[co][m])),
        ("净支出",          _C_RED_D,  True,  _all(net_exp)),
        ("净现金流",        _C_BLUE_L, True,  _all(net_cf)),
    ]

    for label, bg, bold, fn in metric_rows:
        vals = [fn(m) for m in months]
        _w(ws, row, 1, label, bold=bold, bg=bg, h="left")
        for c, v in enumerate(vals, 2):
            _w(ws, row, c, v if v else None, bold=bold, bg=bg, fmt=_NUM)
        _w(ws, row, 2 + n_months, sum(vals) if any(vals) else None,
           bold=True, bg=bg, fmt=_NUM)
        ws.row_dimensions[row].height = 18
        row += 1

    row += 1  # 空行

    # ════════════════════════════════════════════════════════════════════════
    # 二、按公司明细
    # ════════════════════════════════════════════════════════════════════════
    ws.merge_cells(start_row=row, start_column=1,
                   end_row=row, end_column=total_cols)
    _w(ws, row, 1, "二、按公司明细（净收入 / 净支出 / 净现金流）",
       bold=True, size=11, color=_C_WHITE, bg=_C_BLUE, h="left")
    ws.row_dimensions[row].height = 22
    row += 1

    # 公司区段共 4 + n_months 列
    co_total_cols = 4 + n_months
    co_headers = (["公司名称", "净收入（元）", "净支出（元）", "净现金流（元）"]
                  + [f"{m}月净现金流" for m in months])
    co_hdr_row = row
    for c, h in enumerate(co_headers, 1):
        _w(ws, row, c, h, bold=True, color=_C_WHITE, bg=_C_BLUE)
    ws.row_dimensions[row].height = 20
    row += 1

    company_data_start = row
    for i, co in enumerate(companies):
        bg = _C_STRIPE if i % 2 == 0 else _C_WHITE
        ni  = sum(net_inc(co, m) for m in months)
        ne  = sum(net_exp(co, m) for m in months)
        ncf = ni - ne
        monthly_cf = [net_cf(co, m) for m in months]

        _w(ws, row, 1, co, bg=bg, h="left")
        for c, v in enumerate([ni, ne, ncf] + monthly_cf, 2):
            _w(ws, row, c, v if v else None, bg=bg, fmt=_NUM)
        ws.row_dimensions[row].height = 18
        row += 1

    # 集团合计行
    grand_ni  = sum(sum(net_inc(co, m) for m in months) for co in companies)
    grand_ne  = sum(sum(net_exp(co, m) for m in months) for co in companies)
    grand_ncf = grand_ni - grand_ne
    grand_monthly = [sum(net_cf(co, m) for co in companies) for m in months]

    for c, v in enumerate(
        ["集团合计", grand_ni, grand_ne, grand_ncf] + grand_monthly, 1
    ):
        _w(ws, row, c, v, bold=True, color=_C_WHITE, bg=_C_BLUE,
           h="left" if c == 1 else "center", fmt=_NUM if c > 1 else None)
    ws.row_dimensions[row].height = 20
    company_data_end = row
    row += 1

    # ── 列宽 ──────────────────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 26
    for c in range(2, co_total_cols + 2):
        ws.column_dimensions[get_column_letter(c)].width = 14

    # ── 冻结 & AutoFilter ────────────────────────────────────────────────────
    ws.freeze_panes = ws.cell(month_hdr_row + 1, 2)
    ws.auto_filter.ref = (
        f"A{co_hdr_row}:"
        f"{get_column_letter(co_total_cols)}{company_data_end}"
    )

    print(f"  ✓ 收支综合对比 Sheet 已生成"
          f"（{len(months)} 个月 × {len(companies)} 家公司）")

    return {
        "sheet_name":      "收支综合对比",
        "company_rows":    (company_data_start, company_data_end - 1),
        "month_col_range": (2, 1 + n_months),           # 月度净现金流列范围（公司区段）
        "sparkline_col":   co_total_cols + 1,            # 迷你图放在合计列之后
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Feature 2 — AutoFilter + 冻结行 + 完整度状态列
# ═══════════════════════════════════════════════════════════════════════════════

def apply_autofilter_and_freeze(wb, detail_keywords: tuple[str, ...] = ("明细",)) -> None:
    """
    对所有包含 detail_keywords 的 Sheet：
      - 找到表头行 → 设置 AutoFilter
      - 冻结表头下一行
    """
    count = 0
    for name in wb.sheetnames:
        if not any(kw in name for kw in detail_keywords):
            continue
        ws = wb[name]
        hrow = _find_header_col(ws, "公司名称")
        if hrow is None:
            continue
        max_col = ws.max_column
        max_row = ws.max_row
        if max_col < 2 or max_row <= hrow:
            continue
        ws.auto_filter.ref = (
            f"A{hrow}:{get_column_letter(max_col)}{max_row}"
        )
        ws.freeze_panes = ws.cell(hrow + 1, 1)
        count += 1

    print(f"  ✓ AutoFilter + 冻结行 已应用于 {count} 个明细 Sheet")


def add_balance_status_column(wb) -> None:
    """
    在"各账户余额"Sheet 末尾增加"完整度"状态列。

    判断逻辑（检查表头含"期初余额"/"期末余额"的列是否为有效数值）：
      ✓ 完整   — D/E/F 三列均为数值      → 绿色
      △ 部分   — 部分为数值              → 黄色
      ✗ 全缺失 — 全部为"数据缺失"占位符  → 红色
    """
    if "各账户余额" not in wb.sheetnames:
        return

    ws = wb["各账户余额"]
    hrow = _find_header_col(ws, "来源文件")
    if hrow is None:
        hrow = _find_header_col(ws, "银行账户")
    if hrow is None:
        return

    # 找余额列（表头含"期初"或"期末"的列）
    balance_cols: list[int] = []
    for c in range(1, ws.max_column + 1):
        v = _clean(ws.cell(hrow, c).value)
        if ("期初" in v or "期末" in v) and "余额" in v:
            balance_cols.append(c)
        if len(balance_cols) >= 3:
            break

    if len(balance_cols) < 2:
        print("  ⚠ 未找到足够余额列，跳过完整度状态列")
        return

    status_col = ws.max_column + 1
    _w(ws, hrow, status_col, "完整度", bold=True, color=_C_WHITE, bg=_C_BLUE)
    ws.column_dimensions[get_column_letter(status_col)].width = 10

    added = 0
    for r in range(hrow + 1, ws.max_row + 1):
        first = _clean(ws.cell(r, 1).value)
        # 跳过合计行、空行、说明行
        if not first or "合计" in first or "说明" in first or "—" in first:
            continue

        vals   = [ws.cell(r, c).value for c in balance_cols]
        has    = [_is_number(v) for v in vals]
        filled = sum(has)

        if filled == len(balance_cols):
            status, bg, fc = "✓ 完整",   _C_GREEN, "375623"
        elif filled == 0:
            status, bg, fc = "✗ 全缺失", "FFB3B3", "843C0C"
        else:
            status, bg, fc = "△ 部分",   _C_YELL,  "7D6608"

        cell = ws.cell(r, status_col)
        cell.value     = status
        cell.font      = _font(False, 10, fc)
        cell.fill      = _fill(bg)
        cell.alignment = _align()
        cell.border    = _BORDER
        added += 1

    print(f"  ✓ 完整度状态列 已添加（共 {added} 个账户行）")


# ═══════════════════════════════════════════════════════════════════════════════
# Feature 3 — 原生 Sparkline（lxml XML 注入）
# ═══════════════════════════════════════════════════════════════════════════════

# Sparkline 规格：一个 dict 描述在哪个 Sheet 的哪些行加迷你图
SparklineSpec = dict  # {sheet_name, data_first_row, data_last_row,
#                        month_first_col, month_last_col, sparkline_col, type}


def _build_sparkline_xml(sheet_name: str, specs: list[SparklineSpec]) -> str:
    """
    构建一个 <extLst> 字符串，包含所有 Sparkline 组。
    每个 spec 对应一组相同配置的 sparklines（同一类型、同一行范围）。
    """
    # 安全处理 sheet 名中的单引号
    safe_name = sheet_name.replace("'", "''")

    groups_xml = ""
    for spec in specs:
        sp_type   = spec.get("type", "line")
        first_row = spec["data_first_row"]
        last_row  = spec["data_last_row"]
        mc_letter = get_column_letter(spec["month_first_col"])
        ml_letter = get_column_letter(spec["month_last_col"])
        sp_letter = get_column_letter(spec["sparkline_col"])

        sparklines_inner = ""
        for r in range(first_row, last_row + 1):
            sparklines_inner += (
                f"<x14:sparkline>"
                f"<xm:f>'{safe_name}'!${mc_letter}${r}:${ml_letter}${r}</xm:f>"
                f"<xm:sqref>{sp_letter}{r}</xm:sqref>"
                f"</x14:sparkline>"
            )

        groups_xml += f"""
        <x14:sparklineGroup
            type="{sp_type}"
            displayEmptyCellsAs="gap"
            markers="1"
            high="1"
            low="1">
          <x14:colorSeries theme="4" tint="-0.499984740745262"/>
          <x14:colorNegative theme="5"/>
          <x14:colorMarkers theme="4" tint="-0.499984740745262"/>
          <x14:colorFirst theme="4" tint="0.39997558519241921"/>
          <x14:colorLast theme="4" tint="0.39997558519241921"/>
          <x14:colorHigh theme="4"/>
          <x14:colorLow theme="5"/>
          <x14:sparklines>{sparklines_inner}</x14:sparklines>
        </x14:sparklineGroup>"""

    return (
        '<extLst>'
        '<ext uri="{05C60535-1F16-4fd2-B633-E4A46CF9E463}"'
        ' xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main">'
        '<x14:sparklineGroups'
        ' xmlns:xm="http://schemas.microsoft.com/office/excel/2006/main">'
        + groups_xml
        + '</x14:sparklineGroups></ext></extLst>'
    )


def _detect_company_pivot_structure(wb, sheet_name: str) -> dict | None:
    """
    分析"公司月度汇总"类 Sheet 的结构，返回：
      {header_row, first_data_row, last_data_row, month_first_col, month_last_col}
    """
    if sheet_name not in wb.sheetnames:
        return None
    ws = wb[sheet_name]

    hrow = _find_header_col(ws, "公司名称")
    if hrow is None:
        return None

    # 找月份列范围（表头含"月"字的列）
    month_cols = []
    for c in range(1, ws.max_column + 1):
        v = _clean(ws.cell(hrow, c).value)
        if re.search(r"\d+月", v):
            month_cols.append(c)

    if not month_cols:
        return None

    # 找数据行范围（跳过"合计"/"往来款"/"净"行）
    skip_keywords = ("合计", "往来款", "净", "集团", "")
    data_rows = []
    for r in range(hrow + 1, ws.max_row + 1):
        v = _clean(ws.cell(r, 1).value)
        if v and not any(v.startswith(kw) for kw in skip_keywords):
            data_rows.append(r)

    if not data_rows:
        return None

    return {
        "header_row":      hrow,
        "first_data_row":  data_rows[0],
        "last_data_row":   data_rows[-1],
        "month_first_col": min(month_cols),
        "month_last_col":  max(month_cols),
    }


def inject_sparklines(
    xlsx_path: Path,
    sparkline_map: dict[str, list[SparklineSpec]],
) -> None:
    """
    通过 ZIP 后处理向已保存的 XLSX 文件注入原生 Sparkline XML。

    sparkline_map: {sheet_name: [SparklineSpec, ...]}
    """
    # 读取 workbook.xml.rels 以获取 sheet_name → sheet XML 文件 的映射
    buf = io.BytesIO(xlsx_path.read_bytes())

    with zipfile.ZipFile(buf) as zf:
        # 建立 sheetName → zipfile 内路径 的映射
        wb_xml = zf.read("xl/workbook.xml").decode("utf-8")
        rels_xml = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8")

    # 从 workbook.xml 提取 sheetName
    sheet_entries: dict[str, str] = {}  # name → r:id
    for m in re.finditer(r'<sheet\b[^>]*name="([^"]*)"[^>]*r:id="([^"]*)"', wb_xml):
        sheet_entries[m.group(1)] = m.group(2)

    # 从 rels 提取 r:id → 相对路径（逐个 Relationship 元素解析）
    rid_to_path: dict[str, str] = {}
    for rel_el in re.finditer(r'<Relationship\b(.+?)/?>', rels_xml, re.DOTALL):
        attrs    = rel_el.group(1)
        rid_m    = re.search(r'Id="([^"]*)"',     attrs)
        target_m = re.search(r'Target="([^"]*)"', attrs)
        if rid_m and target_m:
            target = target_m.group(1).lstrip("/")   # 去掉前导 /
            rid_to_path[rid_m.group(1)] = target

    # 最终：sheetName → zip 内路径
    name_to_zip: dict[str, str] = {
        name: rid_to_path[rid]
        for name, rid in sheet_entries.items()
        if rid in rid_to_path
    }

    buf.seek(0)
    out_buf = io.BytesIO()

    with zipfile.ZipFile(buf) as zin, \
         zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            # 找需要注入的 sheet
            injected = False
            for sheet_name, specs in sparkline_map.items():
                zip_path = name_to_zip.get(sheet_name)
                if zip_path and item.filename == zip_path:
                    xml_str = data.decode("utf-8")
                    sp_xml  = _build_sparkline_xml(sheet_name, specs)
                    # 替换 </worksheet>
                    xml_str = xml_str.replace("</worksheet>",
                                              sp_xml + "</worksheet>")
                    data    = xml_str.encode("utf-8")
                    injected = True
                    break

            zout.writestr(item, data)

    xlsx_path.write_bytes(out_buf.getvalue())
    print(f"  ✓ Sparkline 已注入 {len(sparkline_map)} 个 Sheet")


def prepare_sparkline_specs(wb, comparison_meta: dict | None) -> dict[str, list[SparklineSpec]]:
    """
    自动分析工作簿，为以下 Sheet 准备 Sparkline 规格：
      - 公司月度汇总（收入）
      - 公司月度汇总
      - 收支综合对比（如果有）
    """
    result: dict[str, list[SparklineSpec]] = {}

    for sheet_name in wb.sheetnames:
        if "公司月度汇总" not in sheet_name:
            continue
        struct = _detect_company_pivot_structure(wb, sheet_name)
        if struct is None:
            continue
        ws = wb[sheet_name]
        sp_col = struct["month_last_col"] + 2  # 合计列之后放迷你图

        # 在表头写"趋势"标签
        hrow = struct["header_row"]
        _w(ws, hrow, sp_col, "趋势", bold=True, color=_C_WHITE, bg=_C_BLUE)
        ws.column_dimensions[get_column_letter(sp_col)].width = 12

        result[sheet_name] = [{
            "data_first_row":  struct["first_data_row"],
            "data_last_row":   struct["last_data_row"],
            "month_first_col": struct["month_first_col"],
            "month_last_col":  struct["month_last_col"],
            "sparkline_col":   sp_col,
            "type":            "line",
        }]
        print(f"  ✓ Sparkline 规格已准备：{sheet_name}"
              f"（{struct['last_data_row'] - struct['first_data_row'] + 1} 行）")

    # 收支综合对比 Sheet 的公司区段
    if comparison_meta:
        sname = comparison_meta["sheet_name"]
        if sname in wb.sheetnames:
            ws  = wb[sname]
            fr, lr = comparison_meta["company_rows"]
            mc, ml = comparison_meta["month_col_range"]
            sp_col = comparison_meta["sparkline_col"]

            # 在表头写"趋势"标签
            hrow = fr - 1
            _w(ws, hrow, sp_col, "趋势", bold=True, color=_C_WHITE, bg=_C_BLUE)
            ws.column_dimensions[get_column_letter(sp_col)].width = 12

            result[sname] = [{
                "data_first_row":  fr,
                "data_last_row":   lr,
                "month_first_col": mc,
                "month_last_col":  ml,
                "sparkline_col":   sp_col,
                "type":            "line",
            }]
            print(f"  ✓ Sparkline 规格已准备：{sname}（公司区段）")

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════════════════

def _find_latest(output_dir: Path, keyword: str) -> Path | None:
    """从 output/ 自动找最新的匹配文件。"""
    candidates = sorted(
        [p for p in output_dir.glob("*.xlsx") if keyword in p.name
         and not p.name.startswith(".")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="报表增强：收支对比 + AutoFilter + Sparkline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--income",  type=Path, default=None,
                   help="收入报表路径（不传则自动查找最新收入全年统计文件）")
    p.add_argument("--expense", type=Path, default=None,
                   help="支出报表路径（不传则自动查找最新收支全年统计文件）")
    p.add_argument("--output-dir", type=Path, default=None,
                   help="输出目录（默认与输入文件相同）")
    p.add_argument("--no-overwrite", action="store_true",
                   help="不覆盖原文件，另存为 *_增强版.xlsx")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # ── 解析项目根目录 ─────────────────────────────────────────────────────────
    project_root = Path(__file__).resolve().parent.parent
    output_dir   = project_root / "output"

    # ── 自动查找输入文件 ───────────────────────────────────────────────────────
    income_path  = args.income  or _find_latest(output_dir, "收入全年统计")
    expense_path = args.expense or _find_latest(output_dir, "收支全年统计")

    if income_path is None:
        raise SystemExit("❌ 未找到收入报表，请用 --income 指定路径")
    if expense_path is None:
        raise SystemExit("❌ 未找到支出报表，请用 --expense 指定路径")
    if not income_path.exists():
        raise SystemExit(f"❌ 收入报表不存在：{income_path}")
    if not expense_path.exists():
        raise SystemExit(f"❌ 支出报表不存在：{expense_path}")

    print(f"\n📊 收入报表：{income_path.name}")
    print(f"📊 支出报表：{expense_path.name}\n")

    # ── 读取明细数据 ───────────────────────────────────────────────────────────
    print("📂 读取收入明细数据……")
    wb_income  = openpyxl.load_workbook(income_path)
    income_data = read_all_details(wb_income,
                                   amount_col="贷方发生额",
                                   type_col="收入类型",
                                   sheet_keyword="收入明细")
    print(f"   收入记录 {len(income_data)} 条")

    print("📂 读取支出明细数据……")
    wb_expense  = openpyxl.load_workbook(expense_path)
    expense_data = read_all_details(wb_expense,
                                    amount_col="借方发生额",
                                    type_col="费用类型",
                                    sheet_keyword="明细")
    print(f"   支出记录 {len(expense_data)} 条")

    # 推断年份
    all_months = [m for _, m, _, _ in income_data + expense_data]
    years_from_file = re.findall(r"(\d{4})年", income_path.name)
    year = int(years_from_file[0]) if years_from_file else 2026

    # ── Feature 1：收支综合对比 Sheet ──────────────────────────────────────────
    print("\n⚙️  生成收支综合对比 Sheet……")
    comparison_meta = build_comparison_sheet(wb_income, income_data, expense_data, year)

    # ── Feature 2：AutoFilter + 冻结行（收入工作簿）──────────────────────────
    print("\n⚙️  应用 AutoFilter + 冻结行……")
    apply_autofilter_and_freeze(wb_income,  detail_keywords=("明细",))
    apply_autofilter_and_freeze(wb_expense, detail_keywords=("明细",))

    # ── Feature 2：完整度状态列（两个工作簿）────────────────────────────────
    print("\n⚙️  添加完整度状态列……")
    add_balance_status_column(wb_income)
    add_balance_status_column(wb_expense)

    # ── Feature 3：Sparkline 准备（收入工作簿）──────────────────────────────
    print("\n⚙️  准备 Sparkline 规格……")
    sp_map = prepare_sparkline_specs(wb_income, comparison_meta)

    # ── 确定输出路径 ───────────────────────────────────────────────────────────
    out_dir = args.output_dir or income_path.parent

    def _out_path(original: Path) -> Path:
        if args.no_overwrite:
            return out_dir / (original.stem + "_增强版.xlsx")
        return out_dir / original.name

    income_out  = _out_path(income_path)
    expense_out = _out_path(expense_path)

    # ── 保存工作簿 ──────────────────────────────────────────────────────────
    print(f"\n💾 保存收入报表……")
    wb_income.save(income_out)

    print(f"💾 保存支出报表……")
    wb_expense.save(expense_out)

    # ── Feature 3：注入 Sparkline XML（ZIP 后处理）──────────────────────────
    if sp_map:
        print(f"\n✨ 注入 Sparkline……")
        inject_sparklines(income_out, sp_map)

    print(f"\n✅ 增强完成！")
    print(f"   收入报表 → {income_out.name}")
    print(f"   支出报表 → {expense_out.name}")


if __name__ == "__main__":
    main()
