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


def _person_name(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        return str(name) if name is not None else None
    return None


class CustomerSummary(CamelModel):
    id: str
    number: str
    company_name: str | None = Field(default=None, alias="companyName")
    company_short_name: str | None = Field(default=None, alias="companyShortName")
    state: str | None = None
    level: str | None = None
    customer_segment: str | None = Field(default=None, alias="customerSegment")
    category_type_names: str | None = Field(default=None, alias="categoryTypeNames")
    assigned_sales_name: str | None = Field(default=None, alias="assignedSalesName")
    assigned_org_name: str | None = Field(default=None, alias="assignedOrgName")
    credit_code: str | None = Field(default=None, alias="creditCode")
    legal_person: str | None = Field(default=None, alias="legalPerson")
    company_address: str | None = Field(default=None, alias="companyAddress")
    open_date: str | None = Field(default=None, alias="openDate")
    last_order_date: str | None = Field(default=None, alias="lastOrderDate")
    arrears_days: str | None = Field(default=None, alias="arrearsDays")
    rmb_balance: float | None = Field(default=None, alias="rmbBalance")
    usd_balance: float | None = Field(default=None, alias="usdBalance")
    hkd_balance: float | None = Field(default=None, alias="hkdBalance")


class SettlementAccount(CamelModel):
    id: str | None = None
    system_code: str | None = Field(default=None, alias="systemCode")
    business_type: str | None = Field(default=None, alias="businessType")
    business_type_code: str | None = Field(default=None, alias="businessTypeCode")
    payment_method: str | None = Field(default=None, alias="paymentMethod")
    payment_method_code: str | None = Field(default=None, alias="paymentMethodCode")
    rmb_balance: float | None = Field(default=None, alias="rmbBalance")
    usd_balance: float | None = Field(default=None, alias="usdBalance")
    hkd_balance: float | None = Field(default=None, alias="hkdBalance")
    credit_limit: float | None = Field(default=None, alias="creditLimit")
    arrears_days: int | float | None = Field(default=None, alias="arrearsDays")
    status: int | None = None
    financial_person_name: str | None = Field(default=None, alias="financialPersonName")
    client_service_name: str | None = Field(default=None, alias="clientServiceName")


class CustomerAccountsResult(CamelModel):
    customer_id: str = Field(alias="customerId")
    number: str | None = None
    company_name: str | None = Field(default=None, alias="companyName")
    accounts: list[SettlementAccount]


class CustomerOverview(CamelModel):
    customer: CustomerSummary
    accounts: list[SettlementAccount]


class FreightTrendPoint(CamelModel):
    finance_date: str | None = Field(default=None, alias="financeDate")
    order_count: float | None = Field(default=None, alias="orderCount")
    total_package_count: float | None = Field(default=None, alias="totalPackageCount")
    total_actual_weight: float | None = Field(default=None, alias="totalActualWeight")
    total_charged_weight: float | None = Field(default=None, alias="totalChargedWeight")
    total_goods_volume: float | None = Field(default=None, alias="totalGoodsVolume")
    total_revenue: float | None = Field(default=None, alias="totalRevenue")


class FreightTrendSummary(CamelModel):
    order_count: float = Field(default=0, alias="orderCount")
    total_package_count: float = Field(default=0, alias="totalPackageCount")
    total_actual_weight: float = Field(default=0, alias="totalActualWeight")
    total_charged_weight: float = Field(default=0, alias="totalChargedWeight")
    total_goods_volume: float = Field(default=0, alias="totalGoodsVolume")
    total_revenue: float = Field(default=0, alias="totalRevenue")
    day_count: int = Field(default=0, alias="dayCount")


class FreightTrendResult(CamelModel):
    deal_customer_id: str = Field(alias="dealCustomerId")
    number: str | None = None
    company_name: str | None = Field(default=None, alias="companyName")
    from_type: str = Field(alias="fromType")
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    summary: FreightTrendSummary
    items: list[FreightTrendPoint]


def summarize_customer(item: dict[str, Any]) -> CustomerSummary:
    assigned_org = item.get("assignedOrg") or {}
    return CustomerSummary(
        id=str(item.get("id") or ""),
        number=str(item.get("number") or ""),
        companyName=item.get("companyName"),
        companyShortName=item.get("companyShortName"),
        state=_enum_name(item.get("state")),
        level=_enum_name(item.get("level")),
        customerSegment=_enum_name(item.get("customerSegment")),
        categoryTypeNames=item.get("categoryTypeNames"),
        assignedSalesName=_person_name(item.get("assignedSales")),
        assignedOrgName=assigned_org.get("name") if isinstance(assigned_org, dict) else None,
        creditCode=item.get("creditCode"),
        legalPerson=item.get("legalPerson"),
        companyAddress=item.get("companyAddress"),
        openDate=item.get("openDate"),
        lastOrderDate=item.get("lastOrderDate"),
        arrearsDays=item.get("arrearsDaysStr") or item.get("arrearsDays"),
        rmbBalance=_as_float(item.get("rmbBalance")),
        usdBalance=_as_float(item.get("usdBalance")),
        hkdBalance=_as_float(item.get("hkdBalance")),
    )


def summarize_account(item: dict[str, Any]) -> SettlementAccount:
    business_type = item.get("businessType") or {}
    payment_method = item.get("paymentMethod") or {}
    return SettlementAccount(
        id=str(item["id"]) if item.get("id") is not None else None,
        systemCode=item.get("systemCode"),
        businessType=_enum_name(business_type),
        businessTypeCode=(
            str(business_type.get("value"))
            if isinstance(business_type, dict) and business_type.get("value") is not None
            else None
        ),
        paymentMethod=_enum_name(payment_method),
        paymentMethodCode=(
            str(payment_method.get("value"))
            if isinstance(payment_method, dict) and payment_method.get("value") is not None
            else None
        ),
        rmbBalance=_as_float(item.get("rmbBalance")),
        usdBalance=_as_float(item.get("usdBalance")),
        hkdBalance=_as_float(item.get("hkdBalance")),
        creditLimit=_as_float(item.get("creditLimit")),
        arrearsDays=item.get("arrearsDays"),
        status=item.get("status"),
        financialPersonName=_person_name(item.get("financialPerson")),
        clientServiceName=_person_name(item.get("clientService")),
    )


def summarize_freight_point(item: dict[str, Any]) -> FreightTrendPoint:
    return FreightTrendPoint(
        financeDate=item.get("financeDate"),
        orderCount=_as_float(item.get("order_count")),
        totalPackageCount=_as_float(item.get("total_package_count")),
        totalActualWeight=_as_float(item.get("total_actual_weight")),
        totalChargedWeight=_as_float(item.get("total_charged_weight")),
        totalGoodsVolume=_as_float(item.get("total_goods_volume")),
        totalRevenue=_as_float(item.get("total_revenue")),
    )


def summarize_freight_trend(items: list[dict[str, Any]]) -> tuple[FreightTrendSummary, list[FreightTrendPoint]]:
    points = [summarize_freight_point(item) for item in items]
    summary = FreightTrendSummary(
        orderCount=sum(p.order_count or 0 for p in points),
        totalPackageCount=sum(p.total_package_count or 0 for p in points),
        totalActualWeight=sum(p.total_actual_weight or 0 for p in points),
        totalChargedWeight=sum(p.total_charged_weight or 0 for p in points),
        totalGoodsVolume=sum(p.total_goods_volume or 0 for p in points),
        totalRevenue=sum(p.total_revenue or 0 for p in points),
        dayCount=len(points),
    )
    return summary, points


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
