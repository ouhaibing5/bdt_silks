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
    └── bdt-customer/           # 八达通客户 / 跟进 / 货量 MCP
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

跨境物流销售助手：内置 SOP，配合 MCP 生成多维跟进清单、单客深挖、写跟进记录。

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
      "args": ["-y", "@dingjian168/customer-mcp@latest"],
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

若宿主侧「安装 / 更新 / 获取工具」失败：先确认 `npm view @dingjian168/customer-mcp` 能查到版本；再确认 `mcp.json` 已配置 `BDT_ERP_*`。详情见 [mcp/bdt-customer/README.md](mcp/bdt-customer/README.md)。
