# 八达通轨迹查询 PRD

## 需求背景

业务侧需要基于永利通八达通公开查询能力，按追踪单号快速查看物流轨迹，并输出可视化报告，便于客服 / 运营在 Cursor Agent 中直接调用。

## 目标

1. 提供可安装的 Cursor Skill：`bdt-tracking`
2. 根据追踪单号调用八达通接口查询轨迹
3. 生成独立 HTML 轨迹报告文件

## 用户场景

- 客服拿到客户追踪号，要求 Agent「查八达通轨迹」
- 运营批量核对 1~N 个单号并下载 HTML 报告

## 需求明细

### 查询

- 输入：一个或多个追踪单号 / 运单号
- 接口：`POST https://8dt.com/api/tracking/query`
- 请求体：`{"trackingNumbers":["..."]}`

### 报告

- 输出形态：HTML 文件（自包含 CSS）
- 内容：运单摘要、流程节点、轨迹时间线
- 未命中单号：在报告中明确标记

## 参考 CURL

```bash
curl --url 'https://8dt.com/api/tracking/query' \
  -H 'accept: application/json' \
  -H 'content-type: application/json' \
  -H 'origin: https://www.8dt.com' \
  -H 'referer: https://www.8dt.com/' \
  --data-raw '{"trackingNumbers":["1ZC23F680420753718"]}'
```

## 验收标准

- [ ] `skills/bdt-tracking/SKILL.md` 可被 `npx skills` 识别
- [ ] `python3 scripts/query_tracking.py <单号> -o report.html` 可生成报告
- [ ] 报告包含状态、流程节点与轨迹明细
- [ ] README 提供对外安装命令
