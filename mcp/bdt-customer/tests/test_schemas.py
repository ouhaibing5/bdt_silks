"""schema 裁剪单测。"""

from bdt_customer_mcp.schemas import summarize_account, summarize_customer


def test_summarize_customer_uses_enum_names() -> None:
    summary = summarize_customer(
        {
            "id": "KXT_1",
            "number": "DSKJ",
            "companyName": "测试公司",
            "state": {"name": "合作中", "value": "COMPDEALED"},
            "level": {"name": "V1", "value": "V1"},
            "assignedSales": {"name": "张三", "idCard": "secret"},
            "rmbBalance": -105,
        }
    )
    data = summary.model_dump(by_alias=True)
    assert data["companyName"] == "测试公司"
    assert data["state"] == "合作中"
    assert data["assignedSalesName"] == "张三"
    assert "idCard" not in data


def test_summarize_account_strips_sensitive_fields() -> None:
    account = summarize_account(
        {
            "id": "T6_DSKJ",
            "systemCode": "DSKJ",
            "businessType": {"name": "FBA头程", "value": "FBA"},
            "paymentMethod": {"name": "现结", "value": "DELIVERY"},
            "rmbBalance": 1.5,
            "apiToken": "token",
            "financialPerson": {"name": "会计", "idCard": "x"},
        }
    )
    data = account.model_dump(by_alias=True)
    assert data["businessType"] == "FBA头程"
    assert data["financialPersonName"] == "会计"
    assert "apiToken" not in data
    assert "idCard" not in data


def test_summarize_freight_trend_totals() -> None:
    from bdt_customer_mcp.schemas import summarize_freight_trend

    summary, points = summarize_freight_trend(
        [
            {
                "financeDate": "2026-01-12",
                "order_count": 3,
                "total_package_count": 4,
                "total_actual_weight": 55.24,
                "total_charged_weight": 57,
                "total_goods_volume": 0.3,
                "total_revenue": 10,
            },
            {
                "financeDate": "2026-01-19",
                "order_count": 2,
                "total_package_count": 3,
                "total_actual_weight": 43.66,
                "total_charged_weight": 47,
                "total_goods_volume": 0.2,
                "total_revenue": 5,
            },
        ]
    )
    assert len(points) == 2
    assert summary.day_count == 2
    assert summary.order_count == 5
    assert summary.total_package_count == 7
    assert abs(summary.total_actual_weight - 98.9) < 0.001
    assert summary.total_revenue == 15
