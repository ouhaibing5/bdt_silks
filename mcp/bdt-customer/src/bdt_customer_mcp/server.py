"""八达通客户查询 MCP Server 入口。"""

from __future__ import annotations

import json
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from bdt_customer_mcp.erp_client import ErpClient, get_settings
from bdt_customer_mcp.followup import group_followup_items, score_customer_for_followup
from bdt_customer_mcp.schemas import (
    CustomerAccountsResult,
    CustomerOverview,
    FreightTrendResult,
    summarize_account,
    summarize_customer,
    summarize_freight_trend,
)

mcp = FastMCP(
    "bdt-customer",
    instructions=(
        "查询永利通八达通 ERP 客户信息、结算账户余额、货量趋势；"
        "支持拉取私海客户列表、生成多维跟进清单，以及写跟进记录。"
        "优先使用客户编号（如 DSKJ）。跟进清单默认只基于列表字段打分，不批量拉货量。"
    ),
)


def _client() -> ErpClient:
    """构造 ERP 客户端；凭证缺失时抛出可读错误（供 tools/call 返回）。"""
    try:
        return ErpClient(get_settings())
    except ValueError as exc:
        # 统一成 RuntimeError，避免被部分宿主当成协议层故障
        raise RuntimeError(str(exc)) from exc


