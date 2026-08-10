import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.failure_taxonomy import build_failure_taxonomy


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--results",
        required=True,
        help="Path to a results JSON file, e.g. reports/v4-broken_results.json",
    )

    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Prefix for taxonomy output files.",
    )

    args = parser.parse_args()

    results_path = Path(args.results)

    if not results_path.exists():
        raise SystemExit(f"Results file not found: {results_path}")

    data = json.loads(results_path.read_text(encoding="utf-8"))

    results = data.get("results", [])

    taxonomy = build_failure_taxonomy(results)

    if args.output_prefix is None:
        output_prefix = results_path.stem.replace("_results", "")
    else:
        output_prefix = args.output_prefix

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / f"{output_prefix}_failure_taxonomy.json"
    json_path.write_text(json.dumps(taxonomy, indent=2), encoding="utf-8")

    markdown = []

    markdown.append(f"# Failure Taxonomy: {output_prefix}")
    markdown.append("")
    markdown.append(f"- Total results: `{taxonomy['total_results']}`")
    markdown.append(f"- Total failures: `{taxonomy['total_failures']}`")
    markdown.append(f"- Failure rate: `{taxonomy['failure_rate']:.2%}`")
    markdown.append("")

    markdown.append("## Failure Categories")
    markdown.append("")
    markdown.append("| Category | Count | Percentage |")
    markdown.append("|---|---:|---:|")

    for item in taxonomy["taxonomy"]:
        markdown.append(
            f"| {item['category']} | {item['count']} | {item['percentage']:.2%} |"
        )

    markdown.append("")

    markdown.append("## Examples")
    markdown.append("")

    for item in taxonomy["taxonomy"]:
        markdown.append(f"### {item['category']}")
        markdown.append("")

        for example in item["examples"]:
            markdown.append(f"- Task: `{example['task_id']}`")
            markdown.append(f"  - Difficulty: `{example['difficulty']}`")
            markdown.append(f"  - Behavior: `{example['expected_behavior']}`")
            markdown.append(f"  - Error: `{example['error']}`")
            markdown.append(f"  - Judge reason: `{example['judge_reason']}`")
            markdown.append(f"  - Failure reasons: `{example['failure_reasons']}`")
            markdown.append(f"  - Final answer preview: `{example['final_answer_preview']}`")
            markdown.append("")

    markdown_path = reports_dir / f"{output_prefix}_failure_taxonomy.md"
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")

    print(json.dumps(
        {
            "total_results": taxonomy["total_results"],
            "total_failures": taxonomy["total_failures"],
            "failure_rate": taxonomy["failure_rate"],
            "categories": {
                item["category"]: item["count"]
                for item in taxonomy["taxonomy"]
            },
        },
        indent=2,
    ))

    print(f"Failure taxonomy JSON saved to: {json_path}")
    print(f"Failure taxonomy Markdown saved to: {markdown_path}")


if __name__ == "__main__":
    main()