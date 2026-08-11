import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.failure_taxonomy import classify_failure


def load_results(path):
    path = Path(path)

    if not path.exists():
        raise SystemExit(f"Results file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    return data


def safe_average(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def category_counts(results):
    counts = Counter()

    for result in results:
        counts[classify_failure(result)] += 1

    return dict(counts)


def paired_bootstrap_pass_rate(baseline_flags, candidate_flags, iterations=1000, seed=42):
    n = len(baseline_flags)

    if n == 0:
        return None, None

    rng = random.Random(seed)

    differences = []

    for _ in range(iterations):
        sampled_indices = [rng.randrange(n) for _ in range(n)]

        baseline_rate = sum(
            baseline_flags[index]
            for index in sampled_indices
        ) / n

        candidate_rate = sum(
            candidate_flags[index]
            for index in sampled_indices
        ) / n

        differences.append(candidate_rate - baseline_rate)

    differences.sort()

    lower_index = int(0.025 * len(differences))
    upper_index = int(0.975 * len(differences))

    if upper_index >= len(differences):
        upper_index = len(differences) - 1

    return differences[lower_index], differences[upper_index]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--baseline",
        required=True,
        help="Baseline results JSON file, e.g. reports/v3-judge_results.json",
    )

    parser.add_argument(
        "--candidate",
        required=True,
        help="Candidate results JSON file, e.g. reports/v4-broken_results.json",
    )

    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Prefix for comparison output files.",
    )

    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with error code if a significant regression is detected.",
    )

    args = parser.parse_args()

    baseline_data = load_results(args.baseline)
    candidate_data = load_results(args.candidate)

    baseline_results = baseline_data.get("results", [])
    candidate_results = candidate_data.get("results", [])

    baseline_by_task = {
        result["task_id"]: result
        for result in baseline_results
    }

    candidate_by_task = {
        result["task_id"]: result
        for result in candidate_results
    }

    common_task_ids = sorted(
        set(baseline_by_task.keys()) & set(candidate_by_task.keys())
    )

    baseline_only_task_ids = sorted(
        set(baseline_by_task.keys()) - set(candidate_by_task.keys())
    )

    candidate_only_task_ids = sorted(
        set(candidate_by_task.keys()) - set(baseline_by_task.keys())
    )

    baseline_pass_flags = []
    candidate_pass_flags = []

    baseline_judge_scores = []
    candidate_judge_scores = []

    baseline_costs = []
    candidate_costs = []

    baseline_latencies = []
    candidate_latencies = []

    regressed_tasks = []
    improved_tasks = []

    for task_id in common_task_ids:
        baseline_result = baseline_by_task[task_id]
        candidate_result = candidate_by_task[task_id]

        baseline_passed = 1 if baseline_result.get("passed") else 0
        candidate_passed = 1 if candidate_result.get("passed") else 0

        baseline_pass_flags.append(baseline_passed)
        candidate_pass_flags.append(candidate_passed)

        baseline_judge_scores.append(baseline_result.get("judge_score", 0))
        candidate_judge_scores.append(candidate_result.get("judge_score", 0))

        baseline_costs.append(baseline_result.get("total_cost", 0.0))
        candidate_costs.append(candidate_result.get("total_cost", 0.0))

        baseline_latencies.append(baseline_result.get("total_latency_ms", 0.0))
        candidate_latencies.append(candidate_result.get("total_latency_ms", 0.0))

        if baseline_passed == 1 and candidate_passed == 0:
            regressed_tasks.append(
                {
                    "task_id": task_id,
                    "baseline_judge_score": baseline_result.get("judge_score"),
                    "candidate_judge_score": candidate_result.get("judge_score"),
                    "candidate_failure_reasons": candidate_result.get("failure_reasons", []),
                    "candidate_judge_reason": candidate_result.get("judge_reason"),
                }
            )

        if baseline_passed == 0 and candidate_passed == 1:
            improved_tasks.append(
                {
                    "task_id": task_id,
                    "baseline_judge_score": baseline_result.get("judge_score"),
                    "candidate_judge_score": candidate_result.get("judge_score"),
                    "baseline_failure_reasons": baseline_result.get("failure_reasons", []),
                    "candidate_judge_reason": candidate_result.get("judge_reason"),
                }
            )

    baseline_pass_rate = safe_average(baseline_pass_flags)
    candidate_pass_rate = safe_average(candidate_pass_flags)
    pass_rate_delta = candidate_pass_rate - baseline_pass_rate

    baseline_average_judge = safe_average(baseline_judge_scores)
    candidate_average_judge = safe_average(candidate_judge_scores)
    judge_score_delta = candidate_average_judge - baseline_average_judge

    baseline_total_cost = sum(baseline_costs)
    candidate_total_cost = sum(candidate_costs)
    cost_delta = candidate_total_cost - baseline_total_cost

    baseline_average_latency = safe_average(baseline_latencies)
    candidate_average_latency = safe_average(candidate_latencies)
    latency_delta = candidate_average_latency - baseline_average_latency

    lower_ci, upper_ci = paired_bootstrap_pass_rate(
    baseline_pass_flags,
    candidate_pass_flags,
)

    if lower_ci is None:
        regression_status = "not_enough_tasks"
    elif upper_ci < 0:
        regression_status = "significant_regression"
    elif lower_ci > 0:
        regression_status = "significant_improvement"
    else:
        regression_status = "no_significant_change"

    baseline_categories = category_counts(
        [baseline_by_task[task_id] for task_id in common_task_ids]
    )

    candidate_categories = category_counts(
        [candidate_by_task[task_id] for task_id in common_task_ids]
    )

    all_categories = sorted(
        set(baseline_categories.keys()) | set(candidate_categories.keys())
    )

    category_comparison = []

    for category in all_categories:
        baseline_count = baseline_categories.get(category, 0)
        candidate_count = candidate_categories.get(category, 0)

        category_comparison.append(
            {
                "category": category,
                "baseline_count": baseline_count,
                "candidate_count": candidate_count,
                "delta": candidate_count - baseline_count,
            }
        )

    comparison = {
        "baseline_file": str(args.baseline),
        "candidate_file": str(args.candidate),
        "baseline_agent_version": baseline_data.get("summary", {}).get("agent_version"),
        "candidate_agent_version": candidate_data.get("summary", {}).get("agent_version"),
        "common_tasks": len(common_task_ids),
        "baseline_only_tasks": baseline_only_task_ids,
        "candidate_only_tasks": candidate_only_task_ids,
        "baseline_pass_rate": baseline_pass_rate,
        "candidate_pass_rate": candidate_pass_rate,
        "pass_rate_delta": pass_rate_delta,
        "bootstrap_ci_95": {
            "lower": lower_ci,
            "upper": upper_ci,
        },
        "regression_status": regression_status,
        "baseline_average_judge_score": baseline_average_judge,
        "candidate_average_judge_score": candidate_average_judge,
        "judge_score_delta": judge_score_delta,
        "baseline_total_cost": baseline_total_cost,
        "candidate_total_cost": candidate_total_cost,
        "cost_delta": cost_delta,
        "baseline_average_latency_ms": baseline_average_latency,
        "candidate_average_latency_ms": candidate_average_latency,
        "latency_delta_ms": latency_delta,
        "regressed_tasks": regressed_tasks,
        "improved_tasks": improved_tasks,
        "category_comparison": category_comparison,
    }

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if args.output_prefix is None:
        baseline_name = Path(args.baseline).stem.replace("_results", "")
        candidate_name = Path(args.candidate).stem.replace("_results", "")
        output_prefix = f"{baseline_name}_vs_{candidate_name}"
    else:
        output_prefix = args.output_prefix

    json_path = reports_dir / f"{output_prefix}_comparison.json"
    json_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    markdown = []

    markdown.append(f"# Regression Comparison: {output_prefix}")
    markdown.append("")
    markdown.append(f"- Baseline: `{comparison['baseline_agent_version']}`")
    markdown.append(f"- Candidate: `{comparison['candidate_agent_version']}`")
    markdown.append(f"- Common tasks: `{comparison['common_tasks']}`")
    markdown.append("")

    markdown.append("## Main Metrics")
    markdown.append("")
    markdown.append("| Metric | Baseline | Candidate | Delta |")
    markdown.append("|---|---:|---:|---:|")
    markdown.append(
        f"| Pass rate | {baseline_pass_rate:.2%} | {candidate_pass_rate:.2%} | {pass_rate_delta:+.2%} |"
    )
    markdown.append(
        f"| Average judge score | {baseline_average_judge:.2f} | {candidate_average_judge:.2f} | {judge_score_delta:+.2f} |"
    )
    markdown.append(
        f"| Total cost | {baseline_total_cost:.6f} | {candidate_total_cost:.6f} | {cost_delta:+.6f} |"
    )
    markdown.append(
        f"| Average latency ms | {baseline_average_latency:.2f} | {candidate_average_latency:.2f} | {latency_delta:+.2f} |"
    )
    markdown.append("")

    markdown.append("## Regression Status")
    markdown.append("")
    markdown.append(f"`{regression_status}`")
    markdown.append("")

    if lower_ci is not None:
        markdown.append(
            f"95% bootstrap CI for pass-rate difference: `[{lower_ci:+.3f}, {upper_ci:+.3f}]`"
        )
        markdown.append("")

    markdown.append("## Category Changes")
    markdown.append("")
    markdown.append("| Category | Baseline | Candidate | Delta |")
    markdown.append("|---|---:|---:|---:|")

    for item in category_comparison:
        markdown.append(
            f"| {item['category']} | {item['baseline_count']} | {item['candidate_count']} | {item['delta']:+d} |"
        )

    markdown.append("")

    markdown.append("## Regressed Tasks")
    markdown.append("")

    if regressed_tasks:
        markdown.append("| Task | Candidate Judge Score | Candidate Judge Reason |")
        markdown.append("|---|---:|---|")

        for task in regressed_tasks:
            markdown.append(
                f"| {task['task_id']} | {task['candidate_judge_score']} | {task['candidate_judge_reason']} |"
            )
    else:
        markdown.append("No regressed tasks detected.")

    markdown.append("")

    markdown.append("## Improved Tasks")
    markdown.append("")

    if improved_tasks:
        markdown.append("| Task | Candidate Judge Score | Candidate Judge Reason |")
        markdown.append("|---|---:|---|")

        for task in improved_tasks:
            markdown.append(
                f"| {task['task_id']} | {task['candidate_judge_score']} | {task['candidate_judge_reason']} |"
            )
    else:
        markdown.append("No improved tasks detected.")

    markdown_path = reports_dir / f"{output_prefix}_comparison.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")

    print(
        json.dumps(
            {
                "baseline_agent_version": comparison["baseline_agent_version"],
                "candidate_agent_version": comparison["candidate_agent_version"],
                "common_tasks": comparison["common_tasks"],
                "baseline_pass_rate": baseline_pass_rate,
                "candidate_pass_rate": candidate_pass_rate,
                "pass_rate_delta": pass_rate_delta,
                "regression_status": regression_status,
                "bootstrap_ci_95": comparison["bootstrap_ci_95"],
            },
            indent=2,
        )
    )

    print(f"Comparison JSON saved to: {json_path}")
    print(f"Comparison Markdown saved to: {markdown_path}")

    if args.fail_on_regression and regression_status == "significant_regression":
        raise SystemExit("Significant regression detected.")


if __name__ == "__main__":
    main()