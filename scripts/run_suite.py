import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.llm import MockLLM
from agent.loop import run_agent
from evaluation.checks import (
    programmatic_check,
    trajectory_check,
    graceful_error_check,
)
from evaluation.judge import HeuristicJudge
from tracing.tracer import save_trace


def load_tasks(path):
    tasks = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                tasks.append(json.loads(line))

    return tasks


def get_llm(name):
    if name == "mock":
        return MockLLM()

    if name == "mockv2":
        from agent.mock_llm_v2 import MockLLMv2

        return MockLLMv2()

    if name == "broken":
        from agent.broken_llm import BrokenMockLLM

        return BrokenMockLLM()

    raise ValueError("Unknown LLM. Use --llm mock, mockv2, or broken.")


def get_judge(name):
    if name == "heuristic":
        return HeuristicJudge()

    raise ValueError("Unknown judge. Use --judge heuristic.")


def build_failure_reasons(run, programmatic, trajectory):
    reasons = []

    if run["error"]:
        reasons.append(f"run_error:{run['error']}")

    if not programmatic["passed"]:
        reasons.append("programmatic_check_failed")

    if not trajectory["passed"]:
        if trajectory["missing_tools"]:
            reasons.append("missing_tools")

        if trajectory["used_forbidden_tools"]:
            reasons.append("used_forbidden_tools")

        if trajectory["looping_tools"]:
            reasons.append("looping")

    return reasons


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--suite",
        default=str(ROOT / "tasks" / "suite.jsonl"),
    )

    parser.add_argument(
        "--agent-version",
        default="v1",
    )

    parser.add_argument(
        "--llm",
        default="mock",
    )

    parser.add_argument(
        "--judge",
        default="heuristic",
    )

    args = parser.parse_args()

    tasks = load_tasks(args.suite)
    llm = get_llm(args.llm)
    judge = get_judge(args.judge)

    results = []

    for task in tasks:
        run = run_agent(
            task=task,
            llm=llm,
            agent_version=args.agent_version,
        )

        trace = run["trace"]

        save_trace(trace)

        expected_behavior = task.get("expected_behavior", "answer")

        if expected_behavior == "graceful_error":
            programmatic = {
                "passed": graceful_error_check(run["final_answer"]),
                "predicted": run["final_answer"],
                "expected": "graceful_error",
            }
        else:
            programmatic = programmatic_check(
                predicted=run["final_answer"],
                expected=task["expected_answer"],
            )

        trajectory = trajectory_check(
            trace=trace,
            task=task,
        )

        judge_result = judge.score(
            task=task,
            run=run,
            programmatic=programmatic,
            trajectory=trajectory,
        )

        passed = (
            programmatic["passed"]
            and trajectory["passed"]
            and run["error"] is None
        )

        failure_reasons = []

        if not passed:
            failure_reasons = build_failure_reasons(
                run=run,
                programmatic=programmatic,
                trajectory=trajectory,
            )

        results.append(
            {
                "task_id": task["task_id"],
                "difficulty": task.get("difficulty"),
                "expected_behavior": expected_behavior,
                "passed": passed,
                "programmatic_passed": programmatic["passed"],
                "trajectory_passed": trajectory["passed"],
                "judge_score": judge_result["judge_score"],
                "judge_reason": judge_result["judge_reason"],
                "judge_passed": judge_result["judge_score"] >= 2,
                "error": run["error"],
                "failure_reasons": failure_reasons,
                "final_answer": run["final_answer"],
                "expected_answer": task.get("expected_answer"),
                "called_tools": trajectory["called_tools"],
                "missing_tools": trajectory["missing_tools"],
                "total_tokens": trace["total_tokens"],
                "total_latency_ms": trace["total_latency_ms"],
                "total_cost": trace.get("total_cost", 0.0),
            }
        )

    passed_count = sum(1 for result in results if result["passed"])
    total_tasks = len(results)

    pass_rate = passed_count / total_tasks if total_tasks else 0.0

    total_cost = sum(result["total_cost"] for result in results)

    average_latency = (
        sum(result["total_latency_ms"] for result in results) / total_tasks
        if total_tasks
        else 0.0
    )

    judge_scores = [result["judge_score"] for result in results]

    average_judge_score = (
        sum(judge_scores) / total_tasks
        if total_tasks
        else 0.0
    )

    judge_passed_count = sum(1 for result in results if result["judge_passed"])

    judge_pass_rate = (
        judge_passed_count / total_tasks
        if total_tasks
        else 0.0
    )

    judge_score_counts = Counter(judge_scores)
    judge_reason_counts = Counter(result["judge_reason"] for result in results)

    difficulty_stats = {}

    for result in results:
        difficulty = result.get("difficulty") or "unknown"

        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {
                "total": 0,
                "passed": 0,
            }

        difficulty_stats[difficulty]["total"] += 1

        if result["passed"]:
            difficulty_stats[difficulty]["passed"] += 1

    for difficulty, stats in difficulty_stats.items():
        stats["pass_rate"] = (
            stats["passed"] / stats["total"]
            if stats["total"]
            else 0.0
        )

    behavior_stats = {}

    for result in results:
        behavior = result.get("expected_behavior") or "answer"

        if behavior not in behavior_stats:
            behavior_stats[behavior] = {
                "total": 0,
                "passed": 0,
            }

        behavior_stats[behavior]["total"] += 1

        if result["passed"]:
            behavior_stats[behavior]["passed"] += 1

    for behavior, stats in behavior_stats.items():
        stats["pass_rate"] = (
            stats["passed"] / stats["total"]
            if stats["total"]
            else 0.0
        )

    failure_reason_counts = Counter()

    for result in results:
        for reason in result["failure_reasons"]:
            failure_reason_counts[reason] += 1

    summary = {
        "summary": {
            "agent_version": args.agent_version,
            "llm": llm.name,
            "judge": judge.name,
            "total_tasks": total_tasks,
            "passed_tasks": passed_count,
            "pass_rate": pass_rate,
            "average_judge_score": average_judge_score,
            "judge_passed_count": judge_passed_count,
            "judge_pass_rate": judge_pass_rate,
            "judge_score_counts": dict(judge_score_counts),
            "judge_reason_counts": dict(judge_reason_counts),
            "total_cost": total_cost,
            "average_latency_ms": average_latency,
            "difficulty_stats": difficulty_stats,
            "behavior_stats": behavior_stats,
            "failure_reason_counts": dict(failure_reason_counts),
        },
        "results": results,
    }

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / f"{args.agent_version}_results.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    markdown = []

    markdown.append(f"# Agent Evaluation Report: {args.agent_version}")
    markdown.append("")
    markdown.append(f"- LLM: `{llm.name}`")
    markdown.append(f"- Judge: `{judge.name}`")
    markdown.append(f"- Total tasks: `{total_tasks}`")
    markdown.append(f"- Passed tasks: `{passed_count}`")
    markdown.append(f"- Pass rate: `{pass_rate:.2%}`")
    markdown.append(f"- Average judge score: `{average_judge_score:.2f} / 3`")
    markdown.append(f"- Judge pass rate: `{judge_pass_rate:.2%}`")
    markdown.append(f"- Total cost: `{total_cost:.6f}`")
    markdown.append(f"- Average latency: `{average_latency:.2f} ms`")
    markdown.append("")

    markdown.append("## Judge Score Breakdown")
    markdown.append("")
    markdown.append("| Judge Score | Count |")
    markdown.append("|---:|---:|")

    for score in sorted(judge_score_counts.keys()):
        markdown.append(f"| {score} | {judge_score_counts[score]} |")

    markdown.append("")

    markdown.append("## Judge Reasons")
    markdown.append("")
    markdown.append("| Judge Reason | Count |")
    markdown.append("|---|---:|")

    for reason, count in judge_reason_counts.most_common():
        markdown.append(f"| {reason} | {count} |")

    markdown.append("")

    markdown.append("## Difficulty Breakdown")
    markdown.append("")
    markdown.append("| Difficulty | Total | Passed | Pass Rate |")
    markdown.append("|---|---:|---:|---:|")

    for difficulty, stats in difficulty_stats.items():
        markdown.append(
            f"| {difficulty} | {stats['total']} | {stats['passed']} | {stats['pass_rate']:.2%} |"
        )

    markdown.append("")

    markdown.append("## Behavior Breakdown")
    markdown.append("")
    markdown.append("| Behavior | Total | Passed | Pass Rate |")
    markdown.append("|---|---:|---:|---:|")

    for behavior, stats in behavior_stats.items():
        markdown.append(
            f"| {behavior} | {stats['total']} | {stats['passed']} | {stats['pass_rate']:.2%} |"
        )

    markdown.append("")

    markdown.append("## Failure Reasons")
    markdown.append("")

    if failure_reason_counts:
        markdown.append("| Failure Reason | Count |")
        markdown.append("|---|---:|")

        for reason, count in failure_reason_counts.most_common():
            markdown.append(f"| {reason} | {count} |")
    else:
        markdown.append("No failures detected.")

    markdown.append("")

    markdown.append("## Task Results")
    markdown.append("")
    markdown.append("| Task | Difficulty | Behavior | Passed | Judge | Judge Reason | Error |")
    markdown.append("|---|---|---|---:|---:|---|---|")

    for result in results:
        markdown.append(
            "| {task_id} | {difficulty} | {behavior} | {passed} | {judge_score} | {judge_reason} | {error} |".format(
                task_id=result["task_id"],
                difficulty=result.get("difficulty", ""),
                behavior=result.get("expected_behavior", "answer"),
                passed=result["passed"],
                judge_score=result["judge_score"],
                judge_reason=result["judge_reason"],
                error=result["error"] or "",
            )
        )

    markdown_path = reports_dir / f"{args.agent_version}_report.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")

    print(json.dumps(summary["summary"], indent=2))
    print(f"JSON report saved to: {json_path}")
    print(f"Markdown report saved to: {markdown_path}")


if __name__ == "__main__":
    main()