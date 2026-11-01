#!/usr/bin/env python3
"""rm-guard-replay.py -- 进程内回放会话记录里的 Bash 命令, 列出会被递归删除守卫拒绝的命令。

只读取 projects-dir 下 .jsonl 每行里 message.content 中 type=tool_use 且 name=Bash 的 input.command
字符串(content 为字符串或缺失的行跳过), 以及该行记录自带的 cwd 字段(没有就当作未知); 其它字段一律
不读取、不保存、不输出。不起子进程, 不执行任何命令。

钩子模块按文件路径用 importlib 加载, 进程内调用 judge(command, cwd) -> None | (规则名, 目标原文)。
每次调用用 signal.setitimer 设 5 秒上限, 超时单独计数(不算拒绝)。被拒绝的命令按文本去重(保留首次
出现的项目)。

用法:
  rm-guard-replay.py --out FILE [--projects-dir DIR ...] [--hook PATH] [--limit N]
  rm-guard-replay.py --self-test

  --out        必填, 不得在仓库目录内; 新建权限 600; 每个被拒绝的命令一行:
               项目目录名 TAB 规则名 TAB 命令前 200 字(换行换成空格)
  --projects-dir  可多次给; 默认 ~/.claude/projects
  --hook       默认:环境变量 RM_GUARD_HOOKS_DIR 指的目录;没设时依次找本目录的 ../hooks 与上一级目录里的 block-recursive-rm.py
  --limit N    最多回放 N 条命令(0 或不给为不限)
  --self-test  在临时目录里造假 jsonl, 用注入的假 judge 断言解析/去重/输出格式/权限, 不需要钩子文件

标准输出只有计数(扫描文件数、命令数、拒绝数按规则分组、超时数), 不含命令文本。
退出码: 0 正常(--self-test 通过); 1 --self-test 断言失败; 2 参数或环境错误。

只用标准库, 兼容 python 3.9。
"""
import argparse
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_NAME = "block-recursive-rm.py"


def _default_hook():
    env = os.environ.get("RM_GUARD_HOOKS_DIR")
    if env:
        return os.path.join(os.path.abspath(env), HOOK_NAME)
    cands = [os.path.join(os.path.dirname(HERE), "hooks"), os.path.dirname(HERE)]
    for c in cands:
        if os.path.isfile(os.path.join(c, HOOK_NAME)):
            return os.path.join(c, HOOK_NAME)
    return os.path.join(cands[0], HOOK_NAME)


DEFAULT_HOOK = _default_hook()
CALL_LIMIT_S = 5
CMD_PREFIX_LEN = 200


class CallTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise CallTimeout()


def die(msg, code=2):
    print("rm-guard-replay: %s" % msg, file=sys.stderr)
    sys.exit(code)


def git_toplevel(path):
    try:
        p = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=20)
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def check_out_path(out):
    real = os.path.realpath(os.path.abspath(out))
    for base in (HERE, os.path.dirname(real) if os.path.isdir(os.path.dirname(real)) else HERE):
        top = git_toplevel(base)
        if top:
            top_real = os.path.realpath(top)
            if real == top_real or real.startswith(top_real + os.sep):
                die("--out must not be inside a git repository: %s" % top_real)
    return real


def load_hook(path):
    if not os.path.isfile(path):
        die("hook file not found: %s" % path)
    spec = importlib.util.spec_from_file_location("rm_guard_hook", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        die("cannot load hook: %r" % (e,))
    fn = getattr(mod, "judge", None)
    if not callable(fn):
        die("hook has no judge()")
    return fn


def iter_records(path, stats):
    """逐行产出 (command, cwd): 只取 Bash tool_use 的 input.command 与该行的 cwd。"""
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        stats["unreadable"] += 1
        return
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                stats["bad_lines"] += 1
                continue
            if not isinstance(obj, dict):
                continue
            msg = obj.get("message")
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            cwd = obj.get("cwd")
            cwd = cwd if isinstance(cwd, str) and cwd else None
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "tool_use" or item.get("name") != "Bash":
                    continue
                inp = item.get("input")
                cmd = inp.get("command") if isinstance(inp, dict) else None
                if isinstance(cmd, str) and cmd:
                    yield cmd, cwd


def find_jsonl(projects_dir):
    res = []
    for root, _dirs, files in os.walk(projects_dir):
        for fn in files:
            if fn.endswith(".jsonl"):
                res.append(os.path.join(root, fn))
    res.sort()
    return res


def project_of(projects_dir, path):
    rel = os.path.relpath(path, projects_dir)
    return rel.split(os.sep, 1)[0] if os.sep in rel else "(root)"


def call_judge(judge, cmd, cwd):
    """返回 (status, result): status 为 ok / timeout / error。"""
    old = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, CALL_LIMIT_S)
    try:
        return "ok", judge(cmd, cwd)
    except CallTimeout:
        return "timeout", None
    except BaseException as e:  # 钩子里的任何异常都只计数, 不中断回放
        if isinstance(e, KeyboardInterrupt):
            raise
        return "error", None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def replay(projects_dirs, judge, limit):
    stats = {"bad_lines": 0, "unreadable": 0, "files": 0}
    total = 0
    timeouts = 0
    errors = 0
    seen = {}        # 命令文本 -> 是否被拒绝(去重, 同一文本只判一次)
    denied = []      # (project, rule, cmd) 去重后首次出现
    by_rule = {}
    done = False
    for pdir in projects_dirs:
        for path in find_jsonl(pdir):
            stats["files"] += 1
            proj = project_of(pdir, path)
            for cmd, cwd in iter_records(path, stats):
                if limit and total >= limit:
                    done = True
                    break
                total += 1
                if cmd in seen:
                    continue
                status, res = call_judge(judge, cmd, cwd)
                seen[cmd] = bool(res)
                if status == "timeout":
                    timeouts += 1
                elif status == "error":
                    errors += 1
                elif res:
                    rule = str(res[0])
                    denied.append((proj, rule, cmd))
                    by_rule[rule] = by_rule.get(rule, 0) + 1
            if done:
                break
        if done:
            break
    return {"stats": stats, "total": total, "unique": len(seen), "timeouts": timeouts,
            "errors": errors, "denied": denied, "by_rule": by_rule}


