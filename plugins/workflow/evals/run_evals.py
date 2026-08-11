#!/usr/bin/env python3
"""evals/run_evals.py — auto-scaffold 判定规则的 trigger/no_trigger 轻量评测。

对 evals/cases.jsonl 里每个案例：
  1. 拼装「规则正文 + 场景描述（user_utterance + cwd_context）」的 prompt；
  2. 用 `claude -p` 非交互调用，要求模型只回 TRIGGER 或 NO_TRIGGER；
  3. 与 case 的 expected（trigger|no_trigger）比对，逐条与汇总通过率。

用法:
    python3 evals/run_evals.py [--limit N] [--timeout SEC] [--dry-run]
        [--cases PATH] [--rules PATH] [--out-dir PATH]

环境变量:
    CLAUDE_BIN    claude 可执行文件路径（默认 "claude"）
    CLAUDE_MODEL  传给 `claude -p --model <值>` 的模型名（默认不传，用 claude 默认模型）

工程约束（spec §7 第 4 条 / speak-human evals 同款解法）：
    - 子进程调用带 AUTO_SCAFFOLD_EVALS_HERMETIC=1，防常驻 hook 在 claude -p 里
      再次注入规则、污染判定（inject.sh 识别此变量后静默退出）；
    - 规则文件默认路径按脚本所在目录解析（../hooks/auto-scaffold.md），不依赖
      运行时 cwd，避免 speak-human 曾因默认路径依赖 cwd 踩过的坑；
    - --dry-run 只打印拼装好的 prompt，不真的调用 claude；
    - 单案例失败不中断全局：记 error 继续跑下一个。

产物：<out-dir>/results.json（逐条明细）+ <out-dir>/summary.md（通过率汇总）。
默认 out-dir 是 evals/out/，不入库（见同目录 .gitignore）。
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = SCRIPT_DIR / "cases.jsonl"
DEFAULT_RULES_PATH = SCRIPT_DIR / ".." / "hooks" / "auto-scaffold.md"
DEFAULT_OUT_DIR = SCRIPT_DIR / "out"
DEFAULT_TIMEOUT = 120.0

VALID_EXPECTED = ("trigger", "no_trigger")


class ClaudeError(Exception):
    """claude -p 调用失败（超时/找不到可执行文件/非零退出码）。"""


# ---------------------------------------------------------------------------
# claude -p 调用封装
# ---------------------------------------------------------------------------

def get_claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN", "claude")


def get_claude_model() -> Optional[str]:
    return os.environ.get("CLAUDE_MODEL") or None


def run_claude(prompt: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """非交互调用 `claude -p`，prompt 走 stdin，返回 stdout 文本。

    失败（找不到可执行文件 / 超时 / 非零退出码）一律抛 ClaudeError，
    调用方负责捕获并记 error、不中断全局。
    """
    claude_bin = get_claude_bin()
    model = get_claude_model()
    cmd = [claude_bin, "-p"]
    if model:
        cmd += ["--model", model]
    # 评测隔离：常驻 auto-scaffold hook 在 claude -p 里同样会触发（speak-human
    # 2026-08-05 同款实测坑），不隔离的话判定 prompt 会被 hook 再注入一次规则。
    env = dict(os.environ, AUTO_SCAFFOLD_EVALS_HERMETIC="1")
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=env,
        )
    except FileNotFoundError as e:
        raise ClaudeError(f"claude 可执行文件未找到: {claude_bin}") from e
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            proc.communicate(timeout=5)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        raise ClaudeError(f"claude 调用超时（{timeout}s）: {cmd}") from e
    if proc.returncode != 0:
        stderr_tail = (stderr or "").strip()[-300:]
        stdout_tail = (stdout or "").strip()[-300:]
        raise ClaudeError(
            f"claude 退出码非零（{proc.returncode}）: stderr={stderr_tail!r} stdout={stdout_tail!r}"
        )
    return stdout


# ---------------------------------------------------------------------------
# 数据装载
# ---------------------------------------------------------------------------

def load_cases(cases_path: Path, limit: Optional[int] = None) -> list[dict]:
    cases = []
    with open(cases_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if case.get("expected") not in VALID_EXPECTED:
                raise ValueError(
                    f"case {case.get('id')!r} 的 expected 字段非法: {case.get('expected')!r}"
                )
            cases.append(case)
    if limit is not None:
        cases = cases[:limit]
    return cases


def load_rules_text(rules_path: Path) -> str:
    return rules_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# prompt 拼装
# ---------------------------------------------------------------------------

def build_prompt(case: dict, rules_text: str) -> str:
    return (
        "你是 Claude Code 里的一个判定器。下面是一份规则文档，用来判断当前这轮对话"
        "是否应该触发\"自动铺设新项目\"这个动作：\n\n"
        f"{rules_text}\n\n"
        "现在给你一个具体场景，请你严格按上面的判定条款判断是否应该触发：\n\n"
        f"用户说的话：{case['user_utterance']}\n"
        f"当前目录情况：{case['cwd_context']}\n\n"
        "请只输出一个词：应该触发就输出 TRIGGER，不应该触发就输出 NO_TRIGGER。"
        "不要输出任何解释、标点或其他文字。"
    )


def parse_verdict(text: str) -> Optional[str]:
    """从模型输出里解析判定结果，返回 "trigger" / "no_trigger" / None（无法解析）。"""
    t = text.strip().upper()
    has_trigger = "NO_TRIGGER" not in t and "NO TRIGGER" not in t and "TRIGGER" in t
    has_no_trigger = "NO_TRIGGER" in t or "NO TRIGGER" in t
    if has_no_trigger and not has_trigger:
        return "no_trigger"
    if has_trigger and not has_no_trigger:
        return "trigger"
    return None


# ---------------------------------------------------------------------------
# 单案例评测
# ---------------------------------------------------------------------------

def evaluate_one(case: dict, rules_text: str, timeout: float) -> dict:
    """返回 {"prompt": str, "raw": str|None, "verdict": str|None, "correct": bool|None, "error": str|None}。"""
    prompt = build_prompt(case, rules_text)
    try:
        raw = run_claude(prompt, timeout=timeout)
    except ClaudeError as e:
        return {"prompt": prompt, "raw": None, "verdict": None, "correct": None, "error": str(e)}

    verdict = parse_verdict(raw)
    if verdict is None:
        return {
            "prompt": prompt,
            "raw": raw,
            "verdict": None,
            "correct": None,
            "error": f"无法从输出解析 TRIGGER/NO_TRIGGER: {raw.strip()[:200]!r}",
        }
    correct = verdict == case["expected"]
    return {"prompt": prompt, "raw": raw, "verdict": verdict, "correct": correct, "error": None}


# ---------------------------------------------------------------------------
# 汇总 + 输出
# ---------------------------------------------------------------------------

def render_summary_md(case_results: list[dict]) -> str:
    lines = ["# auto-scaffold evals 结果", ""]
    n = len(case_results)
    n_correct = sum(1 for r in case_results if r["result"].get("correct") is True)
    n_error = sum(1 for r in case_results if r["result"].get("error"))
    lines.append(f"案例数：{n}")
    lines.append(f"通过：{n_correct}/{n}")
    lines.append(f"出错单元数：{n_error}")
    lines.append("")
    lines.append("| id | expected | verdict | 结果 |")
    lines.append("|---|---|---|---|")
    for r in case_results:
        case = r["case"]
        result = r["result"]
        if result.get("error"):
            outcome = f"ERROR: {result['error'][:60]}"
        elif result["correct"] is True:
            outcome = "PASS"
        else:
            outcome = "FAIL"
        lines.append(
            f"| {case['id']} | {case['expected']} | {result.get('verdict') or 'n/a'} | {outcome} |"
        )
    lines.append("")
    denom = n - n_error
    rate = (n_correct / denom) if denom else None
    rate_s = f"{rate*100:.0f}%" if rate is not None else "n/a"
    lines.append(f"**通过率（不计 error 单元）**：{n_correct}/{denom}（{rate_s}）")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(
    cases_path: Path,
    rules_path: Path,
    out_dir: Path,
    limit: Optional[int],
    timeout: float,
    dry_run: bool,
) -> dict:
    cases = load_cases(cases_path, limit=limit)
    rules_text = load_rules_text(rules_path)

    case_results = []
    n = len(cases)
    for i, case in enumerate(cases, 1):
        prompt = build_prompt(case, rules_text)
        if dry_run:
            print(f"[{i}/{n}] {case['id']} ({case['expected']}) prompt:\n{prompt}\n{'-'*60}")
            case_results.append({"case": case, "result": {"prompt": prompt, "raw": None,
                                                            "verdict": None, "correct": None,
                                                            "error": None}})
            continue
        print(f"[{i}/{n}] {case['id']} ...", file=sys.stderr, flush=True)
        result = evaluate_one(case, rules_text, timeout)
        if result["error"]:
            print(f"[{i}/{n}] {case['id']} ERROR: {result['error'][:120]}", file=sys.stderr, flush=True)
        case_results.append({"case": case, "result": result})

    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        results_payload = {"cases": case_results}
        (out_dir / "results.json").write_text(
            json.dumps(results_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary_md = render_summary_md(case_results)
        (out_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    return {"cases": case_results}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="auto-scaffold evals: 判定规则 trigger/no_trigger 通过率"
    )
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 个案例（抽样）")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="单次 claude 调用超时秒数")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="只打印拼装好的 prompt，不调用 claude")
    args = parser.parse_args(argv)

    payload = run(
        cases_path=args.cases,
        rules_path=args.rules,
        out_dir=args.out_dir,
        limit=args.limit,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        summary_md = render_summary_md(payload["cases"])
        print(summary_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
