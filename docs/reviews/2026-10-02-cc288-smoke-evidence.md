# Claude Code 2.1.288 真机取证:插件子代理 effort 与 omitClaudeMd 按需加载

临时目录 T=/tmp/cc288smoke.bdwfR6(保留);项目 P=$T/P,插件 PL=$T/PL(name smokeprobe,`claude plugin validate` 通过,仅一条缺 author 的警告)。
启动前负载:1 分钟 6.01,10 核(低于 70%),嵌套 claude 全部串行。
取证通道:通道一 InstructionsLoaded hook($T/hook.sh,把 stdin JSON 按行写入 $T/hook-<组>.jsonl)。通道三 --debug-file 日志里没有 effort 字样(grep 无输出),未使用;通道二未需要。

每组命令形式(run.sh):
`env -u CLAUDECODE perl -e 'alarm 300; exec @ARGV' claude -p --plugin-dir $T/PL --model sonnet --effort high --debug-file $T/debug-<组>.log "<指令>"`(在 P 目录执行,全部 exit 0)。各组指令原文在 $T/run.sh 调用记录里;输出在 $T/out-<组>.txt。

## 结论

### Q1:PASS
- (a) probe-noeffort(无 effort):hook 载荷 `"agent_type": "smokeprobe:probe-noeffort", "effort": {"level": "high"}`,与主会话 --effort high 一致。
- (b) probe-keep(effort: low):hook 载荷 `"agent_type": "smokeprobe:probe-keep", "effort": {"level": "low"}`。
- (c)(d)(e)(f)(g) 里 probe-omit / probe-keep 载荷也都是 `{"level": "low"}`。
- 即子代理 frontmatter 的 effort: low 在主会话 high 时生效,不写则继承主会话。

### Q2
| 组 | 子代理 | 操作 | hook 触发 | 子代理自述 |
|---|---|---|---|---|
| (c) | probe-omit | Read sub/a.txt | nested_traversal 加载 sub/CLAUDE.md,trigger=sub/a.txt | 看到 SUB-RULE-5527,没看到 ROOT |
| (d) | probe-omit | Edit sub/a.txt | 同上,但子代理先直接 Edit 失败(Edit 要求先 Read),随后 Read 再 Edit;加载由 Read 触发,无法单独归因 Edit | 看到 SUB,没看到 ROOT |
| (e) | probe-omit | Write 新文件 sub2/c.txt(未 Read) | path_glob_match 加载 .claude/rules/pathrule.md,trigger=sub2/c.txt | 看到 PATH-RULE-8846(Write 之后出现) |
| (g,补充) | probe-omit | Write 新文件 sub/d.txt(未 Read) | nested_traversal 加载 sub/CLAUDE.md,trigger=sub/d.txt | 自述未逐字确认,以 hook 为准 |
| (b) | probe-keep(对照) | Read sub/a.txt | nested_traversal 加载 sub/CLAUDE.md | 看到 ROOT 与 SUB |
| (f) | probe-keep(对照) | Read+Edit sub2/b.txt | path_glob_match 加载 pathrule.md,trigger=sub2/b.txt | 看到 ROOT 与 PATH |

- omitClaudeMd 只屏蔽开局自动加载:probe-omit 看不到根 CLAUDE.md 的 ROOT-RULE-7391(c、d 自述均确认);probe-keep 看得到(b、f)。但按需加载(子目录 CLAUDE.md、路径规则)对 omit 子代理照常生效,Read 与 Write 都已实测触发。
- Edit 本身是否单独触发未能隔离:Edit 必须先 Read,所以加载总是先由 Read 触发。
- 子代理触发的事件载荷带 agent_id、agent_type、effort,与 2.1.288 更新日志一致;会话开局的 session_start 事件没有这三个字段。

## hook 载荷原文摘录

### 组 a(只摘子代理触发的行)
```json
{"session_id": "1319c511-5740-488b-ab67-dfe7c2c0c995", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "f6b43e92-640f-40ff-93c4-bf32ab7096db", "agent_id": "a2a05a21327ee5835", "agent_type": "smokeprobe:probe-noeffort", "effort": {"level": "high"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/CLAUDE.md", "memory_type": "Project", "load_reason": "nested_traversal", "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/a.txt"}
```

