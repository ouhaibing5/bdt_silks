"""ERP 配置与 HTTP 客户端（物流产品 / 报价）。"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from bdt_product_mcp.auth import build_auth_headers, require_config

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)


class ErpSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BDT_ERP_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "https://erptestdev.8dt.com/supply/"
    secret: str = ""
    client_id: str = ""
    cu_id: str = ""
    user_id: str = ""
    dc: str = ""
    timeout: float = 60.0
    oss_base_url: str = "https://erposs.8dt.com/images/"

    @property
    def timeout_seconds(self) -> float:
        return self.timeout

    def validate_credentials(self) -> None:
        require_config(
            {
                "BDT_ERP_SECRET": self.secret,
                "BDT_ERP_CLIENT_ID": self.client_id,
                "BDT_ERP_CU_ID": self.cu_id,
                "BDT_ERP_USER_ID": self.user_id,
                "BDT_ERP_DC": self.dc,
            },
            [
                "BDT_ERP_SECRET",
                "BDT_ERP_CLIENT_ID",
                "BDT_ERP_CU_ID",
                "BDT_ERP_USER_ID",
                "BDT_ERP_DC",
            ],
        )

    def build_export_download_url(self, relative_or_url: str) -> str:
        """将导出接口返回的相对路径拼成下载地址。

        标准格式：
        https://erposs.8dt.com/images/quote/{cuId}/xxx.xlsx?token
        接口 data 已含 ``quote/{cuId}/...``，此处不再额外拼接 cuId。
        """
        value = (relative_or_url or "").strip()
        if not value:
            return ""
        if value.startswith("http://") or value.startswith("https://"):
            return value
        base = self.oss_base_url.rstrip("/")
        path = value.lstrip("/")
        # 兼容误传已带 images/ 前缀的相对路径
        if path.startswith("images/"):
            path = path[len("images/") :]
        return f"{base}/{path}"


@lru_cache(maxsize=1)
def get_settings() -> ErpSettings:
    return ErpSettings()


def _default_package_list() -> str:
    return json.dumps([{"weight": 0, "length": 0, "width": 0, "height": 0}])


class ErpClient:
    """调用八达通 ERP 物流产品 / 报价接口。"""

    PRICE_QUERY_API = "oms/productPriceDetail/priceQueryListData"
    PRICE_DETAIL_API = "oms/supplyProduct/getPriceDetailViewInfo"
    EXPORT_PRICE_API = "oms/supplyProduct/exportPriceData"
    CUSTOMER_LOGISTICS_API = "oms/supplyProduct/getDealCustomerLogisticsPage"

    def __init__(self, settings: ErpSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.validate_credentials()

    def _url(self, api_path: str) -> str:
        base = self.settings.base_url
        if not base.endswith("/"):
            base += "/"
        return urljoin(base, f"{api_path}?djrqformat=pcjson")

    def _post(self, api_path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = build_auth_headers(
            secret=self.settings.secret,
            third_client_id=self.settings.client_id,
            third_cu_id=self.settings.cu_id,
            third_user_id=self.settings.user_id,
            third_dc=self.settings.dc,
            api_path=api_path,
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                    response = client.post(
                        self._url(api_path), headers=headers, json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.6 * (attempt + 1))
                continue
            if not isinstance(data, dict):
                raise RuntimeError(f"ERP 返回非 JSON 对象: {type(data)}")
            if data.get("resultType") in (903, "903"):
                last_error = RuntimeError(str(data.get("resultMsg") or "QPS限流"))
                time.sleep(0.8 * (attempt + 1))
                headers = build_auth_headers(
                    secret=self.settings.secret,
                    third_client_id=self.settings.client_id,
                    third_cu_id=self.settings.cu_id,
                    third_user_id=self.settings.user_id,
                    third_dc=self.settings.dc,
                    api_path=api_path,
                )
                continue
            return data
        if last_error:
            raise RuntimeError(f"ERP 请求失败: {last_error}") from last_error
        raise RuntimeError("ERP 请求失败")

    def price_query_list_data(
        self,
        *,
        product_line: str = "EXPRESS",
        key_word: str = "",
        item_type: str = "WPX",
        country_id: str = "",
        country_name: str = "",
        warehouse_code: str = "",
        site_id: str = "",
        supply_product_id: str = "",
        customer_id: str = "",
        key_type: str = "",
        weight: str | float | int = "",
        volume: str | float | int = "",
        length: str | float | int = "",
        width: str | float | int = "",
        height: str | float | int = "",
        piece_count: int = 1,
        current_page: int = 1,
        page_size: int = 100,
        sort_name: str = "publishedFreight",
        sort_order: str = "asc",
        package_list: str | None = None,
    ) -> dict[str, Any]:
        """按产品编号/名称查价（指导价候选列表）。"""
        return self._post(
            self.PRICE_QUERY_API,
            {
                "productLine": product_line,
                "itemType": item_type,
                "countryId": country_id,
                "warehouseCode": warehouse_code,
                "siteId": site_id,
                "supplyProductId": supply_product_id,
                "keyType": key_type,
                "keyWord": key_word,
                "customerId": customer_id,
                "sortname": sort_name,
                "sortorder": sort_order,
                "pieceCount": piece_count,
                "weight": weight,
                "volume": volume,
                "length": length,
                "width": width,
                "height": height,
                "packageList": package_list or _default_package_list(),
                "currentPage": current_page,
                "pageSize": page_size,
                "countryName": country_name,
            },
        )

    def get_price_detail_view_info(
        self,
        *,
        quote_time_id: str,
        product_id: str,
        price_type: str = "PUBLISHED",
    ) -> dict[str, Any]:
        """按报价时段 ID + 产品 ID 查询价格明细（含重量段）。"""
        return self._post(
            self.PRICE_DETAIL_API,
            {
                "id": quote_time_id,
                "productId": product_id,
                "priceType": price_type,
            },
        )

    def export_published_price_data(
        self,
        *,
        quote_time_ids: str,
        product_line: str = "EXPRESS",
        key_word: str = "",
        item_type: str = "WPX",
        country_id: str = "",
        country_name: str = "",
        warehouse_code: str = "",
        site_id: str = "",
        supply_product_id: str = "",
        customer_id: str = "",
        key_type: str = "",
        current_page: int = 1,
        page_size: int = 500,
        sort_name: str = "publishedFreight",
        sort_order: str = "asc",
        package_list: str | None = None,
    ) -> dict[str, Any]:
        """导出指导价 Excel（返回 OSS 相对路径）。"""
        return self._post(
            self.EXPORT_PRICE_API,
            {
                "productLine": product_line,
                "itemType": item_type,
                "countryId": country_id,
                "warehouseCode": warehouse_code,
                "siteId": site_id,
                "supplyProductId": supply_product_id,
                "keyType": key_type,
                "keyWord": key_word,
                "customerId": customer_id,
                "sortname": sort_name,
                "sortorder": sort_order,
                "pieceCount": 1,
                "weight": "",
                "volume": "",
                "length": "",
                "width": "",
                "height": "",
                "packageList": package_list or _default_package_list(),
                "currentPage": current_page,
                "pageSize": page_size,
                "quoteTimeIds": quote_time_ids,
                "countryName": country_name,
            },
        )

    def get_deal_customer_logistics_page(
        self,
        *,
        customer_id: str,
        product_line: str = "EXPRESS",
        key_word: str = "",
        key_type: str = "",
        price_type: str = "",
        price_status: str = "START",
        pricing_mode: str = "",
        current_page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """查询客户关联物流产品 / 报价列表。"""
        return self._post(
            self.CUSTOMER_LOGISTICS_API,
            {
                "customerId": customer_id,
                "productLine": product_line,
                "productLines": product_line,
                "keyType": key_type,
                "keyWord": key_word,
                "priceType": price_type,
                "priceStatus": price_status,
                "pricingMode": pricing_mode,
                "currentPage": current_page,
                "pageSize": page_size,
            },
        )

    def export_customer_price_data(
        self,
        *,
        customer_id: str,
        quote_time_ids: str,
        product_line: str = "EXPRESS",
        sell_quote_time_ids: str | None = None,
    ) -> dict[str, Any]:
        """导出客户报价 Excel（返回 OSS 相对路径）。"""
        ids = [part.strip() for part in quote_time_ids.split(",") if part.strip()]
        if sell_quote_time_ids is None:
            sell_quote_time_ids = ",".join("-" for _ in ids) if ids else "-"
        return self._post(
            self.EXPORT_PRICE_API,
            {
                "quoteTimeIds": quote_time_ids,
                "sellQuoteTimeIds": sell_quote_time_ids,
                "customerId": customer_id,
                "productLine": product_line,
            },
        )
