#!/usr/bin/env python3
"""evals/run_evals.py — 基线 vs 带 skill 的提问质量对比评测。

对 evals/cases.jsonl 里每个案例：
  1. 用 `claude -p` 非交互生成一版「不带 skill」的改造提问（只给案例情境）；
  2. 再用 `claude -p` 生成一版「带 skill」的改造提问（案例情境 + 注入 SKILL.md 正文）；
  3. 用 `claude -p` 当 judge，按 evals/rubric.md 逐条给两版打分（pass/fail/n/a）；
  4. 汇总各条款（P1~P8、S1~S3）通过率与总通过率，基线 vs 带 skill 对比。

用法:
    python3 evals/run_evals.py [--limit N] [--timeout SEC]
        [--cases PATH] [--rubric PATH] [--skill PATH] [--out-dir PATH]

环境变量:
    CLAUDE_BIN    claude 可执行文件路径（默认 "claude"）
    CLAUDE_MODEL  传给 `claude -p --model <值>` 的模型名（默认不传，用 claude 默认模型）

工程约束（spec §4 / ultracode U4 任务书）：
    - claude 命令路径/模型可用环境变量覆盖
    - 单案例（含单次 claude 调用）失败不中断全局：记 error 继续跑下一个
    - --limit N 支持抽样跑（取前 N 条，保证结果可复现）
    - 每次 claude 调用都有超时保护

产物：<out-dir>/results.json（结构化明细）+ <out-dir>/summary.md（人读通过率对比表）。
默认 out-dir 是 evals/out/，已在 .gitignore 里排除，不入库。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CASES_PATH = REPO_DIR / "evals" / "cases.jsonl"
DEFAULT_RUBRIC_PATH = REPO_DIR / "evals" / "rubric.md"
DEFAULT_SKILL_PATH = REPO_DIR / "SKILL.md"
DEFAULT_OUT_DIR = REPO_DIR / "evals" / "out"

ALL_RULES = [f"P{i}" for i in range(1, 9)] + [f"S{i}" for i in range(1, 4)]
DEFAULT_TIMEOUT = 120.0
VERSIONS = ("baseline", "skill")


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
    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeError(f"claude 调用超时（{timeout}s）: {cmd}") from e
    except FileNotFoundError as e:
        raise ClaudeError(f"claude 可执行文件未找到: {claude_bin}") from e
    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()[-500:]
        raise ClaudeError(f"claude 退出码非零（{result.returncode}）: {stderr_tail}")
    return result.stdout


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
            cases.append(json.loads(line))
    if limit is not None:
        cases = cases[:limit]
    return cases


def load_skill_text(skill_path: Path) -> str:
    """读 SKILL.md，剥掉开头的 YAML frontmatter（--- ... ---），只留正文。"""
    text = skill_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            if body.startswith("\n"):
                body = body[1:]
            text = body
    return text.strip()


# ---------------------------------------------------------------------------
# prompt 拼装
# ---------------------------------------------------------------------------

def build_generation_prompt(case: dict, skill_text: Optional[str]) -> str:
    """拼装「生成改造提问」的 prompt。skill_text 为 None 时是基线版，否则是带 skill 版。"""
    parts = [
        "你是 Claude Code，正在和用户讨论下面这个情境，需要立刻向用户提一个问题（可能带选项）"
        "来推进这个决策。",
    ]
    if skill_text is not None:
        parts.append(
            "在提问之前，你必须遵守以下规则文档（这是你说话方式的强制纪律，不是参考建议）：\n\n"
            f"{skill_text}"
        )
    parts.append(f"当前情境：{case['context_summary']}")
    parts.append(
        "你在提问前已用工具查证得到以下现状事实（可在提问里引用）："
        f"{case['known_facts']}"
    )
    parts.append(
        "请直接输出你会问用户的那段提问文本（含选项，如果有的话）。"
        "只输出提问本身，不要输出任何解释、前后缀或元评论。"
    )
    return "\n\n".join(parts)


def build_judge_prompt(case: dict, rubric_text: str, question_text: str) -> str:
    """拼装 judge 打分的 prompt，要求输出严格 JSON。"""
    forced = ", ".join(case["rules_tested"])
    return (
        "你是评分裁判。请依据下面的评分标准（rubric）对「改造后的提问」逐条判断"
        " P1~P8、S1~S3。\n\n"
        f"{rubric_text}\n\n"
        f"本案例的 rules_tested（强制判 pass/fail，禁止判 n/a）：{forced}\n"
        f"known_facts（用于核验 P1/P7 查证结果是否属实）：{case['known_facts']}\n\n"
        "改造后的提问文本：\n"
        "-----\n"
        f"{question_text}\n"
        "-----\n\n"
        "请只输出一个 JSON 对象，key 是你判分的条款（P1..P8, S1..S3 中的若干个），"
        'value 是 "pass" / "fail" / "n/a" 之一。rules_tested 列出的条款必须出现在这个'
        "对象里且值只能是 pass 或 fail。不要输出任何 JSON 之外的文字。"
    )


def parse_judge_response(text: str) -> Optional[dict]:
    """从 judge 的输出文本里解析 JSON 打分。解析失败返回 None。"""
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    # 容错：judge 可能在 JSON 前后夹了几句话，抓第一个 {...} 块
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _coerce_verdict(val: object) -> Optional[str]:
    """把 judge 原始值规整成 "pass"/"fail"/"n/a"，大小写与首尾空白不敏感。

    非字符串或无法识别的值返回 None（由调用方决定丢弃还是防御性判 fail）。
    """
    if not isinstance(val, str):
        return None
    v = val.strip().lower()
    if v in ("pass", "fail", "n/a"):
        return v
    return None


def normalize_scores(case: dict, raw_scores: dict) -> dict:
    """把 judge 原始输出规整成 {rule: "pass"|"fail"|"n/a"}。

    先大小写/空白归一（judge 返回 "Pass"/" FAIL "等合法语义值不应被误判），再按规则分流：
    - rules_tested 里的条款：归一后不是 pass/fail 就防御性地记 fail（judge 违反强制项时不能算过）。
    - 其余条款：归一后不是 pass/fail/n/a 就丢弃（不进分母）。
    """
    normalized = {}
    forced = set(case["rules_tested"])
    for rule in ALL_RULES:
        v = _coerce_verdict(raw_scores.get(rule))
        if rule in forced:
            normalized[rule] = v if v in ("pass", "fail") else "fail"
        else:
            if v in ("pass", "fail", "n/a"):
                normalized[rule] = v
    return normalized


# ---------------------------------------------------------------------------
# 单案例单版本评测
# ---------------------------------------------------------------------------

def evaluate_one(
    case: dict,
    skill_text: Optional[str],
    rubric_text: str,
    timeout: float,
) -> dict:
    """跑一个案例的一个版本（baseline: skill_text=None / skill: skill_text=正文）。

    返回 {"question": str|None, "scores": dict|None, "error": str|None}。
    出错时 question/scores 为 None、error 记原因，调用方据此跳过该单元的聚合，不中断全局。
    """
    gen_prompt = build_generation_prompt(case, skill_text)
    try:
        question = run_claude(gen_prompt, timeout=timeout).strip()
    except ClaudeError as e:
        return {"question": None, "scores": None, "error": f"生成失败: {e}"}

    if not question:
        return {"question": "", "scores": None, "error": "生成结果为空文本"}

    judge_prompt = build_judge_prompt(case, rubric_text, question)
    try:
        judge_raw = run_claude(judge_prompt, timeout=timeout)
    except ClaudeError as e:
        return {"question": question, "scores": None, "error": f"judge 调用失败: {e}"}

    raw_scores = parse_judge_response(judge_raw)
    if raw_scores is None:
        return {
            "question": question,
            "scores": None,
            "error": f"judge 输出无法解析为 JSON: {judge_raw[:300]!r}",
        }

    scores = normalize_scores(case, raw_scores)
    return {"question": question, "scores": scores, "error": None}


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------

def aggregate(case_results: list[dict]) -> dict:
    """按版本(baseline/skill)汇总各条款 pass/fail 计数与通过率、总通过率。"""
    summary = {}
    for version in VERSIONS:
        per_rule = {rule: {"pass": 0, "fail": 0} for rule in ALL_RULES}
        for case_result in case_results:
            scores = case_result[version].get("scores")
            if not scores:
                continue
            for rule, val in scores.items():
                if val == "pass":
                    per_rule[rule]["pass"] += 1
                elif val == "fail":
                    per_rule[rule]["fail"] += 1
        per_rule_rate = {}
        total_pass = 0
        total_denom = 0
        for rule in ALL_RULES:
            p, f = per_rule[rule]["pass"], per_rule[rule]["fail"]
            denom = p + f
            per_rule_rate[rule] = {
                "pass": p,
                "fail": f,
                "rate": (p / denom) if denom else None,
            }
            total_pass += p
            total_denom += denom
        summary[version] = {
            "per_rule": per_rule_rate,
            "total_pass": total_pass,
            "total_denom": total_denom,
            "overall_rate": (total_pass / total_denom) if total_denom else None,
        }
    return summary


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

def render_summary_md(summary: dict, case_results: list[dict]) -> str:
    lines = ["# speak-human evals 结果", ""]
    lines.append(f"案例数：{len(case_results)}")
    n_errors = sum(
        1
        for cr in case_results
        for v in VERSIONS
        if cr[v].get("error")
    )
    lines.append(f"出错单元数：{n_errors}")
    lines.append("")
    lines.append("| 条款 | 基线 pass/denom | 基线通过率 | 带 skill pass/denom | 带 skill 通过率 |")
    lines.append("|---|---|---|---|---|")
    for rule in ALL_RULES:
        b = summary["baseline"]["per_rule"][rule]
        s = summary["skill"]["per_rule"][rule]

        def fmt(entry):
            denom = entry["pass"] + entry["fail"]
            rate = f"{entry['rate']*100:.0f}%" if entry["rate"] is not None else "n/a"
            return f"{entry['pass']}/{denom}", rate

        b_frac, b_rate = fmt(b)
        s_frac, s_rate = fmt(s)
        lines.append(f"| {rule} | {b_frac} | {b_rate} | {s_frac} | {s_rate} |")

    b_overall = summary["baseline"]["overall_rate"]
    s_overall = summary["skill"]["overall_rate"]
    b_overall_s = f"{b_overall*100:.1f}%" if b_overall is not None else "n/a"
    s_overall_s = f"{s_overall*100:.1f}%" if s_overall is not None else "n/a"
    lines.append("")
    lines.append(f"**总通过率**：基线 {b_overall_s} → 带 skill {s_overall_s}")
    lines.append("")
    verdict_pass = s_overall is not None and s_overall >= 0.8 and (
        b_overall is None or s_overall > b_overall
    )
    verdict = "达线（≥80% 且显著高于基线）" if verdict_pass else "未达线，需回 SKILL.md 重新打磨措辞"
    lines.append(f"**验收线（spec §4）**：{verdict}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(
    cases_path: Path = DEFAULT_CASES_PATH,
    rubric_path: Path = DEFAULT_RUBRIC_PATH,
    skill_path: Path = DEFAULT_SKILL_PATH,
    out_dir: Path = DEFAULT_OUT_DIR,
    limit: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    cases = load_cases(cases_path, limit=limit)
    rubric_text = rubric_path.read_text(encoding="utf-8")
    skill_text = load_skill_text(skill_path)

    case_results = []
    for case in cases:
        baseline = evaluate_one(case, None, rubric_text, timeout)
        skill = evaluate_one(case, skill_text, rubric_text, timeout)
        case_results.append({"id": case["id"], "baseline": baseline, "skill": skill})

    summary = aggregate(case_results)

    out_dir.mkdir(parents=True, exist_ok=True)
    results_payload = {"cases": case_results, "summary": summary}
    (out_dir / "results.json").write_text(
        json.dumps(results_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary_md = render_summary_md(summary, case_results)
    (out_dir / "summary.md").write_text(summary_md, encoding="utf-8")

    return results_payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="speak-human evals: 基线 vs 带 skill 提问质量对比")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 个案例（抽样）")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="单次 claude 调用超时秒数")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC_PATH)
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    payload = run(
        cases_path=args.cases,
        rubric_path=args.rubric,
        skill_path=args.skill,
        out_dir=args.out_dir,
        limit=args.limit,
        timeout=args.timeout,
    )

    summary_md = render_summary_md(payload["summary"], payload["cases"])
    print(summary_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
