# 新项目从第一天起按「日志契约」写(脚手架 + 评审链)

- 日期:2026-10-15
- 路径:bounded(改模板与规则措辞,不加新技能、不加 hook)
- 目标覆盖声明:覆盖目标台账 2026-10-15 那条「以后写项目的时候避免像今天这样回头重写日志」;不覆盖存量项目的日志改造(那是各项目自己的批次)、不覆盖监控站本身。
- 背景:2026-10-15 一天里有 8 个按本方法论铺出来的项目不得不回头把日志改成结构化、补访问行 / 作业行 / 外部调用行 / 健康检查正文,原因只有一个——脚手架里从来没有写「日志该长什么样」,每个项目都是临时写、各写各的,等到要上监控才发现机器读不了。日志契约不是监控的需求,是任何常驻服务的基本要求,所以放进脚手架的硬规则,和「错误显式处理」「密钥只来自环境变量」同级。

## 1. 现状

- `plugins/workflow` / `workflow-en` / `workflow-codex` 三套脚手架模板里,`CLAUDE.md.tmpl`(codex 版是 `AGENTS.md.tmpl`)第 4 节「代码约定」只有 `{{CODE_CONVENTIONS_BLOCK}}` 加两条通用约定,没有一个字提到日志;`docs/ARCHITECTURE.md.tmpl` 只在目录树注释里出现过一次「请求日志」;`docs/DEPLOYMENT.md.tmpl` 的上线核对没有日志项;`scaffold/SKILL.md` 的技术栈基线表没有日志行。
- README 两语的工作流 prompt 里,评审链的基础检查只写「核对测试本身」,日志不在任何检查项里。

## 2. 日志契约(本次写进模板的内容,三套模板共用同一份,中英各一)

- **形态**:每行一个 JSON 对象写 stdout(容器化服务由运行环境收集与轮转,不写文件);必有 `time`(RFC3339 毫秒)、`level`(`debug` / `info` / `warn` / `error`,小写)、`msg`(稳定短句,不夹变量;变量一律放独立字段)。`msg` 就是接口:监控与排障按它认行,改它等于改接口。一行不超过 4 KB,堆栈放 `stack` 字段。
- **必有的事件行**(msg 固定,下面这些英文短句不翻译):
  | 时机 | 级别 | `msg` | 字段 |
  |---|---|---|---|
  | 进程开始监听前 | info | `service start` | `service`、`version`(构建时注入的 commit 短哈希)、`addr` |
  | 进程退出(信号、监听出错、启动失败) | info / error | `service stop` | `reason`、失败时 `err` |
  | 每个 HTTP 请求结束 | info(5xx 为 error) | `http request` | `method`、`route`(路由模板,不是实际路径)、`path`、`status`、`duration_ms`、`request_id`;有登录态加 `user_id`;健康检查路径不记 |
  | 捕获到 panic / 未处理异常 | error | `panic` | `err`、`stack`、`request_id`;响应已写出时只记行并中止连接 |
  | 间隔 > 1 分钟的定时 / 后台作业开始 | info | `job start` | `job`、`run_id`、`trigger`(timer / manual / retry / startup) |
  | 作业结束 | info(失败 error) | `job end` | `job`、`run_id`、`ok`、`duration_ms`、各类计数、失败带 `err`;部分失败也是 `ok=false` |
  | 高频轮询(间隔 ≤ 1 分钟)的 tick | — | `job end` 只在有动作或出错时记;每 5 分钟一行 `job heartbeat`(`job`、`ticks`、自上次心跳以来的计数、`skipped`、`errors`) |
  | 作业重试 | warn(放弃 error) | `job retry` | `job`、`attempt`、`max_attempts`、`next_retry_in_s`;放弃时 `attempts`、`giving_up=true` |
  | 调外部服务(LLM、第三方 API、数据库迁移) | info(失败 warn / error) | `<目标> call`(如 `llm call`、`payment call`) | `target`、`ok`、`status`(HTTP 状态码,拿不到写 0 或 null)、`duration_ms`、`attempt` 或 `attempts`;不记 prompt、请求体、响应正文、令牌 |
- **去重**:同一原因连续失败时,同一错误文本只记第一条 error,之后降 debug 或带 `repeat` 计数;恢复后重置。不许每 N 分钟原样重复同一条 error。
- **健康检查**:`GET /health` 是存活语义,HTTP 恒 200,正文 `{ok, version, db, uptime_s}`,依赖坏了 `ok=false`;就绪语义另开 `GET /health/ready`,依赖不可用回 503,容器健康检查探它。两条路径都不记访问行。
- **不记的东西**:密钥、令牌、cookie、Authorization 头、密码、邮箱与手机号原文(要记就打码 `t***@domain`)、用户正文、LLM 的 prompt 与响应正文。错误文本也算:`fmt.Errorf("查用户(%s)", email)` 这种把邮箱拼进错误里的写法同样违反。
- **版本注入**:Dockerfile `ARG APP_VERSION=unknown` + `ENV APP_VERSION=$APP_VERSION`,CI 构建传 `--build-arg APP_VERSION=<commit 短哈希>`;进程里版本取 `APP_VERSION` → 构建信息里的 vcs 修订 → `unknown`。
- **验收清单**(每个新项目第一次上线前过一遍):① 启动后 stdout 全是 JSON 行;② 随便请求一个接口,多一行 `http request` 且 `route` 是模板;③ `service start` 带 commit;④ 每个作业跑一轮能看到 `job end`(高频的看到 `job heartbeat`);⑤ 让一个外部调用失败,看到带 `err` 的 `<目标> call` 且不含密钥;⑥ `/health` 正文四个字段齐全,`/health/ready` 在依赖断开时 503;⑦ 日志里 grep 不到邮箱、token、密码。

