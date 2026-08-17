"""精简响应模型（对外 camelCase）。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        ser_json_by_alias=True,
    )


def _enum_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        name = value.get("name")
        if name is not None:
            return str(name)
        if value.get("value") is not None:
            return str(value.get("value"))
    return str(value)


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if value.get("value") is not None:
            return str(value.get("value"))
        if value.get("name") is not None:
            return str(value.get("name"))
    return str(value)


def _as_bool_flag(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


class ProductPriceCandidate(CamelModel):
    quote_time_id: str = Field(alias="quoteTimeId")
    supply_product_id: str | None = Field(default=None, alias="supplyProductId")
    product_number: str | None = Field(default=None, alias="productNumber")
    product_name: str | None = Field(default=None, alias="productName")
    currency_name: str | None = Field(default=None, alias="currencyName")
    delivery_method: str | None = Field(default=None, alias="deliveryMethod")
    delivery_method_name: str | None = Field(default=None, alias="deliveryMethodName")
    deadline: str | None = None
    include_published_price: bool | None = Field(
        default=None, alias="includePublishedPrice"
    )
    include_sales_price: bool | None = Field(default=None, alias="includeSalesPrice")
    include_fuel_fee: bool | None = Field(default=None, alias="includeFuelFee")
    allow_battery: bool | None = Field(default=None, alias="allowBattery")
    allow_magnet: bool | None = Field(default=None, alias="allowMagnet")
    allow_powder: bool | None = Field(default=None, alias="allowPowder")
    allow_liquid: bool | None = Field(default=None, alias="allowLiquid")


class ProductPriceListResult(CamelModel):
    product_line: str = Field(alias="productLine")
    key_word: str | None = Field(default=None, alias="keyWord")
    current_page: int | None = Field(default=None, alias="currentPage")
    page_count: int | None = Field(default=None, alias="pageCount")
    page_size: int | None = Field(default=None, alias="pageSize")
    record_count: int | None = Field(default=None, alias="recordCount")
    items: list[ProductPriceCandidate]


class WeightBand(CamelModel):
    start_weight: float | None = Field(default=None, alias="startWeight")
    end_weight: float | None = Field(default=None, alias="endWeight")
    formula: str | None = None
    calc_type_name: str | None = Field(default=None, alias="calcTypeName")
    goods_type_name: str | None = Field(default=None, alias="goodsTypeName")
    item_type_name: str | None = Field(default=None, alias="itemTypeName")
    item_type_value: str | None = Field(default=None, alias="itemTypeValue")
    unit_weight: str | None = Field(default=None, alias="unitWeight")


class ProductPriceDetailResult(CamelModel):
    quote_time_id: str = Field(alias="quoteTimeId")
    product_id: str = Field(alias="productId")
    price_type: str = Field(alias="priceType")
    supply_product_name: str | None = Field(default=None, alias="supplyProductName")
    product_line: str | None = Field(default=None, alias="productLine")
    plan_name: str | None = Field(default=None, alias="planName")
    price_range_name: str | None = Field(default=None, alias="priceRangeName")
    currency_name: str | None = Field(default=None, alias="currencyName")
    logistics_type_name: str | None = Field(default=None, alias="logisticsTypeName")
    price_status: str | None = Field(default=None, alias="priceStatus")
    start_date: str | None = Field(default=None, alias="startDate")
    end_date: str | None = Field(default=None, alias="endDate")
    include_published_price: bool | None = Field(
        default=None, alias="includePublishedPrice"
    )
    include_sales_price: bool | None = Field(default=None, alias="includeSalesPrice")
    include_fuel_fee: bool | None = Field(default=None, alias="includeFuelFee")
    large_cargo_threshold: str | None = Field(
        default=None, alias="largeCargoThreshold"
    )
    ticket_large_cargo_threshold: str | None = Field(
        default=None, alias="ticketLargeCargoThreshold"
    )
    remark: str | None = None
    weight_band_count: int = Field(default=0, alias="weightBandCount")
    weight_bands: list[WeightBand] = Field(default_factory=list, alias="weightBands")


class ExportPriceResult(CamelModel):
    result_msg: str | None = Field(default=None, alias="resultMsg")
    relative_path: str | None = Field(default=None, alias="relativePath")
    download_url: str | None = Field(default=None, alias="downloadUrl")
    quote_time_ids: str | None = Field(default=None, alias="quoteTimeIds")
    customer_id: str | None = Field(default=None, alias="customerId")
    product_line: str | None = Field(default=None, alias="productLine")


class CustomerProductQuote(CamelModel):
    product_id: str | None = Field(default=None, alias="productId")
    product_number: str | None = Field(default=None, alias="productNumber")
    product_name: str | None = Field(default=None, alias="productName")
    product_display: str | None = Field(default=None, alias="productDisplay")
    product_line: str | None = Field(default=None, alias="productLine")
    product_line_name: str | None = Field(default=None, alias="productLineName")
    price_status: str | None = Field(default=None, alias="priceStatus")
    price_status_name: str | None = Field(default=None, alias="priceStatusName")
    pricing_mode: str | None = Field(default=None, alias="pricingMode")
    pricing_mode_name: str | None = Field(default=None, alias="pricingModeName")
    currency_name: str | None = Field(default=None, alias="currencyName")
    ticket_large_cargo_threshold: str | None = Field(
        default=None, alias="ticketLargeCargoThreshold"
    )
    quote_time_id: str | None = Field(default=None, alias="quoteTimeId")
    sell_quote_time_id: str | None = Field(default=None, alias="sellQuoteTimeId")
    price_type: str | None = Field(default=None, alias="priceType")
    price_start_time: str | None = Field(default=None, alias="priceStartTime")
    price_end_time: str | None = Field(default=None, alias="priceEndTime")
    price_date_text: str | None = Field(default=None, alias="priceDateText")
    description: str | None = None


class CustomerProductQuoteListResult(CamelModel):
    customer_id: str = Field(alias="customerId")
    product_line: str = Field(alias="productLine")
    key_word: str | None = Field(default=None, alias="keyWord")
    current_page: int | None = Field(default=None, alias="currentPage")
    page_count: int | None = Field(default=None, alias="pageCount")
    page_size: int | None = Field(default=None, alias="pageSize")
    record_count: int | None = Field(default=None, alias="recordCount")
    items: list[CustomerProductQuote]
    exportable_count: int = Field(default=0, alias="exportableCount")


def summarize_price_candidate(raw: dict[str, Any]) -> ProductPriceCandidate:
    supply = raw.get("supplyProduct")
    product_number = None
    if isinstance(supply, dict) and supply.get("number") is not None:
        product_number = str(supply.get("number"))
    return ProductPriceCandidate(
        quoteTimeId=str(raw.get("id") or ""),
        supplyProductId=str(raw["supplyProductId"])
        if raw.get("supplyProductId") is not None
        else None,
        productNumber=product_number,
        productName=str(raw["productName"]) if raw.get("productName") is not None else None,
        currencyName=str(raw["currencyName"])
        if raw.get("currencyName") is not None
        else None,
        deliveryMethod=str(raw["deliveryMethod"])
        if raw.get("deliveryMethod") is not None
        else None,
        deliveryMethodName=str(raw["deliveryMethodName"])
        if raw.get("deliveryMethodName") is not None
        else None,
        deadline=str(raw["deadline"]) if raw.get("deadline") is not None else None,
        includePublishedPrice=_as_bool_flag(raw.get("includePublishedPrice")),
        includeSalesPrice=_as_bool_flag(raw.get("includeSalesPrice")),
        includeFuelFee=_as_bool_flag(raw.get("includeFuelFee")),
        allowBattery=_as_bool_flag(raw.get("allowBattery")),
        allowMagnet=_as_bool_flag(raw.get("allowMagnet")),
        allowPowder=_as_bool_flag(raw.get("allowPowder")),
        allowLiquid=_as_bool_flag(raw.get("allowLiquid")),
    )


def summarize_weight_band(raw: dict[str, Any]) -> WeightBand:
    return WeightBand(
        startWeight=_to_float(raw.get("startWeight")),
        endWeight=_to_float(raw.get("endWeight")),
        formula=str(raw["formula"]) if raw.get("formula") is not None else None,
        calcTypeName=str(raw["calcTypeName"])
        if raw.get("calcTypeName") is not None
        else None,
        goodsTypeName=str(raw["goodsTypeName"])
        if raw.get("goodsTypeName") is not None
        else None,
        itemTypeName=str(raw["itemTypeName"])
        if raw.get("itemTypeName") is not None
        else None,
        itemTypeValue=str(raw["itemTypeValue"])
        if raw.get("itemTypeValue") is not None
        else None,
        unitWeight=str(raw["unitWeight"]) if raw.get("unitWeight") is not None else None,
    )


def summarize_price_detail(
    *,
    quote_time_id: str,
    product_id: str,
    price_type: str,
    payload: dict[str, Any],
    max_weight_bands: int = 40,
) -> ProductPriceDetailResult:
    data = payload.get("data")
    source = data if isinstance(data, dict) else {}
    ext = payload.get("extData")
    if not isinstance(ext, dict):
        ext = source.get("extData") if isinstance(source, dict) else {}
    if not isinstance(ext, dict):
        ext = {}
    raw_bands = ext.get("weightCols") or []
    bands: list[WeightBand] = []
    if isinstance(raw_bands, list):
        for item in raw_bands:
            if isinstance(item, dict):
                bands.append(summarize_weight_band(item))
    truncated = bands[: max(0, max_weight_bands)]
    return ProductPriceDetailResult(
        quoteTimeId=quote_time_id,
        productId=product_id,
        priceType=price_type,
        supplyProductName=str(source["supplyProductName"])
        if source.get("supplyProductName") is not None
        else None,
        productLine=str(source["productLine"])
        if source.get("productLine") is not None
        else None,
        planName=str(source["planName"]) if source.get("planName") is not None else None,
        priceRangeName=str(source["priceRangeName"])
        if source.get("priceRangeName") is not None
        else None,
        currencyName=str(source["currencyName"])
        if source.get("currencyName") is not None
        else None,
        logisticsTypeName=str(source["logisticsTypeName"])
        if source.get("logisticsTypeName") is not None
        else None,
        priceStatus=str(source["priceStatus"])
        if source.get("priceStatus") is not None
        else None,
        startDate=str(source["startDate"]) if source.get("startDate") is not None else None,
        endDate=str(source["endDate"]) if source.get("endDate") is not None else None,
        includePublishedPrice=_as_bool_flag(source.get("includePublishedPrice")),
        includeSalesPrice=_as_bool_flag(source.get("includeSalesPrice")),
        includeFuelFee=_as_bool_flag(source.get("includeFuelFee")),
        largeCargoThreshold=str(source["largeCargoThreshold"])
        if source.get("largeCargoThreshold") is not None
        else None,
        ticketLargeCargoThreshold=str(source["ticketLargeCargoThreshold"])
        if source.get("ticketLargeCargoThreshold") is not None
        else None,
        remark=str(source["remark"]) if source.get("remark") is not None else None,
        weightBandCount=len(bands),
        weightBands=truncated,
    )


def summarize_customer_product_quote(raw: dict[str, Any]) -> CustomerProductQuote:
    current = raw.get("currentPrice") if isinstance(raw.get("currentPrice"), dict) else {}
    return CustomerProductQuote(
        productId=str(raw["productId"]) if raw.get("productId") is not None else None,
        productNumber=str(raw["productNumber"])
        if raw.get("productNumber") is not None
        else None,
        productName=str(raw["productName"]) if raw.get("productName") is not None else None,
        productDisplay=str(raw["productDisplay"])
        if raw.get("productDisplay") is not None
        else None,
        productLine=_enum_value(raw.get("productLine")),
        productLineName=_enum_name(raw.get("productLine")),
        priceStatus=str(raw["priceStatus"]) if raw.get("priceStatus") is not None else None,
        priceStatusName=str(raw["priceStatusName"])
        if raw.get("priceStatusName") is not None
        else None,
        pricingMode=_enum_value(raw.get("pricingMode")),
        pricingModeName=_enum_name(raw.get("pricingMode")),
        currencyName=str(raw["currencyName"])
        if raw.get("currencyName") is not None
        else None,
        ticketLargeCargoThreshold=str(raw["ticketLargeCargoThreshold"])
        if raw.get("ticketLargeCargoThreshold") is not None
        else None,
        quoteTimeId=str(current["quoteTimeId"])
        if current.get("quoteTimeId") not in (None, "")
        else None,
        sellQuoteTimeId=str(current["sellQuoteTimeId"])
        if current.get("sellQuoteTimeId") not in (None, "")
        else None,
        priceType=str(current["type"]) if current.get("type") is not None else None,
        priceStartTime=str(current["startTime"])
        if current.get("startTime") not in (None, "")
        else None,
        priceEndTime=str(current["endTime"])
        if current.get("endTime") not in (None, "")
        else None,
        priceDateText=str(current["dateText"])
        if current.get("dateText") not in (None, "")
        else None,
        description=_truncate_text(raw.get("description"), 240),
    )


def summarize_export_result(
    *,
    payload: dict[str, Any],
    download_url: str,
    quote_time_ids: str,
    product_line: str,
    customer_id: str | None = None,
) -> ExportPriceResult:
    relative = payload.get("data")
    return ExportPriceResult(
        resultMsg=str(payload.get("resultMsg") or ""),
        relativePath=str(relative) if relative is not None else None,
        downloadUrl=download_url or None,
        quoteTimeIds=quote_time_ids,
        customerId=customer_id,
        productLine=product_line,
    )


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truncate_text(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"
