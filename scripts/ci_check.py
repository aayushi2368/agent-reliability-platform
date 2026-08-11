import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--results",
        required=True,
        help="Path to results JSON file, e.g. reports/ci-stable_results.json",
    )

    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=0.95,
    )

    parser.add_argument(
        "--min-judge-score",
        type=float,
        default=2.5,
    )

    args = parser.parse_args()

    results_path = Path(args.results)

    if not results_path.exists():
        raise SystemExit(f"Results file not found: {results_path}")

    data = json.loads(results_path.read_text(encoding="utf-8"))

    summary = data.get("summary", {})

    pass_rate = summary.get("pass_rate", 0.0)
    average_judge_score = summary.get("average_judge_score", 0.0)

    failures = []

    if pass_rate < args.min_pass_rate:
        failures.append(
            f"Pass rate {pass_rate:.2%} is below required {args.min_pass_rate:.2%}"
        )

    if average_judge_score < args.min_judge_score:
        failures.append(
            f"Average judge score {average_judge_score:.2f} is below required {args.min_judge_score:.2f}"
        )

    if failures:
        print("CI check failed.")

        for failure in failures:
            print(f"- {failure}")

        sys.exit(1)

    print("CI check passed.")
    print(f"- Pass rate: {pass_rate:.2%}")
    print(f"- Average judge score: {average_judge_score:.2f}")


if __name__ == "__main__":
    main()