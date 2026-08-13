# UI 全量交互遍历报告(模板)

- **日期**:
- **驱动**:agent-browser <版本>(headless Chrome for Testing <版本>)+ ui-sweep 遍历编排
- **对象**:<站点 URL>(<登录态说明>,部署版本 = <commit/pipeline>)
- **方法**:<N> 个屏(<屏 id 列表>),每屏 a11y 快照建元素计划,逐元素「恢复现场→重定位→点击→观察」;观察面=页面指纹变化、未捕获异常、console error/warn、弹窗;破坏性动作拦截名单只记不点;confirm/prompt 一律驳回(不产生真实写入);<语言/主题等基线锁说明>。

## 总量

**<N> 条结果记录(<N2> 次实际点击)。<M> 页面异常,<K> console 报错。** 分布:ok-changed <n1> / dead <n2> / dialog-dismissed <n3> / click-error <n4> / page-error <n5> / 拦截未点(skipped-denylist)<n6> / 定位丢失(miss-not-found)<n7> / 出域已拉回(left-domain)<n8>。(其中 <n9> 次按位回落命中(note-relocated-by-index)——附注,不是独立分类,已计入以上对应分类。)

## 真缺陷(<数量> 个,已修/待修)

逐条列出——每条必须已用真浏览器手动复核坐实,不能只凭台账下结论:

- **<缺陷一句话概括>**:<复现步骤>。<复核证据,如「innerText N→N,零错误元素」>。<修复状态与提交/文件>。

(无真缺陷时写「本轮未发现真缺陷」,不要省略本节。)

## 假阳性定性(逐条人工复核过)

对台账里判为 dead/click-error/page-error 但经复核不是产品缺陷的条目,逐条说明排除依据(引用 SKILL.md「结果判读」里的定性法):

- <元素/按钮名> 判 <原分类> ×<次数>:<排除依据,如「同步 prompt 堵塞点击命令导致超时,台账显示 prompt 内容已弹出并被驳回,按钮本身正常」>。

## 观察级(不定罪,留候选)

不足以定罪但值得记录、留给后续验证或产品决策的观察:

- <观察一句话>——<为什么不定罪,建议的后续动作>。

## 孤儿功能对账(未配 INVENTORY 时删除本节)

- **清单规模**:INVENTORY 共 <A> 条(apis <A1> / routes <A2>),exempt <A3> 条(天然不可达,不参与覆盖率计算)。
- **覆盖率**:可核查条目(inventory_auditable_count,= <A> 减 exempt <A3>)共 <A4> 条,实际命中(inventory_hit_count)<B> 条(<B>/<A4>)。
- **总观测数**(`seen_count`,仅供诊断,不是覆盖率分子——它包含站内观测到的 API/路由(出域与第三方请求已排除),含未列入 INVENTORY 的条目):<S> 条。

### unreachable(<C> 条)

逐条列出 + 判读结论(引用上面四类判读指南,或坐实为真孤儿):

- `<METHOD /path 或 /route>`:<判读结论——权限相关/数据状态相关/拦截名单相关/覆盖不全/真孤儿(三条件均已核对)>。

(无 unreachable 条目时写「本轮未发现 unreachable 条目」,不要省略本节。)

### broken-entry(<D> 条)

逐条列出 + 状态码:

- `<METHOD /path>`:状态码 <status>,<简要说明,如遍历时哪个元素触发>。

(无 broken-entry 条目时写「本轮未发现 broken-entry 条目」。)

### exempt 命中(<E> 条)

- `<正则/条目>` 命中 <N> 次:<说明,如「webhook 端点,预期无 UI 入口」>。

### 对账覆盖缺口(note-partial-coverage)

- <哪些屏/条目因 restore-failed、miss-not-found 等原因未走完,相关 INVENTORY 条目标 note-partial-coverage,不计入 unreachable 结论;与下方「覆盖缺口(诚实记账)」一节对应条目同源,此处只补充"对 INVENTORY 结论的影响",不重复罗列原因细节>。
- **`coverage_note`(台账 `orphan-audit` 记录字段,必须原样转述,不得省略、不得改写成摘要)**:<原样粘贴 ledger.jsonl 里那条 `type: 'orphan-audit'` 记录的 `coverage_note` 字符串>。若这里出现"网络采集失败/从未采集"一类警告,说明本轮 unreachable/broken-entry 结论不可信,报告正文必须原样带出这条警告,不能因为它读起来"扫兴"就悄悄压下去或简化成"覆盖基本完整"。

## 覆盖缺口(诚实记账)

本轮遍历没有覆盖到的部分,以及原因(不要粉饰成"已全量覆盖"):

- 拦截未点 <N> 项(<按钮名列表>):破坏性或产生真实写入,本轮不点。
- <定位丢失/未成屏的部分>:<原因>。
- <未纳入范围的模块/上游产品 UI>:<原因>。
- 出域已拉回 <N> 项(<元素名列表>):点击后跑出了当次 `ALLOWED_DOMAINS`,已被引擎当场恢复现场,该元素本次遍历没有真正被验证到最终态;如果是站内正常跳转到某个上游域名,把该域名加进 `ALLOWED_DOMAINS` 再跑一轮即可覆盖。