### 组 b(只摘子代理触发的行)
```json
{"session_id": "37e7b14e-6389-467c-ad10-61f9ebed55bb", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "26555284-7e10-4f17-8e72-cc251ce3e3da", "agent_id": "a3bc204cae047c515", "agent_type": "smokeprobe:probe-keep", "effort": {"level": "low"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/CLAUDE.md", "memory_type": "Project", "load_reason": "nested_traversal", "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/a.txt"}
```

### 组 c(只摘子代理触发的行)
```json
{"session_id": "06f0a719-83a9-493d-9792-2b5ae429fd8a", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "25fded14-c3d1-4405-bdc5-6c2d62a13e6d", "agent_id": "a294c4e38cc93a6f2", "agent_type": "smokeprobe:probe-omit", "effort": {"level": "low"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/CLAUDE.md", "memory_type": "Project", "load_reason": "nested_traversal", "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/a.txt"}
```

### 组 e(只摘子代理触发的行)
```json
{"session_id": "de8147d4-1f00-4ebd-8798-386e424ff50b", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "e3655e28-51f7-4f55-b8ed-a3a4ac1fa4b9", "agent_id": "a605bdab9056c9c53", "agent_type": "smokeprobe:probe-omit", "effort": {"level": "low"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/.claude/rules/pathrule.md", "memory_type": "Project", "load_reason": "path_glob_match", "globs": ["sub2"], "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub2/c.txt"}
```

### 组 f(只摘子代理触发的行)
```json
{"session_id": "07c6648f-b010-4212-b79f-0648f1296254", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "b480970c-2cbc-4a8f-9759-95d9909d9d3b", "agent_id": "accef1f56a608040d", "agent_type": "smokeprobe:probe-keep", "effort": {"level": "low"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/.claude/rules/pathrule.md", "memory_type": "Project", "load_reason": "path_glob_match", "globs": ["sub2"], "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub2/b.txt"}
```

### 组 g(只摘子代理触发的行)
```json
{"session_id": "ec170739-eb55-4eac-9b65-85da7be6b1c1", "transcript_path": "<本机会话记录>", "cwd": "/private/tmp/cc288smoke.bdwfR6/P", "prompt_id": "87b32741-7b27-4367-b203-23c149153932", "agent_id": "a76b11b4fdd212659", "agent_type": "smokeprobe:probe-omit", "effort": {"level": "low"}, "hook_event_name": "InstructionsLoaded", "file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/CLAUDE.md", "memory_type": "Project", "load_reason": "nested_traversal", "trigger_file_path": "/private/tmp/cc288smoke.bdwfR6/P/sub/d.txt"}
```

## 进程核对
全部嵌套 claude 均已正常退出(exit 0);结束后 `ps -axo pid,command | grep -F /tmp/cc288smoke.bdwfR6` 无输出。未启动浏览器、服务、容器。测试进程已关。

## 补充:实现后的冒烟(2026-10-02)

- **AC3(kit 的 mechanical 定义,实现单元 U2 跑)**:`--plugin-dir plugins/workflow --model sonnet --effort high`,裸 Agent 派 `workflow:mechanical` 读 sub/a.txt,hook 载荷 `"agent_type": "workflow:mechanical", "effort": {"level": "low"}`;换 `plugins/workflow-en` 与 `workflow-en:mechanical`,同为 `{"level": "low"}`。日志 `$T/hook-u2zh.jsonl`、`$T/hook-u2en.jsonl`(各 3 行,前 2 行是主会话 session_start)。
- **AC8(haiku,独立测试 agent 跑)**:同上命令,Agent 工具的 `model` 设 haiku。嵌套会话正常结束;子代理转录的模型是 claude-haiku-4-5-20251001;hook 载荷里该子代理那一行没有 effort 字段。日志 `$T/hook-tester-haiku.jsonl`。
- 两次都核对过没有残留的嵌套 claude 进程。
- **AC7(本机已装的 内部工具包 1.7.4,主对话跑)**:不带 `--plugin-dir`,`--model sonnet --effort high`,裸 Agent 派 `内部工具包:mechanical`(没传 model)读 sub/a.txt,hook 载荷 `"agent_type": "〔内部工具包〕:mechanical", "effort": {"level": "low"}`;嵌套会话 exit 0,无残留进程。日志 `$T/hook-ac7.jsonl`。临时目录 $T 在收尾时已删除,本文件的摘录即留存证据。
