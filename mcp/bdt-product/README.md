# 八达通物流产品 / 报价 MCP Server

基于第三方签名鉴权，查询永利通八达通 ERP 物流产品指导价、价格明细、客户关联报价，并导出 Excel。

支持通过 **`npx @ouhaibing/product-mcp`** 一键启动（Node 启动器 + Python MCP 实现）。

## 功能

| Tool | 说明 |
|------|------|
| `search_product_prices` | 按产品编号/名称查指导价候选（返回 `quoteTimeId`） |
| `get_product_price_detail` | 查询价格明细（渠道说明 + 重量段） |
| `export_product_prices` | 导出指导价 Excel，返回 OSS 下载链接 |
| `list_customer_product_quotes` | 查询客户关联物流产品 / 报价 |
| `export_customer_product_quotes` | 导出客户报价 Excel，返回 OSS 下载链接 |

## 快速开始（npx）

前提：本机有 **Node.js ≥ 18**，以及 **uv** 或 **Python 3.10+**。

### 发布到 npm 后

```bash
npx -y @ouhaibing/product-mcp
```

Cursor `mcp.json`：

```json
{
  "mcpServers": {
    "bdt-product": {
      "command": "npx",
      "args": ["-y", "@ouhaibing/product-mcp"],
      "env": {
        "BDT_ERP_BASE_URL": "https://erptestdev.8dt.com/supply/",
        "BDT_ERP_SECRET": "your-secret",
        "BDT_ERP_CLIENT_ID": "your-client-id",
        "BDT_ERP_CU_ID": "your-cu-id",
        "BDT_ERP_USER_ID": "your-user-id",
        "BDT_ERP_DC": "your-dc",
        "BDT_ERP_OSS_BASE_URL": "https://erposs.8dt.com/images/"
      }
    }
  }
}
```

### 本地未发布时

```bash
npx -y /absolute/path/to/bdt_silks/mcp/bdt-product
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `BDT_ERP_BASE_URL` | 默认测试环境 `https://erptestdev.8dt.com/supply/` |
| `BDT_ERP_SECRET` | 第三方 secret |
| `BDT_ERP_CLIENT_ID` | thirdClientId |
| `BDT_ERP_CU_ID` | thirdCuId |
| `BDT_ERP_USER_ID` | thirdUserId |
| `BDT_ERP_DC` | thirdDc |
| `BDT_ERP_OSS_BASE_URL` | 导出 Excel 下载前缀，默认 `https://erposs.8dt.com/images/` |

## 业务约定

- `productLine`：`EXPRESS`=国际快递，`SPECIAL_LINE`=小包专线
- `keyWord`：支持产品编号（如 `GJ01`）或产品名称（如 `加拿大DHL6000`）
- 客户报价接口需要 **客户 ID**（`dealCustomerId`），不是客户编号；可先用 `bdt-customer` 按编号换 ID
- 导出返回的是 OSS 相对路径，MCP 会拼成完整 `downloadUrl`
- 客户产品仅当 `quoteTimeId` 非空时可导出

## 本地开发

```bash
cd mcp/bdt-product
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
bdt-product-mcp
```

## 接口

- `POST oms/productPriceDetail/priceQueryListData`
- `POST oms/supplyProduct/getPriceDetailViewInfo`
- `POST oms/supplyProduct/exportPriceData`（指导价 / 客户报价共用）
- `POST oms/supplyProduct/getDealCustomerLogisticsPage`
