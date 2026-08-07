"""第三方签名鉴权（对齐 demo.java）。"""

from __future__ import annotations

import hashlib
import time
from typing import Mapping


def build_signature(
    *,
    secret: str,
    third_client_id: str,
    third_timestamp: str,
    third_cu_id: str,
    third_user_id: str,
    third_dc: str,
    api_path: str,
) -> str:
    """按字典序拼接后做 SHA1 hex。"""
    parts = [
        secret,
        third_client_id,
        third_timestamp,
        third_cu_id,
        third_user_id,
        third_dc,
        api_path,
    ]
    parts.sort()
    joined = "".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def build_auth_headers(
    *,
    secret: str,
    third_client_id: str,
    third_cu_id: str,
    third_user_id: str,
    third_dc: str,
    api_path: str,
    timestamp_ms: str | None = None,
) -> dict[str, str]:
    """生成第三方开放接口所需请求头。"""
    third_timestamp = timestamp_ms or str(int(time.time() * 1000))
    signature = build_signature(
        secret=secret,
        third_client_id=third_client_id,
        third_timestamp=third_timestamp,
        third_cu_id=third_cu_id,
        third_user_id=third_user_id,
        third_dc=third_dc,
        api_path=api_path,
    )
    return {
        "thirdtimestamp": third_timestamp,
        "thirdClientId": third_client_id,
        "thirdCuId": third_cu_id,
        "thirdUserId": third_user_id,
        "thirdDc": third_dc,
        "djthirdsign": signature,
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


def require_config(values: Mapping[str, str | None], keys: list[str]) -> None:
    missing = [key for key in keys if not (values.get(key) or "").strip()]
    if missing:
        raise ValueError(
            "缺少 ERP 第三方凭证，请配置环境变量: " + ", ".join(missing)
        )
