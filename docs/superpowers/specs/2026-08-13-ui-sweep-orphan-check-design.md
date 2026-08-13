# ui-sweep 孤儿功能对账 — Design Spec

- 日期:2026-08-13
- 状态:已获 Tony 确认(设计骨架、API + 前端路由两类都对账)
- 依据:Tony 原话——「功能已经实现了,但是前端没有调用的地方,或者调用的地方失效了。这个问题我认为也需要加到那个 ui 点击的 skill 里面」

## 1. 问题与现有能力的关系

ui-sweep 现有的是**遍历视角**:点遍 UI 上存在的元素,查「点了没反应」(dead)。它是黑盒的,天然查不到「功能实现了但 UI 上根本没有入口」——因为没入口的东西不在 a11y 快照里。

新增**对账视角**:代码侧清单 ∩ 遍历侧实际到达 → 求差集。两个视角互补:

| 视角 | 查什么 | 手段 |
|---|---|---|
| 遍历(现有) | 有按钮、点了没反应 | a11y 快照逐元素点击 + 指纹比对 |
| 对账(本次) | 有功能、没入口 / 入口打不通 | 代码清单 vs `network requests` 实际到达 |

## 2. 三类结论

| 结论 | 判据 | 含义 |
|---|---|---|
| `unreachable` | 在 INVENTORY 里、整轮遍历零触发、不在 exempt、且未被拦截名单间接跳过 | 疑似无 UI 入口(真孤儿候选) |
| `broken-entry` | 遍历触发了,但响应状态 ≥400 | 入口存在但打不通 |
| `exempt` | 命中 exempt 正则 | 预期就没有 UI 入口(webhook/健康检查/内部调度),只计数不报警 |

`note-partial-coverage`:遍历因 restore-failed / miss-not-found 等原因未走完的屏,其相关条目单独标注——**覆盖不全时不得把 unreachable 当结论**(诚实记账,与现有报告模板的「覆盖缺口」一节同源)。

## 3. 引擎改造(sweep.mjs)

### 3.1 config 新增字段(全部可选,不配则整个对账功能静默关闭)

```js
export const INVENTORY = {
  apis: ['GET /api/projects', 'POST /api/projects/:id/archive'],  // 方法 + 路径模式
  routes: ['/dashboard', '/projects/:id'],                        // 前端路由模式
  exempt: [/^POST \/api\/webhooks/, /^GET \/health$/],            // 预期无 UI 入口
}
```

校验:`apis`/`routes` 为字符串数组、`exempt` 为正则数组;类型不符即报错退出(与现有 config 校验同款,不静默空跑)。

### 3.2 采集

- 每屏开始 `agent-browser network requests --clear` 清空;
- 每击后 `agent-browser network requests --json` 取增量,解析出 `{method, url, status}`;
- 归一化:URL → `METHOD /path` 模式,数字/UUID/长 hex 段替换为 `:id`(`/projects/123` → `/projects/:id`);query string 丢弃;
- 累积进 `seenApis`(含最后一次见到的 status);SPA 路由从 `location.pathname` 同样归一化后累积进 `seenRoutes`(每击后取一次,与指纹采集同批,不额外开销)。

### 3.3 差集与自动排除

- `unreachable = INVENTORY.apis − seenApis − exempt − 被拦截名单跳过的元素所对应的条目`;
- **被拦截名单间接跳过的**:引擎已记录 `skipped-denylist` 的元素名,若某 API 只可能由这些元素触发,无法自动判定 → 采取保守策略:在报告里把「本轮拦截未点的元素数」与 unreachable 清单并列展示,并在判读指南里点明"先排除这一类";
- `broken-entry`:seenApis 中 status ≥ 400 的条目(含未在 INVENTORY 里的,一并报——它们同样是真实的坏入口)。

### 3.4 台账与产出

- 台账新增记录类型:`{type:'orphan-audit', unreachable:[], broken:[], exempt_hits:[], seen_count, inventory_count, coverage_note}`,写在遍历结束后;
- 不进现有八分类(那是逐击结论,这是全局结论)。

## 4. SKILL.md 新增一节「孤儿功能对账(可选)」

- **怎么生成 INVENTORY**:引擎不懂任何技术栈,清单由 Claude 现场按项目技术栈生成——SKILL 给出常见栈的提取手法示例(Go chi/gin 的路由注册、Express router、FastAPI 装饰器、React Router/Vue Router 的 route 定义),强调**生成后必须抽样核对真实文件**,不许凭空列;
- **判读指南**(与 dead click 假阳性经验对称,四类):
  1. 权限相关——管理员入口在普通账号遍历中必然 unreachable → 换登录态复跑或列 exempt;
  2. 数据状态相关——空列表时没有「编辑」按钮 → 遍历前造数据,或标注为条件入口;
  3. 拦截名单相关——破坏性按钮不点,其 API 自然零触发 → 先排除这一类再看;
  4. 覆盖不全——有屏 restore 失败时,该屏相关条目不得判 unreachable;
- **真孤儿的三条件**(同时成立才定罪):代码里有 → 前端源码全文搜不到任何引用 → 遍历零触发;
- 安全边界不变(对账只读网络记录,不新增任何写操作)。

## 5. 报告模板新增一节

「孤儿功能对账」:清单规模、覆盖率(seen/inventory)、unreachable 逐条 + 判读结论、broken-entry 逐条 + 状态码、exempt 命中数、覆盖缺口说明。

## 6. 验收条款

1. 未配 INVENTORY 时行为与现状完全一致(对账静默关闭,零副作用);
2. 配了 INVENTORY 时:`network requests --json` 采集可用、归一化正确(`/x/123`→`/x/:id`)、差集正确;
3. smoke 新增用例:归一化纯函数(数字/UUID/hex 三种)、差集纯函数(含 exempt 过滤)、config 校验(类型不符报错退出);全部用例仍全绿;
4. SKILL zh/en 新增节语义一致,含四类判读指南与真孤儿三条件;报告模板 zh/en 同步;
5. 引擎 zh/en 逐字节一致;`node --check` 通过;乱码扫描零命中;
6. 现有八分类、双层域名防护、DENY 逻辑零回归。

## 7. 实施

- 分支 `wip/ui-sweep-orphan-check`(kit),commit 即推;
- ultracode:U1 引擎(sonnet/medium,TDD 先写 smoke)∥ U2 SKILL zh + 报告模板(sonnet/medium)→ U3 en 同步(sonnet/medium);逐单元 opus/medium 评审;终审 opus/high;
- merge 前 Tony 门禁;随后按既有流程铺内部工具包仓 / 内网工作站 两面。
