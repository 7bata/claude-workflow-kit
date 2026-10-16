# 评审链:新项目从第一天起按「日志契约」写(脚手架 + 评审链)

spec:`docs/superpowers/specs/2026-10-15-log-contract-in-scaffold-design.md`。

来历:中文插件那一半(`24a5ae7`、`aaf1ad4`、`a2b7c04`,workflow 0.20.0)由内部监控站的会话在分支 `wip/log-contract-scaffold` 做好后交接给本窗口;本窗口在给另一批次建目标台账分支时从那条分支分叉、合并时把这三个提交一并带进了 main(`c330436`,2026-10-15,未经评审,属误并),因此评审链在并 main 之后补做:英文插件与 Codex 插件在分支 `wip/log-contract-en-codex` 实现,评审覆盖三套,中文那一半若有发现按独立 `fix:` 提交修。

编排:盲审 2 个(`opus` + `medium`,镜头 A 契约内容与三套模板 msg / 字段逐字一致、容易漏的五条;镜头 B 公开措辞泄漏、英文翻译、Codex 版措辞、CLAUDE 模板日志块体积),互不可见、不计票;分流按档位表规则 2。

## 第 1 轮:盲审(2026-10-15)

盲审 2 个都返回。归并后:

- P1 两条(都出在三套 scaffold SKILL,中文那份已在 main):① CLI / 无网络服务分支表与日志契约矛盾——分支要求 CLI 项目「不写 /health」,而 DEPLOYMENT 上线后核对、ARCHITECTURE 5.1 验收清单、CLAUDE/AGENTS §4 固定块都无条件要求 `http request` 与 `/health`、`/health/ready`,分支表没说 CLI 项目这些行怎么办;② 基线表「运行镜像」行仍写「`/health` 健康检查」(另一处「/health 健康检查 + 容器运行」同),而契约规定容器健康检查探 `/health/ready`——照基线行写 HEALTHCHECK 会探错路径,就绪探测失效(spec §5 第 3 条的情形,出在 SKILL 基线行)。
- P2 六条:英文模板的 `fmt.Errorf("查用户(%s)", email)` 示例没翻译;去重规则没划界(访问行、外部调用行不该被降级合并);§4 压缩块比完整表少了外部调用级别、panic 响应已写出、trigger 枚举、status 拿不到写 0/null;README 两语工作流 prompt 第七节评审句里的「§4」在那段 prompt 里指向的是第四节「批量与并行」,不是日志契约;README 中文版「六之四」排在六之一前面;README 英文 6d 用了连字符不是 em dash。
- conflict:无。

分流:有 P1、无 P0 → 修复后直接裁决。中文插件那部分已在 main,修复按独立 `fix:` 提交;英文与 Codex 的修复压进本分支单元提交。

## 第 2 轮:裁决(`opus` + `high`,2026-10-15)

结论 PASS_WITH_NOTES:第 1 轮两条 P1、六条 P2 全部闭合;三套 §4 块(各 16 行)、ARCHITECTURE 5.1(各 38 行)、DEPLOYMENT 上线后核对逐字一致,中文与 Codex 除 CLAUDE.md / AGENTS.md 引用外逐字相同;公开措辞无内部名;两份 plugin.json 0.20.0。新 P2 四条,主对话收尾改掉:① CLI 行补交代生成的 CLAUDE.md / AGENTS.md 第 4 节与 ARCHITECTURE 5.1 正文标「本项目无 HTTP,不适用」、版本注入改 `-ldflags` 或构建信息 vcs 修订;② DEPLOYMENT 上线后核对第 1 条拆成「stdout 全 JSON」与「多一行 http request」两条(三套);③ 英文 §4 的 `status` 补「HTTP status code」;④ Codex 版 SKILL「与开源版字节一致」改成「除 5.1 引言的 AGENTS.md 引用外一致」。推翻:无。

裁决模型:claude-opus-5-5;实现模型:claude-sonnet-5-5(英文与 Codex 单元;中文单元由内部监控站会话实现,模型未记)。评审 2 轮。

## 2026-10-16 追加:健康检查按契约事实源改回(分支 wip/log-contract-health-probe)

起因:内部工具包同批评审报出 P0——容器健康检查探哪条路径前后相反:公开版与内部 spec 写「容器健康检查探 /health/ready」,而契约事实源(内部契约事实源)写「/health 是容器健康检查用的存活路径,数据库抖一下也仍 200,否则会把整个站摘掉」。裁定两边都按事实源:容器健康检查探 `/health`(存活,恒 200),`/health/ready` 是可选的就绪语义(需要时另开,依赖不可用 503,开了要把部署配置里切换前探的路径改成它)。提交 63380b4(三套 §4、5.1、SKILL 基线行、spec)。

盲审 1 个(`opus` + `medium`):P1 两条——5.1 验收第 6 条没核事实源的核心保证「数据库停掉时 /health 仍回 200、ok=false、2 秒内返回」;只有 SKILL 基线行写「可选」,§4 / 5.1 / 验收 / DEPLOYMENT 把 /health/ready 写成必做,互相矛盾。P2 三条——「蓝绿切流量前探它」在单容器模板里没有对应时机;spec §5 第 3 条原句作废却只追加注记;DEPLOYMENT 的 /health 一条没核断依赖仍 200。修复后与内部批次一起裁决。

裁决(`opus` + `high`,与内部批次一起,2026-10-16):公开版 PASS_WITH_NOTES——两条 P1、三条 P2 全部闭合,中文两套逐字一致、英文语义一致,分发文字里无内部名。新 P2 三条,主对话收尾改掉:上线后核对补「部署配置里切换前探的路径已改成它」(三套);形态行与 CLI 引言标就绪路径可选(三套);评审记录措辞。评审 2 轮(盲审 1 + 裁决)。
