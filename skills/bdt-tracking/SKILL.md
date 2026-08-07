---
name: bdt-tracking
description: >-
  Query Yonglitong Badatong (八达通 / 8dt.com) logistics tracking by tracking
  number and generate a polished HTML trajectory report. Use when the user asks
  to查八达通轨迹、查永利通运单、查询 BDT / 8dt tracking、生成轨迹报告, or
  provides a tracking/waybill number for Badatong lookup.
---

# 八达通轨迹查询（bdt-tracking）

根据追踪单号调用八达通公开查询接口，生成可打开的 HTML 轨迹报告。

## When to use

- 用户要查永利通 / 八达通 / 8dt 物流轨迹
- 用户给出追踪号、运单号、转单号，要求查轨迹或出报告
- 用户提到 BDT 单号、生成轨迹 HTML

## Workflow

1. 收集一个或多个单号；缺失时先向用户索要。
2. 定位本 Skill 目录下的脚本并执行（优先相对本文件路径）：

```bash
python3 scripts/query_tracking.py <TRACKING_NUMBER> [MORE...] -o <OUTPUT.html>
```

多单号示例：

```bash
python3 scripts/query_tracking.py 1ZC23F680420753718 BDT7603080SZ -o ./reports/tracking.html
```

需要保留原始响应时加 `--json`：

```bash
python3 scripts/query_tracking.py 1ZC23F680420753718 -o ./report.html --json ./report.json
```

3. 脚本成功后，把 **HTML 绝对路径** 告知用户，并简要说明命中条数与最新状态。
4. 不要在对话里大段粘贴完整轨迹；报告以 HTML 文件为准。若用户明确要求摘要，只给状态、最新事件、最新时间。

## Script behavior

- 请求：`POST https://8dt.com/api/tracking/query`
- Body：`{"trackingNumbers":["..."]}`
- 依赖：仅 Python 3 标准库（`urllib` / `json` / `html`）
- 输出：自包含 HTML（流程节点 `flowLayout` + 明细 `timeline`）
- 未命中单号：报告中标记「未找到」，进程仍返回 0（只要接口调用成功）

## Constraints

- 不要手写或改写 curl 去猜字段；统一跑 `scripts/query_tracking.py`。
- 不要把接口响应里的无关调试信息塞进回复。
- 接口为站点公开查询能力，注意合理频率；失败时原样展示脚本 stderr。
- 若脚本路径因安装位置变化找不到，先在 Skill 根目录（含本 `SKILL.md` 的目录）执行。

## Install

本 Skill 位于多 Skill 仓库的 `skills/bdt-tracking/`。

安装全部 Skills：

```bash
npx skills add <owner>/bdt_silks -g -y
```

只安装本 Skill：

```bash
npx skills add <owner>/bdt_silks --skill bdt-tracking -g -y
```

本地开发验证：

```bash
npx skills add /absolute/path/to/bdt_silks --skill bdt-tracking -g -y
```
