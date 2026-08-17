---
name: bdt-crm
description: >-
  Yonglitong Badatong (八达通) CRM sales assistant for cross-border logistics.
  Builds multi-dimensional follow-up lists, drafts follow notes, quotes logistics
  products, exports price Excel, and follows sales SOP for 国际快递/专线/FBA.
  Use when the user asks for 销售跟进清单、私海客户巡检、客户分层、跟进建议、
  写跟进记录、产品查价、客户报价、导出价格表、bdt crm 助手, or sales SOP.
---

# 八达通 CRM 销售助手（bdt-crm）

面向跨境物流销售的日常作业助手。默认通过 MCP **`bdt-customer`**（客户/跟进）与 **`bdt-product`**（产品查价/报价导出）取数，按 SOP 产出可执行跟进与报价动作。

## When to use

- 「生成本周/今日跟进清单」
- 「私海客户谁该跟」
- 「这个客户怎么跟、写条跟进」
- 「按沉默/欠款/交叉销售分层」
- 「查一下 GJ01 / 加拿大DHL 指导价」
- 「导出客户报价 Excel / 发价格表」

## Prerequisites

确认 Cursor 已启用 MCP：

### bdt-customer（客户）

| Tool | 用途 |
|------|------|
| `list_my_customers` | 分页拉私海列表（粗筛） |
| `build_followup_list` | 多维打分跟进清单（默认不批量拉货量） |
| `get_customer_by_number` / `get_customer_overview` | 单客深挖；拿客户 ID |
| `get_customer_freight_trend` | 仅 Top 客户看货量趋势 |
| `save_customer_follow` | 写跟进记录 |

### bdt-product（产品 / 报价）

| Tool | 用途 |
|------|------|
| `search_product_prices` | 按编号/名称查指导价候选 |
| `get_product_price_detail` | 查重量段明细与渠道说明 |
| `export_product_prices` | 导出指导价 Excel（OSS 链接） |
| `list_customer_product_quotes` | 查客户已开通/关联产品报价 |
| `export_customer_product_quotes` | 导出客户报价 Excel（OSS 链接） |

详细 SOP 见 [sop.md](sop.md)。

## Workflow A — 跟进清单（标准作业）

```text
跟进任务进度：
- [ ] 1. 明确范围（私海 / 状态 / 页数）
- [ ] 2. build_followup_list 粗筛
- [ ] 3. 输出分组清单 + 建议
- [ ] 4. 仅对用户指定的 Top 客户深挖
- [ ] 5. 用户确认后 save_customer_follow
```

### Step 1 — 定范围

缺省假设：
- `customer_type=PRIVATE`
- `state=COMPDEALED`（合作中）；若用户要未下单客户，再跑一遍 `NOORDER`
- `max_pages=3`，`top_n=20`，`enrich_top_n=0`

### Step 2 — 粗筛（必做）

```text
build_followup_list(
  state="COMPDEALED",
  max_pages=3,
  page_size=25,
  top_n=20,
  enrich_top_n=0
)
```

**禁止**对全量客户循环调用 `get_customer_freight_trend`。

### Step 3 — 输出格式

用中文输出，结构固定：

1. **范围摘要**：拉取页数、评分人数、高分分布  
2. **今日必跟**（Top 10）：编号、公司、得分、原因、建议话术  
3. **风险客户**：欠款/负余额  
4. **沉默客户**：久未出货  
5. **机会客户**：业务未覆盖 / 高价值沉默  
6. **下一步**：询问是否深挖某编号、查价/导出报价，或直接写跟进  

### Step 4 — 深挖（可选，限量）

仅当用户点名或明确「深挖 TopN」时：

1. `get_customer_overview(number)`
2. 必要时 `get_customer_freight_trend(start_date, end_date, number=...)`（近 90 天即可）

### Step 5 — 写跟进（需确认）

用户确认内容后调用 `save_customer_follow`。跟进正文建议包含：

- 联系方式/结果
- 客户诉求（渠道/时效/价格/目的国）
- 已报价产品编号或已发价格表
- 下一步动作与时间

未获用户确认前不要写入 ERP。

## Workflow B — 产品查价与报价导出

```text
报价任务进度：
- [ ] 1. 明确产品线（EXPRESS / SPECIAL_LINE）与关键字
- [ ] 2. 指导价：search → detail / export
- [ ] 3. 客户价：先拿客户 ID → list → export
- [ ] 4. 把 downloadUrl 交给用户；跟进里记一笔（需确认）
```

### B1 — 公开指导价

1. `search_product_prices(key_word=..., product_line="EXPRESS")`
2. 需要重量段时：`get_product_price_detail(quote_time_id, product_id=supplyProductId)`
3. 需要 Excel：`export_product_prices(quote_time_ids=...)` 或直接 `key_word=...`
4. 输出：产品名、编号、截止日、关键重量段摘要、`downloadUrl`

### B2 — 客户专属报价

1. `get_customer_by_number(number)` → 取 `id` 作为 `customer_id`
2. `list_customer_product_quotes(customer_id, product_line=..., key_word=...)`
3. 仅 `quoteTimeId` 非空的可导出
4. `export_customer_product_quotes(customer_id, quote_time_ids=...)`  
   或按编号：`product_numbers="DHL-US,GJ01"`
5. 把 `downloadUrl` 发给用户；询问是否写跟进

**注意：** 客户列表可能很大，默认 `page_size≤50`，先用 `key_word` 收窄；禁止无过滤全量导出上百条。

## Constraints

- 跟进清单优先 `build_followup_list`，不要手写打分逻辑绕过工具。
- 报价优先 `bdt-product`，不要手拼 ERP curl。
- 不在对话中粘贴完整原始 JSON / 整张价卡；只给结构化摘要 + 下载链接。
- 不暴露密钥、身份证号、apiToken。
- 销售建议要可执行、可验证，避免空泛「加强沟通」。
