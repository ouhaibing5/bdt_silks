# bdt_silks

多模块仓库：Agent Skills + MCP Servers。

## 仓库结构

```text
bdt_silks/
├── README.md
├── skills/
│   ├── bdt-tracking/           # 八达通查轨迹 Skill
│   └── bdt-crm/                # 八达通 CRM 销售助手 Skill
└── mcp/
    ├── bdt-customer/           # 八达通客户 / 跟进 / 货量 MCP
    └── bdt-product/            # 八达通物流产品查价 / 客户报价 MCP
```

后续新 Skill 放在 `skills/<skill-name>/`；新 MCP 放在 `mcp/<service-name>/`。

## Skills

### 安装

```bash
npx skills add <owner>/bdt_silks -g -y
npx skills add <owner>/bdt_silks --skill bdt-crm -g -y
npx skills add <owner>/bdt_silks --skill bdt-tracking -g -y
```

### bdt-tracking

永利通八达通（8dt.com）物流轨迹查询：输入追踪单号，生成 HTML 轨迹报告。

详情见 [skills/bdt-tracking/SKILL.md](skills/bdt-tracking/SKILL.md)。

### bdt-crm

跨境物流销售助手：内置 SOP，配合 MCP 生成多维跟进清单、单客深挖、写跟进记录，以及产品查价 / 导出客户报价。

详情见 [skills/bdt-crm/SKILL.md](skills/bdt-crm/SKILL.md)、[skills/bdt-crm/sop.md](skills/bdt-crm/sop.md)。

## MCP Servers

### bdt-customer

客户列表、跟进清单打分、结算账户、货量趋势、写跟进。

**推荐接入（npx）：**

```json
{
  "mcpServers": {
    "bdt-customer": {
      "command": "npx",
      "args": ["-y", "@ouhaibing/customer-mcp"],
      "env": {
        "BDT_ERP_BASE_URL": "https://erptestdev.8dt.com/supply/",
        "BDT_ERP_SECRET": "...",
        "BDT_ERP_CLIENT_ID": "...",
        "BDT_ERP_CU_ID": "...",
        "BDT_ERP_USER_ID": "...",
        "BDT_ERP_DC": "..."
      }
    }
  }
}
```

本地未发布时：

```bash
npx -y /path/to/bdt_silks/mcp/bdt-customer
```

详情见 [mcp/bdt-customer/README.md](mcp/bdt-customer/README.md)。

### bdt-product

物流产品指导价查询、价格明细、客户关联报价，以及导出 Excel（OSS 下载链接）。

**推荐接入（npx）：**

```json
{
  "mcpServers": {
    "bdt-product": {
      "command": "npx",
      "args": ["-y", "@ouhaibing/product-mcp"],
      "env": {
        "BDT_ERP_BASE_URL": "https://erptestdev.8dt.com/supply/",
        "BDT_ERP_SECRET": "...",
        "BDT_ERP_CLIENT_ID": "...",
        "BDT_ERP_CU_ID": "...",
        "BDT_ERP_USER_ID": "...",
        "BDT_ERP_DC": "...",
        "BDT_ERP_OSS_BASE_URL": "https://bdt-erp.oss-cn-shenzhen.aliyuncs.com"
      }
    }
  }
}
```

本地未发布时：

```bash
npx -y /path/to/bdt_silks/mcp/bdt-product
```

详情见 [mcp/bdt-product/README.md](mcp/bdt-product/README.md)。
