"""八达通物流产品 / 报价 MCP Server 入口。"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from bdt_product_mcp.erp_client import ErpClient, get_settings
from bdt_product_mcp.schemas import (
    CustomerProductQuoteListResult,
    ProductPriceListResult,
    summarize_customer_product_quote,
    summarize_export_result,
    summarize_price_candidate,
    summarize_price_detail,
)

mcp = FastMCP(
    "bdt-product",
    instructions=(
        "查询永利通八达通 ERP 物流产品指导价、价格明细、客户关联报价，"
        "并导出指导价/客户报价 Excel（返回 OSS 下载链接）。"
        "productLine: EXPRESS=国际快递，SPECIAL_LINE=小包专线。"
        "查价可用产品编号或产品名称（如 GJ01 / 加拿大DHL6000）。"
        "客户报价需传客户 ID（dealCustomerId，可先用 bdt-customer 查编号换 ID）。"
        "导出前先查列表拿到 quoteTimeId；无 quoteTimeId 的客户产品无法导出。"
    ),
)


def _client() -> ErpClient:
    return ErpClient(get_settings())


def _dump(model: Any) -> str:
    if hasattr(model, "model_dump"):
        payload = model.model_dump(by_alias=True, exclude_none=True)
    else:
        payload = model
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _page_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = _page_data(payload)
    items = data.get("items") if data else payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _page_meta(payload: dict[str, Any]) -> dict[str, Any]:
    source = _page_data(payload) or payload
    return {
        "currentPage": source.get("currentPage"),
        "pageCount": source.get("pageCount"),
        "pageSize": source.get("pageSize"),
        "recordCount": source.get("recordCount") or source.get("count"),
    }


def _normalize_ids(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace("，", ",").replace(";", ",").split(","):
        value = chunk.strip()
        if value and value not in parts:
            parts.append(value)
    return parts


def _assert_ok(payload: dict[str, Any], action: str) -> None:
    result_type = payload.get("resultType")
    if result_type in (None, 1, "1"):
        return
    msg = payload.get("resultMsg") or payload.get("message") or "未知错误"
    raise RuntimeError(f"{action}失败: resultType={result_type}, msg={msg}")


@mcp.tool()
def search_product_prices(
    key_word: str,
    product_line: str = "EXPRESS",
    item_type: str = "WPX",
    country_id: str = "",
    country_name: str = "",
    customer_id: str = "",
    weight: str = "",
    current_page: int = 1,
    page_size: int = 50,
) -> str:
    """按产品编号或产品名称查询指导价候选列表。

    product_line: EXPRESS=国际快递，SPECIAL_LINE=小包专线。
    key_word: 支持产品编号（如 GJ01）或产品名称（如 加拿大DHL6000）。
    返回 quoteTimeId / supplyProductId，供明细查询与导出使用。
    """
    client = _client()
    payload = client.price_query_list_data(
        product_line=product_line,
        key_word=key_word.strip(),
        item_type=item_type,
        country_id=country_id,
        country_name=country_name,
        customer_id=customer_id,
        weight=weight,
        current_page=max(1, current_page),
        page_size=min(max(1, page_size), 500),
    )
    _assert_ok(payload, "产品查价")
    meta = _page_meta(payload)
    items = [summarize_price_candidate(item) for item in _extract_items(payload)]
    result = ProductPriceListResult(
        productLine=product_line,
        keyWord=key_word.strip() or None,
        currentPage=meta.get("currentPage"),
        pageCount=meta.get("pageCount"),
        pageSize=meta.get("pageSize"),
        recordCount=int(meta["recordCount"])
        if str(meta.get("recordCount") or "").isdigit()
        else meta.get("recordCount"),
        items=items,
    )
    return _dump(result)


@mcp.tool()
def get_product_price_detail(
    quote_time_id: str,
    product_id: str,
    price_type: str = "PUBLISHED",
    max_weight_bands: int = 40,
) -> str:
    """查询产品价格明细（渠道说明 + 重量段价格表）。

    quote_time_id: 来自 search_product_prices 的 quoteTimeId（或客户报价列表）。
    product_id: 来自 search 的 supplyProductId / 客户列表的 productId。
    price_type: 默认 PUBLISHED（指导价）。
    max_weight_bands: 返回的重量段上限，避免超长；完整条数见 weightBandCount。
    """
    client = _client()
    qid = quote_time_id.strip()
    pid = product_id.strip()
    if not qid or not pid:
        raise ValueError("quote_time_id 与 product_id 均不能为空")
    payload = client.get_price_detail_view_info(
        quote_time_id=qid,
        product_id=pid,
        price_type=price_type.strip() or "PUBLISHED",
    )
    _assert_ok(payload, "查询价格明细")
    result = summarize_price_detail(
        quote_time_id=qid,
        product_id=pid,
        price_type=price_type.strip() or "PUBLISHED",
        payload=payload,
        max_weight_bands=min(max(1, max_weight_bands), 200),
    )
    return _dump(result)


@mcp.tool()
def export_product_prices(
    quote_time_ids: str = "",
    key_word: str = "",
    product_line: str = "EXPRESS",
    item_type: str = "WPX",
    country_name: str = "",
) -> str:
    """导出指导价 Excel，返回 OSS 下载链接。

    优先传 quote_time_ids（逗号分隔，来自 search_product_prices.quoteTimeId）。
    若只传 key_word，会先查价再导出命中的全部 quoteTimeId。
    """
    client = _client()
    ids = _normalize_ids(quote_time_ids)
    if not ids:
        keyword = key_word.strip()
        if not keyword:
            raise ValueError("请提供 quote_time_ids，或提供 key_word 以便自动查价导出")
        listed = client.price_query_list_data(
            product_line=product_line,
            key_word=keyword,
            item_type=item_type,
            country_name=country_name,
            page_size=500,
        )
        _assert_ok(listed, "产品查价")
        ids = [
            str(item.get("id")).strip()
            for item in _extract_items(listed)
            if item.get("id")
        ]
        if not ids:
            raise RuntimeError(f"未找到可导出的产品报价: keyWord={keyword}")
    joined = ",".join(ids)
    payload = client.export_published_price_data(
        quote_time_ids=joined,
        product_line=product_line,
        key_word=key_word.strip(),
        item_type=item_type,
        country_name=country_name,
    )
    _assert_ok(payload, "导出指导价")
    relative = str(payload.get("data") or "")
    download_url = client.settings.build_export_download_url(relative)
    result = summarize_export_result(
        payload=payload,
        download_url=download_url,
        quote_time_ids=joined,
        product_line=product_line,
    )
    return _dump(result)


@mcp.tool()
def list_customer_product_quotes(
    customer_id: str,
    product_line: str = "EXPRESS",
    key_word: str = "",
    price_status: str = "START",
    current_page: int = 1,
    page_size: int = 50,
) -> str:
    """查询客户关联的物流产品 / 报价列表。

    customer_id: 成交客户 ID（非客户编号；可先用 bdt-customer.get_customer_by_number 获取）。
    product_line: EXPRESS / SPECIAL_LINE。
    key_word: 可选，按产品名称/编号过滤。
    price_status: 默认 START（已启用）；传空字符串可放宽。
    仅 quoteTimeId 非空的条目可导出 Excel。
    """
    cid = customer_id.strip()
    if not cid:
        raise ValueError("customer_id 不能为空")
    client = _client()
    payload = client.get_deal_customer_logistics_page(
        customer_id=cid,
        product_line=product_line,
        key_word=key_word.strip(),
        price_status=price_status,
        current_page=max(1, current_page),
        page_size=min(max(1, page_size), 500),
    )
    _assert_ok(payload, "查询客户物流产品")
    meta = _page_meta(payload)
    items = [summarize_customer_product_quote(item) for item in _extract_items(payload)]
    exportable = sum(1 for item in items if item.quote_time_id)
    record_count = meta.get("recordCount")
    result = CustomerProductQuoteListResult(
        customerId=cid,
        productLine=product_line,
        keyWord=key_word.strip() or None,
        currentPage=meta.get("currentPage"),
        pageCount=meta.get("pageCount"),
        pageSize=meta.get("pageSize"),
        recordCount=int(record_count)
        if str(record_count or "").isdigit()
        else record_count,
        items=items,
        exportableCount=exportable,
    )
    return _dump(result)


@mcp.tool()
def export_customer_product_quotes(
    customer_id: str,
    quote_time_ids: str = "",
    product_numbers: str = "",
    product_line: str = "EXPRESS",
    key_word: str = "",
) -> str:
    """导出客户报价 Excel，返回 OSS 下载链接。

    customer_id: 成交客户 ID。
    任选其一：
    - quote_time_ids: 逗号分隔，来自 list_customer_product_quotes.quoteTimeId
    - product_numbers: 逗号分隔产品编号，自动在客户产品列表中匹配 quoteTimeId
    若都未传但给了 key_word，则导出该关键字过滤后全部可导出项。
    """
    cid = customer_id.strip()
    if not cid:
        raise ValueError("customer_id 不能为空")
    client = _client()
    ids = _normalize_ids(quote_time_ids)
    sell_ids: list[str] = []

    if not ids:
        numbers = {n.upper() for n in _normalize_ids(product_numbers)}
        listed = client.get_deal_customer_logistics_page(
            customer_id=cid,
            product_line=product_line,
            key_word=key_word.strip(),
            price_status="START",
            page_size=500,
        )
        _assert_ok(listed, "查询客户物流产品")
        matched: list[tuple[str, str]] = []
        for item in _extract_items(listed):
            current = item.get("currentPrice") if isinstance(item.get("currentPrice"), dict) else {}
            qid = str(current.get("quoteTimeId") or "").strip()
            if not qid:
                continue
            number = str(item.get("productNumber") or "").strip().upper()
            if numbers and number not in numbers:
                continue
            sell = str(current.get("sellQuoteTimeId") or "").strip() or "-"
            matched.append((qid, sell))
        if numbers and not matched:
            raise RuntimeError(
                f"未匹配到可导出报价（需有 quoteTimeId）: product_numbers={product_numbers}"
            )
        if not matched:
            raise RuntimeError("未找到可导出的客户报价，请先 list_customer_product_quotes 确认 quoteTimeId")
        ids = [qid for qid, _ in matched]
        sell_ids = [sell for _, sell in matched]

    joined = ",".join(ids)
    sell_joined = ",".join(sell_ids) if sell_ids else ",".join("-" for _ in ids)
    payload = client.export_customer_price_data(
        customer_id=cid,
        quote_time_ids=joined,
        product_line=product_line,
        sell_quote_time_ids=sell_joined,
    )
    _assert_ok(payload, "导出客户报价")
    relative = str(payload.get("data") or "")
    download_url = client.settings.build_export_download_url(relative)
    result = summarize_export_result(
        payload=payload,
        download_url=download_url,
        quote_time_ids=joined,
        product_line=product_line,
        customer_id=cid,
    )
    return _dump(result)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