## 3. 改动清单(验收条款)

- **C1 `CLAUDE.md.tmpl`(zh / en)与 `AGENTS.md.tmpl`(codex)第 4 节**:`{{CODE_CONVENTIONS_BLOCK}}` 之后加固定块「**日志(可观测性契约,第一天起就按这个写)**」:第 2 节的「形态」「必有的事件行」(表格压成一句一行)「去重」「健康检查」「不记的东西」「版本注入」六条,末尾一句「完整表格与验收清单见 `docs/ARCHITECTURE.md`「日志契约」一节」。三套措辞一致;en 版翻译说明文字,`msg` 字符串与字段名保持原样。
- **C2 同三份模板的第 3 节「修改后质量检查」**加一项:「改到请求路径、定时 / 后台作业、外部调用、健康检查的改动,对照「日志契约」核一遍新增或改动的日志行(msg 稳定、字段齐、无密钥与个人信息)」;第 7 节「评审 agent 必须亲自读被改的文件核对……并核对测试本身」改成「……并核对测试本身与日志契约(§4)」;「禁止事项」加一条「改到请求 / 作业 / 外部调用 / 健康检查却不按日志契约写日志行」。
- **C3 `docs/ARCHITECTURE.md.tmpl`(三套)**加一节「日志契约」:第 2 节的完整表格、去重规则、健康检查、不记的东西、版本注入、验收清单,原文照放(模板里是项目文档,不是 skill 说明,所以要完整);放在接口表之后。
- **C4 `docs/DEPLOYMENT.md.tmpl`(三套)**「上线后核对」加四条:stdout 全 JSON;`service start` 带本次 commit;`/health` 正文四字段、`/health/ready` 200;一个作业跑完有 `job end`。
- **C5 `scaffold/SKILL.md`(三套)**:技术栈基线表加一行「日志:标准库结构化日志(Go 用 `log/slog` 的 JSON handler;其它栈用等价的 JSON 行日志库)写 stdout,按 CLAUDE.md 第 4 节的日志契约」;`{{CODE_CONVENTIONS_BLOCK}}` 的说明加「日志按契约写:slog JSON、每请求一行访问日志、作业行、外部调用行、`/health` 正文」;占位符替换表若有 `{{HEALTH_PATH}}` 之类保持不变。
- **C6 README.md / README.zh-CN.md**:「六、开新项目」一节加一段「日志契约」(三四句:为什么、放在哪、评审怎么查),工作流 prompt 第七节评审句同 C2 的改法;「自定义技术栈基线」一节提一句日志行是基线的一部分。
- **C7 kit 自身的记录**:`docs/REQUIREMENTS.md` 目标台账登记本条(open → done 附证据);`docs/Progress.md` 变更日志一条;`plugins/workflow` 与 `workflow-en` 的 `plugin.json` 版本 0.19.1 → 0.20.0(加了规则,不是修 bug);codex 版无 plugin.json,不动。
- **不改**:不加新模板文件(放进既有的 ARCHITECTURE / CLAUDE 模板);不改 hooks;不改 speak-human / send-to / ui-sweep;不动存量项目。

## 4. 验收(主对话收尾时跑)

- 三套 `CLAUDE.md.tmpl` / `AGENTS.md.tmpl`、三套 `ARCHITECTURE.md.tmpl`、三套 `DEPLOYMENT.md.tmpl` 都 grep 得到 `http request`、`service start`、`job end`、`job heartbeat`、`/health/ready`、`APP_VERSION`。
- README 两语都有「日志契约」/ "log contract" 小节;评审句两语都含「日志契约」/ "log contract"。
- `plugin.json` 两处版本一致为 0.20.0。
- 公开措辞检查:新增内容里 grep 不到内部系统名、内网域名、同事名、本机路径(用「内部监控站」「内部工具包」这类中性叫法)。
- 三套模板的 msg 字符串与字段名逐字一致(脚本对比 `msg` 列)。

## 5. 容易漏的输入与失败情形

1. **en 版把 msg 翻译了**:`http request`、`job end` 这些是机器认的字符串,三套模板必须逐字相同;验收第 5 条守住。
2. **高频轮询与普通作业的分界**:「间隔 ≤ 1 分钟走高频规则(每分钟一次的轮询也算)」要写清,否则实现时每分钟一条 job start / job end 刷屏。
3. **存活与就绪混成一条**:`/health` 恒 200、`/health/ready` 才 503,容器健康检查探后者;写反了容器会被反复重启。
4. **错误文本带个人信息**:只删日志字段不够,错误包装里拼了邮箱照样泄漏;「不记的东西」一条点名这种写法。
5. **公开仓的措辞**:背景里不出现内部项目名与监控站名字,只说「按本方法论铺出来的 8 个项目」。

## 6. 文档同步

- `docs/REQUIREMENTS.md` 目标台账销账;`docs/Progress.md` 变更日志;`docs/PLAN.md` Spec 索引加一行;README 两语(C6)。
