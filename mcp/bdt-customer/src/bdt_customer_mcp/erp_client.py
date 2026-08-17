"""ERP 配置与 HTTP 客户端。"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from bdt_customer_mcp.auth import build_auth_headers, require_config

# 优先加载 mcp/bdt-customer/.env，避免 Cursor 启动 cwd 不在项目目录
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
    timeout: float = 30.0

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


@lru_cache(maxsize=1)
def get_settings() -> ErpSettings:
    return ErpSettings()


class ErpClient:
    """调用八达通 ERP 第三方开放接口。"""

    LIST_API = "crm/dealCustomer/listData"
    VIEW_API = "crm/dealCustomer/getViewInfo"
    FREIGHT_TREND_API = "oms/order/freightTrendData"
    FOLLOW_SAVE_API = "crm/customerFollow/save"
    CUSTOMER_ANALYSIS_API = "oms/customerOutboundSummary/getCustomerAnalysisData"

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
            # 903: QPS 限流
            if data.get("resultType") in (903, "903"):
                last_error = RuntimeError(str(data.get("resultMsg") or "QPS限流"))
                time.sleep(0.8 * (attempt + 1))
                # 限流后需重新签名（时间戳变化）
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

    def list_customers_by_number(
        self,
        number: str,
        *,
        customer_type: str = "PRIVATE",
        state: str | None = None,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self.list_customers(
            customer_type=customer_type,
            state=state,
            page_size=page_size,
            key_type="number",
            key_word=number.strip(),
        )

    def list_customers(
        self,
        *,
        customer_type: str = "PRIVATE",
        state: str | None = None,
        current_page: int = 1,
        page_size: int = 25,
        key_type: str | None = None,
        key_word: str | None = None,
        sort_name: str = "lastOrderDate",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """分页拉取客户列表。不传 keyWord 时拉取范围内全量列表。"""
        payload: dict[str, Any] = {
            "sortname": sort_name,
            "sortorder": sort_order,
            "type": customer_type,
            "currentPage": current_page,
            "pageSize": page_size,
        }
        if state:
            payload["state"] = state
        if key_type and key_word:
            payload["keyType"] = key_type
            payload["keyWord"] = key_word
        return self._post(self.LIST_API, payload)

    def get_view_info(self, customer_id: str) -> dict[str, Any]:
        return self._post(self.VIEW_API, {"id": customer_id})

    def get_freight_trend_data(
        self,
        *,
        deal_customer_id: str,
        start_date: str,
        end_date: str,
        from_type: str = "IN",
        sales_person_id: str = "",
        current_page: int = 1,
        page_size: int = 500,
    ) -> dict[str, Any]:
        """查询客户货量/出库（入库）趋势。fromType: IN=入库趋势。"""
        return self._post(
            self.FREIGHT_TREND_API,
            {
                "fromType": from_type,
                "startDate": start_date,
                "endDate": end_date,
                "salesPersonId": sales_person_id,
                "dealCustomerId": deal_customer_id,
                "currentPage": current_page,
                "pageSize": page_size,
            },
        )

    def save_customer_follow(
        self,
        *,
        deal_customer_id: str,
        content: str,
        customer_name: str,
        follow_status: str = "FOLLOW_UP",
        follower_name: str = "",
        save_last_content: int = 1,
        key_follow: bool = False,
        exclusive_follow: bool = False,
    ) -> dict[str, Any]:
        """给客户写跟进记录。"""
        payload: dict[str, Any] = {
            "dealCustomer.id": deal_customer_id,
            "saveLastContent": save_last_content,
            "content": content,
            "customerName": customer_name,
            "followStatus": follow_status,
            "keyFollow": key_follow,
            "exclusiveFollow": exclusive_follow,
        }
        if follower_name:
            payload["name"] = follower_name
        return self._post(self.FOLLOW_SAVE_API, payload)

    def get_customer_analysis_data(
        self,
        *,
        start_date: str,
        end_date: str,
        date_type: str = "month",
        summary_type: str = "in",
        sales_person_id: str = "",
        belong_org_long_number: str = "",
        key_word: str = "",
        product_line: str = "",
        product_id: str = "",
        current_page: int = 1,
        page_size: int = 100,
        sort_name: str = "orders",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """客户下单分析（票数/重量/体积/总业绩 revenue）。

        sort_name 常用：orders / revenue / weight / volume；
        按总业绩排名传 sort_name=revenue 且 sort_order=desc。
        """
        return self._post(
            self.CUSTOMER_ANALYSIS_API,
            {
                "startDate": start_date,
                "endDate": end_date,
                "dateType": date_type,
                "productLine": product_line,
                "productId": product_id,
                "belongOrgLongNumber": belong_org_long_number,
                "salesPersonId": sales_person_id,
                "keyWord": key_word,
                "summaryType": summary_type,
                "currentPage": current_page,
                "pageSize": page_size,
                "sortname": sort_name,
                "sortorder": sort_order,
            },
        )
