# SOP-<业务名>-runbook.md 模板

> 用于目标部署 URL 当前网络不可达(需 Tailscale/内网)时的降级交付。
> 网络恢复后照此文档跑一遍,即可产出正式 `docs/SOP-<业务名>.md`。

## 触发条件

- [ ] 已接入 Tailscale / 内网,可 `curl -I <部署URL>` 得到 200/3xx
- [ ] 已确认测试账号可用(不在本文档记录账号密码)

## 已提前搭好的骨架(来自项目文档,无需网络)

### 角色与业务环节

<!-- 从 HANDOVER.md / BUSINESS.md / REQUIREMENTS.md 提炼,格式:
- 角色A:环节1(对应页面?)、环节2(对应页面?)
-->

### 待确认的页面清单

<!-- 列出从文档能猜到的页面/功能,标注"待遍历确认" -->

## 网络恢复后执行

```bash
# 1. 检查 playwright-mcp 是否已配置,优先用 MCP
claude mcp list | grep -i playwright

# 2a. 若已配置 MCP:直接在对话里用 MCP 工具导航/截图/取 accessibility snapshot,
#     按 SKILL.md 步骤 2-5 走。

# 2b. 若未配置,降级用原生脚本。凭据经环境变量传入,不要写进本文件、
#     不要写进 --user/--pass 命令行参数(会落进 shell history 与 ps aux):
SOP_USER='<测试账号,现场输入或从 .env 读取>' \
SOP_PASS='<同上>' \
node <本 skill base directory>/scripts/crawl.mjs \
  --url <部署URL> \
  --out docs/sop-images

# 2c. 关键操作(提交表单、导出报表等)的前/后两张截图,可选传入动作清单:
node <本 skill base directory>/scripts/crawl.mjs \
  --url <部署URL> --out docs/sop-images --actions <动作清单.json>
```

## 产出后自检(同 SKILL.md 步骤 5)

- [ ] 页面矩阵全覆盖
- [ ] 每个功能点有截图,关键操作有前/后两张
- [ ] 至少一个真实使用样例
- [ ] 全文无真实凭据
- [ ] 业务黑话首次出现有解释
- [ ] UTF-8 无乱码