def _dump(model: Any) -> str:
    if hasattr(model, "model_dump"):
        payload = model.model_dump(by_alias=True, exclude_none=True)
    else:
        payload = model
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _extract_items(list_payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = list_payload.get("data")
    if isinstance(data, dict):
        items = data.get("items") or []
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    items = list_payload.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _find_customer_raw(
    client: ErpClient,
    number: str,
    *,
    state: str | None = None,
) -> dict[str, Any] | None:
    payload = client.list_customers_by_number(number, state=state)
    items = _extract_items(payload)
    exact = [item for item in items if str(item.get("number") or "").upper() == number.strip().upper()]
    if exact:
        return exact[0]
    if len(items) == 1:
        return items[0]
    if items:
        # 编号模糊命中多条时返回第一条，并在上层提示
        return items[0]
    # 未指定 state 时再放宽一次（不带 state）
    if state is not None:
        return _find_customer_raw(client, number, state=None)
    return None


def _accounts_from_view(view_payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("systemAccountList", "data"):
        value = view_payload.get(key)
        if key == "systemAccountList" and isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if key == "data" and isinstance(value, dict):
            nested = value.get("systemAccountList")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _customer_name_from_view(view_payload: dict[str, Any]) -> tuple[str | None, str | None]:
    data = view_payload.get("data")
    source = data if isinstance(data, dict) else view_payload
    if not isinstance(source, dict):
        return None, None
    number = source.get("number")
    company_name = source.get("companyName")
    return (
        str(number) if number is not None else None,
        str(company_name) if company_name is not None else None,
    )


def _page_meta(list_payload: dict[str, Any]) -> dict[str, Any]:
    data = list_payload.get("data")
    source = data if isinstance(data, dict) else list_payload
    if not isinstance(source, dict):
        return {}
    return {
        "currentPage": source.get("currentPage"),
        "pageCount": source.get("pageCount"),
        "pageSize": source.get("pageSize"),
        "recordCount": source.get("recordCount") or source.get("count"),
        "statMap": {
            key: value
            for key, value in (source.get("statMap") or {}).items()
            if key in {"ALL", "COMPDEALED", "NOORDER", "EXPIRED", "recordCount"}
        },
    }


@mcp.tool()
def list_my_customers(
    state: str = "",
    customer_type: str = "PRIVATE",
    current_page: int = 1,
    page_size: int = 25,
    key_word: str = "",
    key_type: str = "number",
) -> str:
    """分页拉取我的客户列表（私海/成交客户）。默认不拉货量详情，适合做跟进粗筛。

    Args:
        state: 客户状态过滤，可选 COMPDEALED / NOORDER / EXPIRED；空表示不按状态过滤
        customer_type: 客户类型，默认 PRIVATE（私海）
        current_page: 页码，从 1 开始
        page_size: 每页条数，默认 25，最大建议 50
        key_word: 可选关键字（客户编号/名称等）
        key_type: 关键字类型，默认 number；也可试 companyName
    """
    client = _client()
    page = max(int(current_page or 1), 1)
    size = min(max(int(page_size or 25), 1), 100)
    state_filter = state.strip() or None
    keyword = key_word.strip() or None
    ktype = key_type.strip() or "number"

    payload = client.list_customers(
        customer_type=customer_type.strip() or "PRIVATE",
        state=state_filter,
        current_page=page,
        page_size=size,
        key_type=ktype if keyword else None,
        key_word=keyword,
    )
    items = _extract_items(payload)
    customers = [summarize_customer(item) for item in items]
    meta = _page_meta(payload)
    return _dump(
        {
            "found": True,
            "customerType": customer_type,
            "state": state_filter,
            **meta,
            "count": len(customers),
            "customers": [c.model_dump(by_alias=True, exclude_none=True) for c in customers],
        }
    )


@mcp.tool()
def build_followup_list(
    state: str = "COMPDEALED",
    customer_type: str = "PRIVATE",
    max_pages: int = 3,
    page_size: int = 25,
    top_n: int = 20,
    enrich_top_n: int = 0,
    silent_days: int = 30,
    cold_days: int = 60,
) -> str:
    """基于客户列表字段生成多维跟进清单（漏斗粗筛）。默认不批量查询货量，请求可控。

    Args:
        state: 状态过滤，默认 COMPDEALED；可空表示不过滤。也可先分别跑 NOORDER
        customer_type: 默认 PRIVATE
        max_pages: 最多拉取页数，默认 3（约 75 人），防止请求过大
        page_size: 每页条数，默认 25
        top_n: 各分组返回条数上限，默认 20
        enrich_top_n: 对得分最高的 N 个客户补查结算账户摘要；0 表示不深挖
        silent_days: 沉默阈值天数，默认 30
        cold_days: 冷客户阈值天数，默认 60
    """
    client = _client()
    pages = min(max(int(max_pages or 1), 1), 20)
    size = min(max(int(page_size or 25), 1), 50)
    top = min(max(int(top_n or 20), 1), 100)
    enrich_n = min(max(int(enrich_top_n or 0), 0), 20)
    state_filter = state.strip() or None

    raw_items: list[dict[str, Any]] = []
    page_count = 1
    for page in range(1, pages + 1):
        if page > page_count:
            break
        payload = client.list_customers(
            customer_type=customer_type.strip() or "PRIVATE",
            state=state_filter,
            current_page=page,
            page_size=size,
            sort_name="lastOrderDate",
            sort_order="asc",
        )
        # 轻微间隔，降低分页连打触发 QPS 限流概率
        time.sleep(0.35)
        meta = _page_meta(payload)
        try:
            page_count = int(meta.get("pageCount") or 1)
        except (TypeError, ValueError):
            page_count = 1
        batch = _extract_items(payload)
        if not batch:
            break
        raw_items.extend(batch)

    scored = [
        score_customer_for_followup(
            item,
            silent_days=int(silent_days or 30),
            cold_days=int(cold_days or 60),
        )
        for item in raw_items
    ]
    grouped = group_followup_items(scored, top_n=top)

    enrichments: list[dict[str, Any]] = []
    if enrich_n > 0:
        for item in grouped["mustFollowToday"][:enrich_n]:
            cid = str(item.get("id") or "")
            if not cid:
                continue
            try:
                view = client.get_view_info(cid)
                accounts = [summarize_account(acc) for acc in _accounts_from_view(view)]
                enrichments.append(
                    {
                        "id": cid,
                        "number": item.get("number"),
                        "companyName": item.get("companyName"),
                        "accountCount": len(accounts),
                        "accounts": [
                            acc.model_dump(by_alias=True, exclude_none=True) for acc in accounts
                        ],
                    }
                )
            except Exception as exc:  # noqa: BLE001
                enrichments.append(
                    {
                        "id": cid,
                        "number": item.get("number"),
                        "error": str(exc),
                    }
                )

    all_ranked = grouped.pop("allRanked", [])
    score_dist = {
        "gte50": sum(1 for x in all_ranked if (x.get("priorityScore") or 0) >= 50),
        "gte30": sum(1 for x in all_ranked if (x.get("priorityScore") or 0) >= 30),
        "lt30": sum(1 for x in all_ranked if (x.get("priorityScore") or 0) < 30),
    }
    return _dump(
        {
            "found": True,
            "scope": {
                "customerType": customer_type,
                "state": state_filter,
                "pagesFetched": min(pages, page_count),
                "pageSize": size,
                "scoredCount": len(scored),
            },
            "scoreDistribution": score_dist,
            "followupList": grouped,
            "enrichments": enrichments,
            "usageHint": (
                "默认仅用列表字段打分；需要对单客深挖时再调用 get_customer_overview / "
                "get_customer_freight_trend / save_customer_follow。"
            ),
        }
    )


@mcp.tool()
def get_customer_by_number(number: str) -> str:
    """按客户编号查询客户基本信息。

    Args:
        number: 客户编号，例如 DSKJ
    """
    number = number.strip()
    if not number:
        return _dump({"found": False, "message": "请提供客户编号"})

    client = _client()
    raw = _find_customer_raw(client, number)
    if not raw:
        return _dump({"found": False, "number": number, "message": "未找到客户"})

    summary = summarize_customer(raw)
    return _dump({"found": True, "customer": summary})


@mcp.tool()
def get_customer_accounts(number: str = "", customer_id: str = "") -> str:
    """按客户编号或客户 ID 查询各业务结算账户与余额。

    Args:
        number: 客户编号（优先）。为空时可改用 customer_id
        customer_id: 客户 ID（如 KXT_xxx）。number 为空时必填
    """
    client = _client()
    cid = customer_id.strip()
    num = number.strip()
    company_name: str | None = None
    resolved_number: str | None = num or None

    if not cid:
        if not num:
            return _dump({"found": False, "message": "请提供 number 或 customerId"})
        raw = _find_customer_raw(client, num)
        if not raw:
            return _dump({"found": False, "number": num, "message": "未找到客户"})
        cid = str(raw.get("id") or "")
        company_name = raw.get("companyName")
        resolved_number = str(raw.get("number") or num)
        if not cid:
            return _dump({"found": False, "number": num, "message": "客户缺少 id，无法查结算账户"})

    view = client.get_view_info(cid)
    accounts_raw = _accounts_from_view(view)
    view_number, view_company = _customer_name_from_view(view)
    result = CustomerAccountsResult(
        customerId=cid,
        number=resolved_number or view_number,
        companyName=company_name or view_company,
        accounts=[summarize_account(item) for item in accounts_raw],
    )
    return _dump({"found": True, **result.model_dump(by_alias=True, exclude_none=True)})


@mcp.tool()
def get_customer_overview(number: str) -> str:
    """一次返回客户摘要 + 各业务结算账户余额。

    Args:
        number: 客户编号，例如 DSKJ
    """
    number = number.strip()
    if not number:
        return _dump({"found": False, "message": "请提供客户编号"})

    client = _client()
    raw = _find_customer_raw(client, number)
    if not raw:
        return _dump({"found": False, "number": number, "message": "未找到客户"})

    customer = summarize_customer(raw)
    cid = customer.id
    if not cid:
        return _dump({"found": False, "number": number, "message": "客户缺少 id，无法查结算账户"})

    view = client.get_view_info(cid)
    accounts = [summarize_account(item) for item in _accounts_from_view(view)]
    overview = CustomerOverview(customer=customer, accounts=accounts)
    return _dump({"found": True, **overview.model_dump(by_alias=True, exclude_none=True)})


@mcp.tool()
def get_customer_freight_trend(
    start_date: str,
    end_date: str,
    number: str = "",
    deal_customer_id: str = "",
    from_type: str = "IN",
) -> str:
    """查询客户货量趋势（入库/出库量分析）。按日汇总票数、包裹数、实重、计费重、体积、营收。

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD，例如 2026-01-01
        end_date: 结束日期，格式 YYYY-MM-DD，例如 2026-07-01
        number: 客户编号（如 DSKJ）。与 deal_customer_id 二选一，优先编号；编号会自动汇总各业务账户
        deal_customer_id: 成交客户/业务账户 ID（如 T6_xxx、KXT_xxx）。number 为空时必填
        from_type: 数据方向，默认 IN（入库趋势，对应页面出库量分析常用口径）
    """
    start = start_date.strip()
    end = end_date.strip()
    num = number.strip()
    deal_id = deal_customer_id.strip()
    direction = (from_type or "IN").strip().upper() or "IN"

    if not start or not end:
        return _dump({"found": False, "message": "请提供 startDate 与 endDate（YYYY-MM-DD）"})

    client = _client()
    company_name: str | None = None
    resolved_number: str | None = num or None
    query_ids: list[str] = []

    if deal_id:
        query_ids = [deal_id]
    else:
        if not num:
            return _dump({"found": False, "message": "请提供 number 或 dealCustomerId"})
        raw = _find_customer_raw(client, num)
        if not raw:
            return _dump({"found": False, "number": num, "message": "未找到客户"})
        main_id = str(raw.get("id") or "")
        company_name = raw.get("companyName")
        resolved_number = str(raw.get("number") or num)
        if not main_id:
            return _dump({"found": False, "number": num, "message": "客户缺少 id，无法查货量趋势"})
        # 货量接口通常挂在业务账户（T6_/K9_ 等）上，主档 KXT 可能无数据；汇总全部账户
        view = client.get_view_info(main_id)
        account_ids = [
            str(item["id"])
            for item in _accounts_from_view(view)
            if item.get("id") is not None
        ]
        query_ids = []
        for cid in [main_id, *account_ids]:
            if cid and cid not in query_ids:
                query_ids.append(cid)

    merged: dict[str, dict[str, float]] = {}
    used_ids: list[str] = []
    for cid in query_ids:
        payload = client.get_freight_trend_data(
            deal_customer_id=cid,
            start_date=start,
            end_date=end,
            from_type=direction,
        )
        items_raw = _extract_items(payload)
        if not items_raw:
            continue
        used_ids.append(cid)
        for item in items_raw:
            day = str(item.get("financeDate") or "")
            if not day:
                continue
            bucket = merged.setdefault(
                day,
                {
                    "order_count": 0.0,
                    "total_package_count": 0.0,
                    "total_actual_weight": 0.0,
                    "total_charged_weight": 0.0,
                    "total_goods_volume": 0.0,
                    "total_revenue": 0.0,
                },
            )
            for key in bucket:
                value = item.get(key)
                try:
                    bucket[key] += float(value or 0)
                except (TypeError, ValueError):
                    continue

    items_raw = [
        {"financeDate": day, **metrics}
        for day, metrics in sorted(merged.items(), key=lambda x: x[0])
    ]
    summary, items = summarize_freight_trend(items_raw)
    result = FreightTrendResult(
        dealCustomerId=deal_id or (used_ids[0] if used_ids else (query_ids[0] if query_ids else "")),
        number=resolved_number,
        companyName=company_name,
        fromType=direction,
        startDate=start,
        endDate=end,
        summary=summary,
        items=items,
    )
    payload_out = result.model_dump(by_alias=True, exclude_none=True)
    payload_out["queriedDealCustomerIds"] = query_ids
    payload_out["hitDealCustomerIds"] = used_ids
    return _dump({"found": True, **payload_out})


@mcp.tool()
def save_customer_follow(
    content: str,
    number: str = "",
    deal_customer_id: str = "",
    customer_name: str = "",
    follow_status: str = "FOLLOW_UP",
    follower_name: str = "",
    key_follow: bool = False,
    exclusive_follow: bool = False,
    save_last_content: bool = True,
) -> str:
    """给客户写入跟进记录（对应 ERP customerFollow/save）。

    Args:
        content: 跟进内容正文
        number: 客户编号（如 DSKJ）。与 deal_customer_id 二选一
        deal_customer_id: 成交客户/业务账户 ID（如 T6_SKYKING）。number 为空时必填
        customer_name: 客户名称；按编号查询时可不传，自动带出
        follow_status: 跟进状态，默认 FOLLOW_UP
        follower_name: 跟进人姓名（可选，如「管理员」）
        key_follow: 是否重点跟进
        exclusive_follow: 是否专属跟进
        save_last_content: 是否同步更新最近跟进内容，默认 true
    """
    text = content.strip()
    num = number.strip()
    deal_id = deal_customer_id.strip()
    name = customer_name.strip()
    status = (follow_status or "FOLLOW_UP").strip() or "FOLLOW_UP"

    if not text:
        return _dump({"success": False, "message": "请提供跟进内容 content"})

    client = _client()
    resolved_number: str | None = num or None

    if not deal_id:
        if not num:
            return _dump({"success": False, "message": "请提供 number 或 dealCustomerId"})
        raw = _find_customer_raw(client, num)
        if not raw:
            return _dump({"success": False, "number": num, "message": "未找到客户"})
        deal_id = str(raw.get("id") or "")
        if not name:
            name = str(
                raw.get("companyShortName")
                or raw.get("companyName")
                or ""
            )
        resolved_number = str(raw.get("number") or num)
        if not deal_id:
            return _dump({"success": False, "number": num, "message": "客户缺少 id，无法写跟进"})

    if not name:
        return _dump(
            {
                "success": False,
                "message": "请提供 customerName，或改用客户编号以便自动带出名称",
            }
        )

    try:
        resp = client.save_customer_follow(
            deal_customer_id=deal_id,
            content=text,
            customer_name=name,
            follow_status=status,
            follower_name=follower_name.strip(),
            save_last_content=1 if save_last_content else 0,
            key_follow=key_follow,
            exclusive_follow=exclusive_follow,
        )
    except Exception as exc:  # noqa: BLE001 - 暴露给 Agent 可读错误
        return _dump(
            {
                "success": False,
                "dealCustomerId": deal_id,
                "number": resolved_number,
                "customerName": name,
                "message": str(exc),
            }
        )

    result_type = resp.get("resultType")
    success = result_type in (1, "1", True) or str(resp.get("resultMsg") or "").find("成功") >= 0
    return _dump(
        {
            "success": bool(success),
            "dealCustomerId": deal_id,
            "number": resolved_number,
            "customerName": name,
            "followStatus": status,
            "content": text,
            "resultType": result_type,
            "resultMsg": resp.get("resultMsg"),
            "requestId": resp.get("requestId"),
            "data": resp.get("data"),
        }
    )


def main() -> None:
    # 注意：不要在启动阶段因缺凭证直接退出。
    # Cursor / MCP Host 会先发 initialize + tools/list；若进程在握手前崩溃，
    # 宿主会表现为「安装/更新失败」或「获取不到工具」。
    # 凭证校验保留在 ErpClient 构造时（真正调用工具时），错误会以工具返回值暴露。
    try:
        get_settings().validate_credentials()
    except ValueError as exc:
        import sys

        print(f"[bdt-customer-mcp] warning: {exc}", file=sys.stderr)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