def one_line(s, n):
    return s[:n].replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_out(path, denied):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for proj, rule, cmd in denied:
            f.write("%s\t%s\t%s\n" % (one_line(proj, 200), one_line(rule, 50), one_line(cmd, CMD_PREFIX_LEN)))
    os.chmod(path, 0o600)


def print_report(r):
    print("files=%d" % r["stats"]["files"])
    print("commands=%d" % r["total"])
    print("unique_commands=%d" % r["unique"])
    print("denied=%d" % len(r["denied"]))
    for rule in sorted(r["by_rule"]):
        print("denied_rule=%s count=%d" % (rule, r["by_rule"][rule]))
    print("timeouts=%d" % r["timeouts"])
    print("errors=%d" % r["errors"])
    print("bad_lines=%d unreadable_files=%d" % (r["stats"]["bad_lines"], r["stats"]["unreadable"]))


# ---------------------------------------------------------------------------
def self_test():
    problems = []

    def check(cond, msg):
        if not cond:
            problems.append(msg)

    calls = []

    def fake_judge(cmd, cwd):
        calls.append((cmd, cwd))
        if "SLOW" in cmd:
            raise CallTimeout()
        if "BOOM" in cmd:
            raise ValueError("boom")
        if "rm -rf $" in cmd:
            return ("expansion", "$X")
        if "rm -rf ~" in cmd:
            return ("tilde", "~")
        return None

    def rec(content, cwd=None, extra=None):
        o = {"message": {"role": "assistant", "content": content}}
        if cwd is not None:
            o["cwd"] = cwd
        if extra:
            o.update(extra)
        return json.dumps(o, ensure_ascii=False)

    def bash(cmd):
        return {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}

    with tempfile.TemporaryDirectory(prefix="rm-guard-replay-selftest-") as tmp:
        pdir = os.path.join(tmp, "projects")
        os.makedirs(os.path.join(pdir, "projA"))
        os.makedirs(os.path.join(pdir, "projB"))
        long_cmd = "rm -rf $" + "y" * 300 + "\nsecond line\twith tab"
        lines_a = [
            rec([bash("rm -rf $X"), bash("ls -la")], cwd="/work/a"),
            rec([{"type": "text", "text": "rm -rf $SECRET_TEXT"}]),
            rec([{"type": "tool_result", "content": "rm -rf $FROM_RESULT"}]),
            rec([{"type": "tool_use", "name": "Read", "input": {"command": "rm -rf $NOT_BASH"}}]),
            rec("rm -rf $STRING_CONTENT"),
            json.dumps({"message": {"role": "user"}}),
            "this is not json",
            "",
            rec([bash("rm -rf ~/x")], extra={"toolUseResult": "rm -rf $LEAK"}),
            rec([bash(long_cmd)]),
            rec([bash("SLOW command")]),
            rec([bash("BOOM command")]),
            rec([bash("")], cwd="/ignored"),
            json.dumps([1, 2, 3]),
        ]
        lines_b = [
            rec([bash("rm -rf $X")], cwd="/work/b"),   # 与 projA 重复: 只出现一次, 项目为 projA
            rec([bash("rm -rf ~/other")], cwd="/work/b"),
        ]
        with open(os.path.join(pdir, "projA", "s1.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines_a) + "\n")
        with open(os.path.join(pdir, "projB", "s2.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines_b) + "\n")
        with open(os.path.join(pdir, "projB", "notes.txt"), "w") as f:
            f.write("rm -rf $IGNORED_FILE\n")

        r = replay([pdir], fake_judge, 0)
        check(r["stats"]["files"] == 2, "files=%r want 2" % r["stats"]["files"])
        check(r["stats"]["bad_lines"] == 1, "bad_lines=%r want 1" % r["stats"]["bad_lines"])
        cmds_seen = [c for c, _ in calls]
        for leaked in ("SECRET_TEXT", "FROM_RESULT", "NOT_BASH", "STRING_CONTENT", "LEAK", "IGNORED_FILE"):
            check(not any(leaked in c for c in cmds_seen), "non-Bash text was parsed: %s" % leaked)
        check(("rm -rf $X", "/work/a") in calls, "cwd from the record line was not passed")
        check(("ls -la", "/work/a") in calls, "cwd not passed for second command")
        check(("rm -rf ~/x", None) in calls, "missing cwd should be None")
        check(cmds_seen.count("rm -rf $X") == 1, "duplicate text judged more than once")
        check("" not in cmds_seen, "empty command was judged")
        check(r["timeouts"] == 1, "timeouts=%r want 1" % r["timeouts"])
        check(r["errors"] == 1, "errors=%r want 1" % r["errors"])
        check(r["total"] == 8, "total=%r want 8" % r["total"])
        check(len(r["denied"]) == 4, "denied=%r want 4" % len(r["denied"]))
        check(r["by_rule"] == {"expansion": 2, "tilde": 2}, "by_rule=%r" % r["by_rule"])
        check(r["denied"][0] == ("projA", "expansion", "rm -rf $X"), "first denied = %r" % (r["denied"][0],))
        check(not any(p == "projB" and c == "rm -rf $X" for p, _r, c in r["denied"]),
              "duplicate attributed to the second project")

        out = os.path.join(tmp, "out.tsv")
        write_out(out, r["denied"])
        check((os.stat(out).st_mode & 0o777) == 0o600, "out mode %o" % (os.stat(out).st_mode & 0o777))
        with open(out, encoding="utf-8") as f:
            rows = f.read().split("\n")
        check(rows[-1] == "", "output should end with a newline")
        rows = rows[:-1]
        check(len(rows) == 4, "out has %d rows, want 4" % len(rows))
        for row in rows:
            check(row.count("\t") == 2, "row has wrong tab count: %r" % row[:60])
        check(rows[0] == "projA\texpansion\trm -rf $X", "row0 = %r" % rows[0])
        long_row = [x for x in rows if "yyy" in x]
        check(len(long_row) == 1, "long command row missing")
        if long_row:
            proj, rule, cmd = long_row[0].split("\t")
            check(len(cmd) == CMD_PREFIX_LEN, "command not cut to %d chars (%d)" % (CMD_PREFIX_LEN, len(cmd)))
            check("\n" not in cmd, "newline left in command")
        check(not any("second line" in x for x in rows), "text beyond 200 chars leaked")

        # --out 已存在且权限宽松时, 重写后仍是 600
        os.chmod(out, 0o644)
        write_out(out, r["denied"])
        check((os.stat(out).st_mode & 0o777) == 0o600, "rewritten out mode not 600")

        # --limit
        calls[:] = []
        r2 = replay([pdir], fake_judge, 2)
        check(r2["total"] == 2, "limit: total=%r want 2" % r2["total"])

        # 标准输出只含计数: 报告里不含任何命令文本
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            print_report(r)
        finally:
            sys.stdout = old
        text = buf.getvalue()
        check("rm -rf" not in text and "ls -la" not in text, "report prints command text")
        check("denied_rule=expansion count=2" in text and "timeouts=1" in text, "report counts missing")

        # --out 在仓库内要被拒绝(以本脚本所在仓库为例)
        top = git_toplevel(HERE)
        if top:
            inside = os.path.join(top, "should-not-exist.tsv")
            try:
                check_out_path(inside)
                check(False, "--out inside the repository was accepted")
            except SystemExit as e:
                check(e.code == 2, "--out inside repo exit code %r" % (e.code,))
            check(not os.path.exists(inside), "check_out_path created the file")

    for p in problems:
        print("SELF-TEST FAIL: %s" % p)
    if problems:
        return 1
    print("SELF-TEST OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--projects-dir", action="append", default=[])
    ap.add_argument("--out")
    ap.add_argument("--hook", default=DEFAULT_HOOK)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.out:
        die("--out is required")
    out = check_out_path(args.out)
    dirs = args.projects_dir or [os.path.expanduser("~/.claude/projects")]
    for d in dirs:
        if not os.path.isdir(d):
            die("projects dir not found: %s" % d)
    judge = load_hook(args.hook)
    r = replay(dirs, judge, max(0, args.limit))
    write_out(out, r["denied"])
    print_report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
