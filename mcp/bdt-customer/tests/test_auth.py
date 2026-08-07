"""签名算法单测（对齐 demo.java 的排序 + SHA1）。"""

from __future__ import annotations

import hashlib

from bdt_customer_mcp.auth import build_auth_headers, build_signature


def test_build_signature_matches_sorted_sha1() -> None:
    secret = "secret"
    client_id = "client"
    timestamp = "1700000000000"
    cu_id = "cu"
    user_id = "user"
    dc = "dc"
    api_path = "crm/dealCustomer/listData"

    parts = [secret, client_id, timestamp, cu_id, user_id, dc, api_path]
    parts.sort()
    expected = hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()

    actual = build_signature(
        secret=secret,
        third_client_id=client_id,
        third_timestamp=timestamp,
        third_cu_id=cu_id,
        third_user_id=user_id,
        third_dc=dc,
        api_path=api_path,
    )
    assert actual == expected
    assert len(actual) == 40


def test_build_auth_headers_include_signature() -> None:
    headers = build_auth_headers(
        secret="s",
        third_client_id="c",
        third_cu_id="u",
        third_user_id="uid",
        third_dc="d",
        api_path="basedata/basicDataType/simpleTreeData",
        timestamp_ms="1234567890",
    )
    assert headers["thirdtimestamp"] == "1234567890"
    assert headers["thirdClientId"] == "c"
    assert headers["thirdCuId"] == "u"
    assert headers["thirdUserId"] == "uid"
    assert headers["thirdDc"] == "d"
    assert headers["djthirdsign"] == build_signature(
        secret="s",
        third_client_id="c",
        third_timestamp="1234567890",
        third_cu_id="u",
        third_user_id="uid",
        third_dc="d",
        api_path="basedata/basicDataType/simpleTreeData",
    )
