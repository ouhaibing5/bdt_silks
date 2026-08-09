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

Skills 通过开源 CLI [`npx skills`](https://github.com/vercel-labs/skills) 安装（不是 npm 包）。  
本仓库已按标准布局放置：`skills/<name>/SKILL.md`（含 YAML frontmatter 的 `name` / `description`）。

### 一条命令安装

```bash
# 先看仓库里有哪些 skill
npx skills add ouhaibing5/bdt_silks --list

# 安装全部（全局，跳过确认）
npx skills add ouhaibing5/bdt_silks -g -y

# 只装某一个
npx skills add ouhaibing5/bdt_silks --skill bdt-crm -g -y
npx skills add ouhaibing5/bdt_silks --skill bdt-tracking -g -y

# 指定给 Cursor
npx skills add ouhaibing5/bdt_silks -g -y -a cursor
```

本地未推送到 GitHub 时：

```bash
npx skills add /absolute/path/to/bdt_silks -g -y
# 或
npx skills add ./skills --skill bdt-tracking -g -y
```

### 让别人也能一条命令安装（关键）

当前仓库是 **private**。别人要装成功，任选其一：

1. **推荐**：把 GitHub 仓库设为 **Public** → 任何人可直接 `npx skills add ouhaibing5/bdt_silks -g -y`
2. 保持私有：安装者本机需已登录 Git（`gh auth login` / SSH key / `GH_TOKEN`），CLI 才会 clone 得到 skills

合并到 `main` 后，安装源默认读默认分支上的 `skills/`。

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
