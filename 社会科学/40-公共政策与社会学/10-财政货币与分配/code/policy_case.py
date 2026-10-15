#!/usr/bin/env python3
"""Recalculate the synthetic closed-economy policy ledger (unit: 亿元)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

Position = Dict[str, int]
State = Dict[str, Position]

START: State = {
    "低资产家庭": {"存款": 20, "贷款": 30},
    "高资产家庭": {"存款": 80, "国债": 60},
    "企业": {"存款": 50, "贷款": 100},
    "银行": {"准备金": 30, "贷款资产": 130, "国债": 20, "存款负债": 150, "权益": 30},
    "政府": {"央行存款": 20, "国债负债": 130},
    "央行": {"国债": 50, "准备金负债": 30, "政府存款负债": 20, "权益": 0},
}


@dataclass(frozen=True)
class Entry:
    name: str
    changes: Mapping[str, Mapping[str, int]]
    kind: str
    gdp: int = 0


ENTRIES: tuple[Entry, ...] = (
    Entry("高资产家庭购买原计划消费", {"高资产家庭": {"存款": -20}, "企业": {"存款": 20}}, "最终消费", 20),
    Entry("企业支付工资", {"企业": {"存款": -60}, "低资产家庭": {"存款": 40}, "高资产家庭": {"存款": 20}}, "生产收入"),
    Entry("低资产家庭购买原计划消费", {"低资产家庭": {"存款": -30}, "企业": {"存款": 30}}, "最终消费", 30),
    Entry("私人部门缴税", {"低资产家庭": {"存款": -5}, "高资产家庭": {"存款": -20}, "企业": {"存款": -5}, "银行": {"存款负债": -30, "准备金": -30}, "政府": {"央行存款": 30}, "央行": {"准备金负债": -30, "政府存款负债": 30}}, "再分配"),
    Entry("向低资产家庭转移", {"低资产家庭": {"存款": 25}, "银行": {"存款负债": 25, "准备金": 25}, "政府": {"央行存款": -25}, "央行": {"准备金负债": 25, "政府存款负债": -25}}, "再分配"),
    Entry("政府购买公共服务", {"企业": {"存款": 20}, "银行": {"存款负债": 20, "准备金": 20}, "政府": {"央行存款": -20}, "央行": {"准备金负债": 20, "政府存款负债": -20}}, "政府最终消费", 20),
    Entry("高资产家庭认购新国债", {"高资产家庭": {"存款": -15, "国债": 15}, "银行": {"存款负债": -15, "准备金": -15}, "政府": {"央行存款": 15, "国债负债": 15}, "央行": {"准备金负债": -15, "政府存款负债": 15}}, "金融交易"),
    Entry("银行向低资产家庭新增贷款", {"低资产家庭": {"存款": 10, "贷款": 10}, "银行": {"贷款资产": 10, "存款负债": 10}}, "金融交易"),
    Entry("新增贷款融资消费", {"低资产家庭": {"存款": -10}, "企业": {"存款": 10}}, "最终消费", 10),
    Entry("银行计付存款利息", {"低资产家庭": {"存款": 1}, "高资产家庭": {"存款": 4}, "企业": {"存款": 2}, "银行": {"存款负债": 7, "权益": -7}}, "财产收入"),
    Entry("借款人支付贷款利息", {"低资产家庭": {"存款": -2}, "企业": {"存款": -7}, "银行": {"存款负债": -9, "权益": 9}}, "财产收入"),
    Entry("政府向家庭付息", {"高资产家庭": {"存款": 3}, "银行": {"存款负债": 3, "准备金": 3}, "政府": {"央行存款": -3}, "央行": {"准备金负债": 3, "政府存款负债": -3}}, "财产收入"),
    Entry("政府向银行付息", {"银行": {"准备金": 1, "权益": 1}, "政府": {"央行存款": -1}, "央行": {"准备金负债": 1, "政府存款负债": -1}}, "财产收入"),
    Entry("政府向央行付息", {"政府": {"央行存款": -2}, "央行": {"政府存款负债": -2, "权益": 2}}, "合并后抵销"),
    Entry("央行向银行支付准备金利息", {"银行": {"准备金": 1, "权益": 1}, "央行": {"准备金负债": 1, "权益": -1}}, "财产收入"),
    Entry("央行向政府上缴利润", {"政府": {"央行存款": 1}, "央行": {"政府存款负债": 1, "权益": -1}}, "合并后抵销"),
)

ASSETS = {
    "低资产家庭": ("存款",), "高资产家庭": ("存款", "国债"), "企业": ("存款",),
    "银行": ("准备金", "贷款资产", "国债"), "政府": ("央行存款",), "央行": ("国债",),
}
LIABILITIES = {
    "低资产家庭": ("贷款",), "高资产家庭": (), "企业": ("贷款",),
    "银行": ("存款负债",), "政府": ("国债负债",), "央行": ("准备金负债", "政府存款负债"),
}


def apply_entries(start: State = START, entries: Iterable[Entry] = ENTRIES) -> State:
    state = deepcopy(start)
    for entry in entries:
        for sector, changes in entry.changes.items():
            for account, change in changes.items():
                state[sector][account] = state[sector].get(account, 0) + change
    return state


def net_financial_worth(state: State, sector: str) -> int:
    if sector in ("银行", "央行"):
        return state[sector]["权益"]
    return sum(state[sector].get(k, 0) for k in ASSETS[sector]) - sum(
        state[sector].get(k, 0) for k in LIABILITIES[sector]
    )


def instrument_gaps(state: State) -> dict[str, int]:
    return {
        "存款": state["低资产家庭"]["存款"] + state["高资产家庭"]["存款"] + state["企业"]["存款"] - state["银行"]["存款负债"],
        "贷款": state["银行"]["贷款资产"] - state["低资产家庭"]["贷款"] - state["企业"]["贷款"],
        "国债": state["高资产家庭"]["国债"] + state["银行"]["国债"] + state["央行"]["国债"] - state["政府"]["国债负债"],
        "准备金": state["银行"]["准备金"] - state["央行"]["准备金负债"],
        "政府存款": state["政府"]["央行存款"] - state["央行"]["政府存款负债"],
        "银行资产负债表": state["银行"]["准备金"] + state["银行"]["贷款资产"] + state["银行"]["国债"] - state["银行"]["存款负债"] - state["银行"]["权益"],
        "央行资产负债表": state["央行"]["国债"] - state["央行"]["准备金负债"] - state["央行"]["政府存款负债"] - state["央行"]["权益"],
    }


def analytical_g_c_nfw(state: State) -> int:
    return net_financial_worth(state, "政府") + net_financial_worth(state, "央行")


def private_nfw(state: State) -> int:
    return sum(net_financial_worth(state, s) for s in ("低资产家庭", "高资产家庭", "企业", "银行"))


SAVING = {"低资产家庭": 19, "高资产家庭": -13, "企业": 10, "银行": 4, "G+C分析性合并": -20}
RATE_CASHFLOW = {
    "低资产家庭": {"调息前": 0.0, "调息后": -1.0},
    "高资产家庭": {"调息前": 4.0, "调息后": 7.0},
    "企业": {"调息前": -4.0, "调息后": -5.0},
    "银行": {"调息前": 3.5, "调息后": 4.0},
    "G+C分析性合并": {"调息前": -3.5, "调息后": -5.0},
}


def validate() -> list[str]:
    end = apply_entries()
    errors: list[str] = []
    for label, state in (("期初", START), ("期末", end)):
        for account, gap in instrument_gaps(state).items():
            if gap:
                errors.append(f"{label}{account}不平: {gap}")
    for label, state in (("期初", START), ("期末", end)):
        if private_nfw(state) + analytical_g_c_nfw(state):
            errors.append(f"{label}部门净金融资产和不为零")
    state = deepcopy(START)
    for step, entry in enumerate(ENTRIES, 1):
        state = apply_entries(state, (entry,))
        for account, gap in instrument_gaps(state).items():
            if gap:
                errors.append(f"第{step}步后{account}不平: {gap}")
        for sector, positions in state.items():
            for account, value in positions.items():
                if value < 0:
                    errors.append(f"第{step}步后出现未声明负余额: {sector}/{account}={value}")
    if sum(e.gdp for e in ENTRIES) != 80:
        errors.append("支出法GDP不是80")
    if sum(SAVING.values()):
        errors.append("部门储蓄和不为零")
    for timing in ("调息前", "调息后"):
        if abs(sum(v[timing] for v in RATE_CASHFLOW.values())) > 1e-9:
            errors.append(f"{timing}利息现金流不平")
    return errors


def markdown_summary() -> str:
    end = apply_entries()
    rows = [
        f"| {s} | {net_financial_worth(START, s)} | {net_financial_worth(end, s)} | {net_financial_worth(end, s)-net_financial_worth(START, s)} |"
        for s in START
    ]
    return "\n".join([
        "| 部门 | 期初净金融资产 | 期末净金融资产 | 变化 |",
        "| --- | ---: | ---: | ---: |", *rows, "",
        f"私人合计：{private_nfw(START)} → {private_nfw(end)}",
        f"G+C分析性合并：{analytical_g_c_nfw(START)} → {analytical_g_c_nfw(end)}",
        f"GDP：{sum(e.gdp for e in ENTRIES)}",
        "校验：" + ("全部通过" if not validate() else "；".join(validate())),
    ])


if __name__ == "__main__":
    print(markdown_summary())
