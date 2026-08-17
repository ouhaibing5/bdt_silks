"""schema / OSS URL 单测。"""

from bdt_product_mcp.erp_client import ErpSettings
from bdt_product_mcp.schemas import (
    summarize_customer_product_quote,
    summarize_export_result,
    summarize_price_candidate,
    summarize_price_detail,
)


def test_summarize_price_candidate() -> None:
    item = summarize_price_candidate(
        {
            "id": "19ffe931e6ed447",
            "supplyProductId": "K9_DHLC-6000",
            "productName": "加拿大DHL6000",
            "supplyProduct": {"number": "GJ01"},
            "deliveryMethodName": "空运",
            "includePublishedPrice": 1,
            "allowBattery": 0,
            "deadline": "2026-08-20",
        }
    )
    data = item.model_dump(by_alias=True)
    assert data["quoteTimeId"] == "19ffe931e6ed447"
    assert data["productNumber"] == "GJ01"
    assert data["includePublishedPrice"] is True
    assert data["allowBattery"] is False


def test_summarize_price_detail_truncates_bands() -> None:
    payload = {
        "data": {
            "supplyProductName": "加拿大DHL6000",
            "productLine": "EXPRESS",
            "planName": "计划A",
            "remark": "只接受普货",
            "includeFuelFee": 1,
        },
        "extData": {
            "weightCols": [
                {
                    "startWeight": 0,
                    "endWeight": 0.5,
                    "formula": "165",
                    "calcTypeName": "总价",
                    "itemTypeName": "纸箱",
                    "itemTypeValue": "WPX",
                    "goodsTypeName": "小货",
                },
                {
                    "startWeight": 0.5,
                    "endWeight": 1,
                    "formula": "186",
                    "calcTypeName": "总价",
                    "itemTypeName": "纸箱",
                    "itemTypeValue": "WPX",
                    "goodsTypeName": "小货",
                },
            ]
        },
    }
    detail = summarize_price_detail(
        quote_time_id="qid",
        product_id="pid",
        price_type="PUBLISHED",
        payload=payload,
        max_weight_bands=1,
    )
    data = detail.model_dump(by_alias=True)
    assert data["weightBandCount"] == 2
    assert len(data["weightBands"]) == 1
    assert data["weightBands"][0]["formula"] == "165"


def test_summarize_customer_product_quote() -> None:
    item = summarize_customer_product_quote(
        {
            "productId": "K9_DHL-US",
            "productNumber": "DHL-US",
            "productName": "香港DHL-US",
            "productLine": {"name": "国际快递", "value": "EXPRESS"},
            "pricingMode": {"name": "总价+单价", "value": "TOTAL_UNIT"},
            "priceStatus": "START",
            "priceStatusName": "已启用",
            "currentPrice": {
                "quoteTimeId": "19ff4082941572e",
                "sellQuoteTimeId": "",
                "type": "指导价",
                "dateText": "(2027-8-6截止)",
                "startTime": "2026-08-12 00:00",
                "endTime": "2027-08-06 00:00",
            },
            "description": "一、渠道说明：" + ("x" * 300),
        }
    )
    data = item.model_dump(by_alias=True)
    assert data["quoteTimeId"] == "19ff4082941572e"
    assert data["productLine"] == "EXPRESS"
    assert data["productLineName"] == "国际快递"
    assert data["description"].endswith("…")
    assert len(data["description"]) <= 240


def test_build_export_download_url() -> None:
    settings = ErpSettings(
        secret="s",
        client_id="c",
        cu_id="ylbdt1",
        user_id="u",
        dc="d",
        oss_base_url="https://erposs.8dt.com/images/",
    )
    relative = "quote/ylbdt1/demo.xlsx?token"
    url = settings.build_export_download_url(relative)
    assert url == "https://erposs.8dt.com/images/quote/ylbdt1/demo.xlsx?token"

    # 相对路径已含 images/ 时不重复拼接
    assert (
        settings.build_export_download_url("images/quote/ylbdt1/a.xlsx")
        == "https://erposs.8dt.com/images/quote/ylbdt1/a.xlsx"
    )


def test_summarize_export_result() -> None:
    result = summarize_export_result(
        payload={"data": "quote/a.xlsx", "resultMsg": "导出成功", "resultType": 1},
        download_url="https://example.com/a.xlsx",
        quote_time_ids="id1,id2",
        product_line="EXPRESS",
        customer_id="K9_1",
    )
    data = result.model_dump(by_alias=True)
    assert data["resultMsg"] == "导出成功"
    assert data["downloadUrl"] == "https://example.com/a.xlsx"
    assert data["customerId"] == "K9_1"
