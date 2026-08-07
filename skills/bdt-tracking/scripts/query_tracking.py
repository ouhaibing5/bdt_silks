#!/usr/bin/env python3
"""Query Yonglitong / Badatong (8dt.com) tracking and render an HTML report."""

from __future__ import annotations

import argparse
import html
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_URL = "https://8dt.com/api/tracking/query"
DEFAULT_HEADERS = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "origin": "https://www.8dt.com",
    "referer": "https://www.8dt.com/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
}

STATUS_LABELS = {
    "delivered": "已签收",
    "in_transit": "运输中",
    "pending": "待处理",
    "exception": "异常",
}


def e(value: Any) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def query_tracking(tracking_numbers: list[str]) -> dict[str, Any]:
    payload = json.dumps({"trackingNumbers": tracking_numbers}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers=DEFAULT_HEADERS,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc

    data = json.loads(body)
    if data.get("code") != 200:
        raise RuntimeError(f"API error: code={data.get('code')} message={data.get('message')}")
    return data


def status_badge_class(status: str | None, node_status: str | None) -> str:
    text = (status or "").lower()
    node = (node_status or "").upper()
    if text == "delivered" or node == "SIGNED":
        return "badge-ok"
    if "EXCEPTION" in node or "FAIL" in node:
        return "badge-warn"
    return "badge-info"


def render_flow(flow_layout: list[dict[str, Any]]) -> str:
    if not flow_layout:
        return '<p class="muted">暂无流程节点</p>'

    parts: list[str] = ['<ol class="flow">']
    for step in flow_layout:
        step_type = step.get("type") or "node"
        reached = bool(step.get("reached"))
        current = bool(step.get("current"))
        classes = [step_type, "reached" if reached else "pending"]
        if current:
            classes.append("current")

        label = step.get("labelCn") or step.get("labelEn") or step.get("code") or ""
        sub = step.get("subLabel") or ""
        time_text = step.get("time") or ""
        hours = step.get("hours") or ""

        meta_bits: list[str] = []
        if sub:
            meta_bits.append(e(sub))
        if time_text:
            meta_bits.append(e(time_text))
        if hours and step_type == "connector":
            meta_bits.append(e(hours))

        details_html = ""
        details = step.get("details")
        if isinstance(details, dict) and details:
            rows = "".join(
                f"<li><span>{e(k)}</span><strong>{e(v)}</strong></li>"
                for k, v in details.items()
            )
            details_html = f'<ul class="details">{rows}</ul>'

        parts.append(
            f'<li class="{" ".join(classes)}">'
            f'<div class="dot"></div>'
            f'<div class="card">'
            f'<div class="title">{e(label)}</div>'
            f'<div class="meta">{" · ".join(meta_bits) if meta_bits else "&nbsp;"}</div>'
            f"{details_html}"
            f"</div>"
            f"</li>"
        )
    parts.append("</ol>")
    return "\n".join(parts)


def render_timeline(timeline: list[dict[str, Any]]) -> str:
    if not timeline:
        return '<p class="muted">暂无轨迹明细</p>'

    parts: list[str] = ['<ol class="timeline">']
    for event in timeline:
        parts.append(
            "<li>"
            f'<div class="when">{e(event.get("time"))}</div>'
            f'<div class="what">'
            f"<strong>{e(event.get('eventCn') or event.get('eventEn'))}</strong>"
            f'<span class="loc">{e(event.get("location"))}</span>'
            f"</div>"
            "</li>"
        )
    parts.append("</ol>")
    return "\n".join(parts)


def render_item(item: dict[str, Any]) -> str:
    found = bool(item.get("found"))
    query_number = item.get("queryNumber") or item.get("trackingNumber") or "unknown"
    if not found:
        return f"""
        <section class="shipment missing">
          <header>
            <h2>{e(query_number)}</h2>
            <span class="badge badge-warn">未找到</span>
          </header>
          <p class="muted">该单号在八达通系统中未查询到轨迹。</p>
        </section>
        """

    badge = status_badge_class(item.get("status"), item.get("nodeStatus"))
    status_text = (
        item.get("nodeStatusName")
        or STATUS_LABELS.get(str(item.get("status") or "").lower())
        or item.get("status")
        or "未知"
    )

    meta_rows = [
        ("运单号", item.get("number")),
        ("追踪号", item.get("trackingNumber")),
        ("客户单号", item.get("customerOrderNo")),
        ("转单号", item.get("transferNumber")),
        ("承运商", item.get("carrier")),
        ("产品线", item.get("productLine")),
        ("始发", item.get("origin")),
        ("目的地", item.get("destination")),
        ("最新事件", item.get("latestEventCn") or item.get("latestEventEn")),
        ("最新时间", item.get("latestTime")),
        ("签收日期", item.get("signDate")),
        ("状态天数", item.get("statusDays")),
    ]
    meta_html = "".join(
        f"<div><dt>{e(label)}</dt><dd>{e(value)}</dd></div>"
        for label, value in meta_rows
        if value not in (None, "")
    )

    return f"""
    <section class="shipment">
      <header>
        <div>
          <p class="eyebrow">Tracking Report</p>
          <h2>{e(item.get("number") or query_number)}</h2>
          <p class="sub">{e(item.get("trackingNumber") or query_number)}</p>
        </div>
        <span class="badge {badge}">{e(status_text)}</span>
      </header>
      <dl class="meta-grid">{meta_html}</dl>
      <div class="panels">
        <div>
          <h3>流程节点</h3>
          {render_flow(item.get("flowLayout") or [])}
        </div>
        <div>
          <h3>轨迹明细</h3>
          {render_timeline(item.get("timeline") or [])}
        </div>
      </div>
    </section>
    """


def render_html(payload: dict[str, Any], tracking_numbers: list[str]) -> str:
    items = ((payload.get("data") or {}).get("items")) or []
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    sections = "\n".join(render_item(item) for item in items) or (
        '<p class="muted">接口未返回任何运单数据。</p>'
    )
    numbers = "、".join(e(n) for n in tracking_numbers)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>八达通轨迹报告</title>
  <style>
    :root {{
      --bg: #eef3f6;
      --ink: #10233a;
      --muted: #5b6b7c;
      --card: #ffffff;
      --line: #d5dee7;
      --accent: #0b6e6a;
      --accent-soft: #d4efed;
      --warn: #b45309;
      --warn-soft: #fff1df;
      --ok: #157a45;
      --ok-soft: #def5e7;
      --info: #1d4f91;
      --info-soft: #e2edf8;
      --shadow: 0 18px 50px rgba(16, 35, 58, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Noto Sans SC", "PingFang SC", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(11, 110, 106, 0.12), transparent 36%),
        radial-gradient(circle at top right, rgba(29, 79, 145, 0.10), transparent 30%),
        linear-gradient(180deg, #e7eef4 0%, var(--bg) 48%, #e9f2f1 100%);
      min-height: 100vh;
    }}
    .wrap {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 40px 0 64px;
    }}
    .hero {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: end;
      margin-bottom: 28px;
    }}
    .hero h1 {{
      margin: 8px 0 0;
      font-size: clamp(2rem, 4vw, 3rem);
      letter-spacing: -0.04em;
      line-height: 1.05;
    }}
    .eyebrow, .sub, .muted, .meta, .loc {{
      color: var(--muted);
    }}
    .eyebrow {{
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.72rem;
      font-weight: 600;
    }}
    .stamp {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      box-shadow: var(--shadow);
      min-width: 220px;
    }}
    .stamp strong {{ display: block; margin-top: 6px; font-size: 0.95rem; }}
    .shipment {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      box-shadow: var(--shadow);
      margin-bottom: 24px;
    }}
    .shipment.missing {{ border-color: #e7c3b0; }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 22px;
    }}
    header h2 {{
      margin: 6px 0 4px;
      font-size: 1.8rem;
      letter-spacing: -0.03em;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 8px 14px;
      font-size: 0.85rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-ok {{ background: var(--ok-soft); color: var(--ok); }}
    .badge-info {{ background: var(--info-soft); color: var(--info); }}
    .badge-warn {{ background: var(--warn-soft); color: var(--warn); }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin: 0 0 28px;
    }}
    .meta-grid div {{
      background: #f3f7fa;
      border-radius: 16px;
      padding: 12px 14px;
    }}
    .meta-grid dt {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .meta-grid dd {{
      margin: 0;
      font-weight: 600;
      word-break: break-all;
    }}
    .panels {{
      display: grid;
      grid-template-columns: 1.05fr 1fr;
      gap: 24px;
    }}
    h3 {{
      margin: 0 0 14px;
      font-size: 1rem;
      letter-spacing: 0.02em;
    }}
    .flow, .timeline {{
      list-style: none;
      margin: 0;
      padding: 0;
    }}
    .flow li {{
      display: grid;
      grid-template-columns: 18px 1fr;
      gap: 12px;
      position: relative;
      padding-bottom: 16px;
    }}
    .flow li::before {{
      content: "";
      position: absolute;
      left: 8px;
      top: 18px;
      bottom: 0;
      width: 2px;
      background: var(--line);
    }}
    .flow li:last-child {{ padding-bottom: 0; }}
    .flow li:last-child::before {{ display: none; }}
    .flow .dot {{
      width: 18px;
      height: 18px;
      border-radius: 50%;
      border: 2px solid var(--line);
      background: #fff;
      margin-top: 4px;
      z-index: 1;
    }}
    .flow .reached .dot {{
      background: var(--accent);
      border-color: var(--accent);
    }}
    .flow .current .dot {{
      box-shadow: 0 0 0 5px var(--accent-soft);
    }}
    .flow .connector .card {{
      background: transparent;
      border: 0;
      padding: 0 0 0 2px;
      box-shadow: none;
    }}
    .flow .connector .title {{
      font-size: 0.85rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .flow .card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 14px;
    }}
    .flow .title {{ font-weight: 700; }}
    .flow .meta {{ margin-top: 4px; font-size: 0.82rem; }}
    .details {{
      list-style: none;
      margin: 10px 0 0;
      padding: 0;
      display: grid;
      gap: 6px;
    }}
    .details li {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 0.82rem;
      padding: 0;
    }}
    .details li::before {{ display: none; }}
    .details span {{ color: var(--muted); }}
    .timeline li {{
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 14px;
      padding: 12px 0;
      border-bottom: 1px dashed var(--line);
    }}
    .timeline li:last-child {{ border-bottom: 0; }}
    .timeline .when {{
      font-variant-numeric: tabular-nums;
      font-size: 0.86rem;
      color: var(--muted);
    }}
    .timeline .what {{
      display: grid;
      gap: 4px;
    }}
    .timeline .loc {{ font-size: 0.84rem; }}
    footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.82rem;
    }}
    @media (max-width: 860px) {{
      .hero, header, .panels, .timeline li {{
        grid-template-columns: 1fr;
        display: grid;
      }}
      .hero, header {{ align-items: start; }}
      .stamp {{ min-width: 0; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <p class="eyebrow">永利通 · 八达通</p>
        <h1>物流轨迹报告</h1>
        <p class="muted">查询单号：{numbers}</p>
      </div>
      <div class="stamp">
        <span class="eyebrow">Generated</span>
        <strong>{e(generated_at)}</strong>
      </div>
    </div>
    {sections}
    <footer>数据来源：八达通公开轨迹查询接口（8dt.com）。本报告由 bdt-tracking Skill 自动生成。</footer>
  </div>
</body>
</html>
"""


def default_output_path(tracking_numbers: list[str]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = "_".join(
        "".join(ch if ch.isalnum() else "-" for ch in number).strip("-") or "unknown"
        for number in tracking_numbers[:3]
    )
    if len(tracking_numbers) > 3:
        safe += f"_plus{len(tracking_numbers) - 3}"
    return Path.cwd() / f"bdt-tracking-{safe}-{stamp}.html"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="查询永利通八达通轨迹并生成 HTML 报告",
    )
    parser.add_argument(
        "tracking_numbers",
        nargs="+",
        help="一个或多个追踪单号 / 运单号",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="HTML 输出路径（默认写到当前目录）",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        help="同时保存原始 JSON 到指定路径",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    numbers = [n.strip() for n in args.tracking_numbers if n.strip()]
    if not numbers:
        print("错误：请至少提供一个追踪单号", file=sys.stderr)
        return 2

    try:
        payload = query_tracking(numbers)
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else default_output_path(numbers)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(payload, numbers), encoding="utf-8")

    if args.json_path:
        json_path = Path(args.json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    items = ((payload.get("data") or {}).get("items")) or []
    found = sum(1 for item in items if item.get("found"))
    print(f"查询完成：共 {len(numbers)} 个单号，命中 {found} 条")
    print(f"HTML 报告：{output.resolve()}")
    if args.json_path:
        print(f"JSON 原始数据：{Path(args.json_path).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
