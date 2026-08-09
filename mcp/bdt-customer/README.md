# 八达通客户查询 MCP Server

基于第三方签名鉴权，查询永利通八达通 ERP 客户信息、结算账户、货量趋势与跟进记录。

支持通过 **`npx @dingjian/customer-mcp`** 一键启动（Node 启动器 + Python FastMCP 实现）。

## 架构说明

这是标准的 **MCP Server（stdio transport）**，不是 HTTP 中间件：

| 层级 | 路径 | 职责 |
|------|------|------|
| Host 适配 | `bin/cli.mjs` | npx 入口；准备 Python 环境；把 stdio 交给 Python |
| MCP 协议层 | `src/bdt_customer_mcp/server.py` | FastMCP + `@mcp.tool()`，stdio JSON-RPC |
| 业务/客户端 | `erp_client.py` / `followup.py` / `schemas.py` | ERP HTTP、打分、响应裁剪 |
| 鉴权 | `auth.py` | 第三方签名头 |

Cursor / Claude Desktop 通过 `command + args` 拉起进程，走 **stdin/stdout** 做 `initialize` → `tools/list` → `tools/call`。不要在启动器里往 **stdout** 打日志（会破坏协议）。

## 功能

| Tool | 说明 |
|------|------|
| `list_my_customers` | 分页拉取私海/成交客户列表（粗筛） |
| `build_followup_list` | 基于列表字段打分，生成多维跟进清单 |
| `get_customer_by_number` | 按客户编号查客户摘要 |
| `get_customer_accounts` | 按编号或客户 ID 查各业务结算账户 / 余额 |
| `get_customer_overview` | 一次返回客户摘要 + 结算账户 |
| `get_customer_freight_trend` | 按日期区间查客户货量/出库趋势 |
| `save_customer_follow` | 给客户写跟进记录 |

## 快速开始（npx）

前提：本机有 **Node.js ≥ 18**。首次启动会自动把 `uv` 与 Python 依赖装到用户缓存目录（`~/.cache/bdt-customer-mcp`），一般不需要本机预装 Python。

### 发布到 npm 后

```bash
npx -y @dingjian/customer-mcp@latest
```

Cursor `mcp.json`：

```json
{
  "mcpServers": {
    "bdt-customer": {
      "command": "npx",
      "args": ["-y", "@dingjian/customer-mcp@latest"],
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

> 当前 npm 包名：`@dingjian/customer-mcp`。若 `npm view @dingjian/customer-mcp` 返回 404，说明尚未成功 publish，或 scope/包名不一致，宿主侧「安装/更新」也会失败。

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
| `BDT_CUSTOMER_MCP_CACHE` | - | 可选，覆盖启动器缓存目录 |

缺凭证时：**服务仍会启动并暴露 tools**；调用工具时再返回明确错误（避免 Host 侧 `tools/list` 失败）。

## 发布 npm（维护者）

发布前自检：

```bash
cd mcp/bdt-customer
npm pack --dry-run
npm view @dingjian/customer-mcp version   # 若 404 说明从未发布成功
npm login --registry https://registry.npmjs.org/
npm publish --access public
npm view @dingjian/customer-mcp version   # 应看到新版本
```

注意：

1. npm scope `@dingjian` 需要你对应该组织/用户有 publish 权限。
2. 发布后用 `@latest` 或显式版本，避免客户端命中旧缓存。
3. 仓库地址与 npm `repository` 字段应指向实际 GitHub 仓库。

## 故障排查

| 现象 | 常见原因 | 处理 |
|------|----------|------|
| `npm/npx` 404 | 包未发布或包名错误 | `npm publish --access public`，确认 `npm view` 有版本 |
| Cursor 显示安装/更新失败、无工具 | 进程在 `tools/list` 前退出；或 npx 拉包失败 | 看 MCP 日志；确认 env 配好；升级到 ≥0.2.1 |
| `python -m venv failed` | 旧启动器依赖本机 `python3-venv` | 升级包；新启动器会自动装 uv 到用户缓存 |
| 有工具但调用报缺凭证 | `mcp.json` 的 `env` 未生效 | 检查变量名是否为 `BDT_ERP_*`，重启 MCP |

调试启动器：

```bash
npx -y @dingjian/customer-mcp --version
# 或本地
node ./bin/cli.mjs --version
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
