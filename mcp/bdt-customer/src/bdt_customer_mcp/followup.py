"""客户跟进打分与清单分组（基于 listData 字段，不依赖全量货量接口）。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


LEVEL_SCORE = {
    "V5": 25,
    "V4": 20,
    "V3": 15,
    "V2": 10,
    "V1": 5,
}

CATEGORY_CROSS_SELL = ("SPECIAL_LINE", "EXPRESS", "FBA")


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _enum_value(value: Any) -> str:
    if isinstance(value, dict):
        raw = value.get("value") or value.get("name") or ""
        return str(raw)
    return str(value or "")


def _enum_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "")
    return str(value or "")


def _days_since(value: Any, today: date) -> int | None:
    parsed = _parse_date(value)
    if not parsed:
        return None
    return max((today - parsed).days, 0)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def score_customer_for_followup(
    item: dict[str, Any],
    *,
    today: date | None = None,
    silent_days: int = 30,
    cold_days: int = 60,
    follow_stale_days: int = 14,
) -> dict[str, Any]:
    """对单条 listData 客户做跟进优先级打分。"""
    today = today or date.today()
    reasons: list[str] = []
    buckets: list[str] = []
    score = 0

    state_value = _enum_value(item.get("state")).upper()
    state_name = _enum_name(item.get("state")) or state_value
    level_value = _enum_value(item.get("level")).upper()
    level_name = _enum_name(item.get("level")) or level_value

    last_order_days = _days_since(item.get("lastOrderDate"), today)
    follow_days = _days_since(item.get("followDate"), today)
    arrears_raw = item.get("arrearsDaysStr")
    if arrears_raw in (None, ""):
        arrears_raw = item.get("arrearsDays")
    try:
        arrears_days = int(float(arrears_raw)) if arrears_raw not in (None, "") else 0
    except (TypeError, ValueError):
        arrears_days = 0

    rmb = _as_float(item.get("rmbBalance")) or 0.0
    usd = _as_float(item.get("usdBalance")) or 0.0
    hkd = _as_float(item.get("hkdBalance")) or 0.0

    # 1) 状态
    if state_value == "NOORDER" or not item.get("lastOrderDate"):
        score += 40
        reasons.append("从未下单或无末单日期")
        buckets.append("neverOrdered")
    elif state_value == "EXPIRED":
        score += 35
        reasons.append("客户状态为已过期")
        buckets.append("expired")
    elif state_value == "COMPDEALED":
        score += 5

    # 2) 沉默 / 流失
    if last_order_days is not None:
        if last_order_days >= cold_days:
            score += 35
            reasons.append(f"末单已 {last_order_days} 天（冷客户）")
            buckets.append("silentRisk")
        elif last_order_days >= silent_days:
            score += 25
            reasons.append(f"末单已 {last_order_days} 天（沉默）")
            buckets.append("silentRisk")
        elif last_order_days <= 7:
            score -= 5
            reasons.append("近 7 天有出货，可暂缓")
            buckets.append("canDefer")

    # 3) 账期 / 余额
    if arrears_days > 0:
        score += min(30, 10 + arrears_days * 2)
        reasons.append(f"欠款天数 {arrears_days}")
        buckets.append("risk")
    if rmb < 0 or usd < 0 or hkd < 0:
        score += 20
        reasons.append("账户余额为负")
        buckets.append("risk")

    # 4) 等级价值
    level_bonus = LEVEL_SCORE.get(level_value, 0)
    if level_bonus:
        score += level_bonus
        reasons.append(f"客户等级 {level_name or level_value}")
        if last_order_days is not None and last_order_days >= silent_days:
            buckets.append("highValueSilent")

    # 5) 跟进断档
    if follow_days is None:
        score += 15
        reasons.append("无跟进记录日期")
        buckets.append("followGap")
    elif follow_days >= follow_stale_days:
        score += 18
        reasons.append(f"距上次跟进 {follow_days} 天")
        buckets.append("followGap")

    # 6) 业务覆盖缺口（交叉销售）
    category = str(item.get("categoryType") or "")
    opened = {part.strip() for part in category.split(",") if part.strip()}
    missing = [code for code in CATEGORY_CROSS_SELL if code not in opened]
    if opened and missing:
        score += 8 * len(missing)
        names = {"SPECIAL_LINE": "小包专线", "EXPRESS": "国际快递", "FBA": "FBA头程"}
        miss_labels = "、".join(names.get(code, code) for code in missing)
        reasons.append(f"业务未覆盖：{miss_labels}")
        buckets.append("upsell")

    # 默认桶
    if not buckets:
        buckets.append("watch")

    # 建议动作
    suggestion = _build_suggestion(
        state_value=state_value,
        last_order_days=last_order_days,
        arrears_days=arrears_days,
        missing=missing,
        follow_days=follow_days,
        level_name=level_name or level_value,
    )

    assigned = item.get("assignedSales") or {}
    assigned_org = item.get("assignedOrg") or {}
    unique_buckets = list(dict.fromkeys(buckets))

    return {
        "id": str(item.get("id") or ""),
        "number": str(item.get("number") or ""),
        "companyName": item.get("companyName"),
        "companyShortName": item.get("companyShortName"),
        "state": state_name,
        "level": level_name or level_value or None,
        "lastOrderDate": item.get("lastOrderDate"),
        "lastOrderDays": last_order_days,
        "followDate": item.get("followDate"),
        "followDays": follow_days,
        "arrearsDays": arrears_days,
        "rmbBalance": rmb,
        "usdBalance": usd,
        "hkdBalance": hkd,
        "categoryType": category or None,
        "categoryTypeNames": item.get("categoryTypeNames"),
        "assignedSalesName": assigned.get("name") if isinstance(assigned, dict) else None,
        "assignedOrgName": assigned_org.get("name") if isinstance(assigned_org, dict) else None,
        "customerSegment": _enum_name(item.get("customerSegment")) or None,
        "priorityScore": score,
        "reasonCodes": unique_buckets,
        "reasons": reasons,
        "suggestion": suggestion,
    }


def _build_suggestion(
    *,
    state_value: str,
    last_order_days: int | None,
    arrears_days: int,
    missing: list[str],
    follow_days: int | None,
    level_name: str,
) -> str:
    parts: list[str] = []
    if arrears_days > 0:
        parts.append(f"先核对应收/账期（欠款 {arrears_days} 天），再谈新单")
    if state_value == "NOORDER" or last_order_days is None:
        parts.append("确认开户后首票卡点：报价、渠道、交仓方式、资料是否齐全")
    elif last_order_days is not None and last_order_days >= 30:
        parts.append(
            f"回访沉默原因（末单 {last_order_days} 天）：是否换渠道、价格、时效或旺季备货"
        )
    if missing:
        names = {"SPECIAL_LINE": "专线", "EXPRESS": "快递", "FBA": "FBA"}
        parts.append(
            "交叉销售："
            + "、".join(names.get(code, code) for code in missing)
            + "，结合目的国与货型给一版对比报价"
        )
    if follow_days is None or (follow_days is not None and follow_days >= 14):
        parts.append("补写跟进记录，约定下次联系时间")
    if level_name and not parts:
        parts.append(f"保持节奏维护 {level_name} 客户，确认本周出货计划")
    if not parts:
        parts.append("保持观察，可做轻触达确认近期货量")
    return "；".join(parts)


def group_followup_items(items: list[dict[str, Any]], *, top_n: int = 20) -> dict[str, Any]:
    ranked = sorted(items, key=lambda x: x.get("priorityScore") or 0, reverse=True)
    top = ranked[: max(top_n, 0)]

    def pick(code: str) -> list[dict[str, Any]]:
        return [item for item in ranked if code in (item.get("reasonCodes") or [])][:top_n]

    return {
        "generatedAt": date.today().isoformat(),
        "totalScored": len(ranked),
        "topN": top_n,
        "mustFollowToday": top,
        "riskCustomers": pick("risk"),
        "silentCustomers": pick("silentRisk"),
        "opportunityCustomers": pick("upsell") + pick("highValueSilent"),
        "canDefer": pick("canDefer"),
        "allRanked": ranked,
    }
