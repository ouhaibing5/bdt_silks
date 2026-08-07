"""跟进打分单测。"""

from datetime import date

from bdt_customer_mcp.followup import group_followup_items, score_customer_for_followup


def test_score_silent_and_arrears() -> None:
    item = {
        "id": "KXT_1",
        "number": "DSKJ",
        "companyName": "测试公司",
        "state": {"name": "合作中", "value": "COMPDEALED"},
        "level": {"name": "V3", "value": "V3"},
        "lastOrderDate": "2025-01-01",
        "followDate": "2025-01-01",
        "arrearsDaysStr": "4",
        "rmbBalance": -10,
        "categoryType": "EXPRESS",
    }
    scored = score_customer_for_followup(item, today=date(2026, 8, 7))
    assert scored["number"] == "DSKJ"
    assert scored["priorityScore"] >= 50
    assert "silentRisk" in scored["reasonCodes"]
    assert "risk" in scored["reasonCodes"]
    assert "upsell" in scored["reasonCodes"]
    assert "欠款" in scored["suggestion"] or "账期" in scored["suggestion"]


def test_group_followup_items_orders_by_score() -> None:
    items = [
        {"number": "A", "priorityScore": 10, "reasonCodes": ["watch"]},
        {"number": "B", "priorityScore": 80, "reasonCodes": ["risk", "silentRisk"]},
        {"number": "C", "priorityScore": 40, "reasonCodes": ["upsell"]},
    ]
    grouped = group_followup_items(items, top_n=2)
    assert grouped["mustFollowToday"][0]["number"] == "B"
    assert any(x["number"] == "B" for x in grouped["riskCustomers"])
