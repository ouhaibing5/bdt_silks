# 八达通客户查询 MCP Server

基于第三方签名鉴权，查询永利通八达通 ERP 客户信息、结算账户、货量趋势与跟进记录。

支持通过 **`npx @ouhaibing/customer-mcp`** 一键启动（Node 启动器 + Python MCP 实现）。

## 功能

| Tool | 说明 |
|------|------|
| `list_my_customers` | 分页拉取私海/成交客户列表（粗筛） |
| `build_followup_list` | 基于列表字段打分，生成多维跟进清单 |
| `get_customer_by_number` | 按客户编号查客户摘要 |
| `get_customer_accounts` | 按编号或客户 ID 查各业务结算账户 / 余额 |
| `get_customer_overview` | 一次返回客户摘要 + 结算账户 |
| `get_customer_freight_trend` | 按日期区间查客户货量/出库趋势 |
| `get_customer_order_analysis` | 客户下单分析（票数/重量/体积/总业绩）；`sortName=revenue` 按总业绩排名 |
| `save_customer_follow` | 给客户写跟进记录 |

## 快速开始（npx）

前提：本机有 **Node.js ≥ 18**，以及 **uv** 或 **Python 3.10+**（启动器会自动准备依赖）。

### 发布到 npm 后

```bash
npx -y @ouhaibing/customer-mcp
```

Cursor `mcp.json`：

```json
{
  "mcpServers": {
    "bdt-customer": {
      "command": "npx",
      "args": ["-y", "@ouhaibing/customer-mcp"],
      "env": {
        "BDT_ERP_BASE_URL": "https://erptestdev.8dt.com/supply/",
        "BDT_ERP_SECRET": "your-secret",
        "BDT_ERP_CLIENT_ID": "your-client-id",
        "BDT_ERP_CU_ID": "your-cu-id",
        "BDT_ERP_USER_ID": "your-user-id",
        "BDT_ERP_DC": "your-dc"
      }
    }
  }
}
```

> 当前 npm 包名：`@ouhaibing/customer-mcp`。

### 本地未发布时

```bash
npx -y /absolute/path/to/bdt_silks/mcp/bdt-customer
```

## 环境变量

可在 Cursor MCP 配置页 / `mcp.json` 的 `env` 中设置（推荐），也可使用 `.env`。

| 变量 | 对应第三方参数 | 说明 |
|------|----------------|------|
| `BDT_ERP_BASE_URL` | - | 默认测试环境 `https://erptestdev.8dt.com/supply/` |
| `BDT_ERP_SECRET` | secret | 第三方 secret |
| `BDT_ERP_CLIENT_ID` | thirdClientId | 客户端 ID |
| `BDT_ERP_CU_ID` | thirdCuId | 控制单元 |
| `BDT_ERP_USER_ID` | thirdUserId | 用户 |
| `BDT_ERP_DC` | thirdDc | 数据中心 |

## 发布 npm（维护者）

```bash
cd mcp/bdt-customer
npm login --registry https://registry.npmjs.org/
npm publish --access public
```

发布后用户即可：

```bash
npx -y @ouhaibing/customer-mcp
```

## 本地开发（Python）

```bash
cd mcp/bdt-customer
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
bdt-customer-mcp
```

或用 uv：

```bash
uv sync --extra dev
uv run bdt-customer-mcp
```

## 鉴权说明

签名算法对齐 `demo.java`：

1. 将 `secret, thirdClientId, thirdtimestamp, thirdCuId, thirdUserId, thirdDc, apiPath` 字典序排序
2. 拼接后做 SHA1 hex，写入请求头 `djthirdsign`
3. `apiPath` 不含 host 与 query（例如 `crm/dealCustomer/listData`）

## 接口

- `POST crm/dealCustomer/listData?djrqformat=pcjson`
- `POST crm/dealCustomer/getViewInfo?djrqformat=pcjson`
- `POST oms/order/freightTrendData?djrqformat=pcjson`
- `POST crm/customerFollow/save?djrqformat=pcjson`

返回已脱敏，不含身份证号、`apiToken`、工商 `businessInfo` 原文等敏感字段。
