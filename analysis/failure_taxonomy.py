from collections import Counter, defaultdict


def classify_failure(result):
    if result.get("passed"):
        return "success"

    error = result.get("error") or ""
    failure_reasons = result.get("failure_reasons", [])
    judge_reason = result.get("judge_reason", "")
    expected_behavior = result.get("expected_behavior", "answer")

    if any("invalid_json" in reason for reason in failure_reasons) or "invalid_json" in error:
        return "invalid_response_format"

    if any("max_steps_exceeded" in reason for reason in failure_reasons) or "max_steps_exceeded" in error:
        return "agent_looping"

    if "looping" in failure_reasons:
        return "agent_looping"

    if "missing_tools" in failure_reasons:
        return "missing_required_tools"

    if "used_forbidden_tools" in failure_reasons:
        return "forbidden_tool_usage"

    if expected_behavior == "graceful_error" and "programmatic_check_failed" in failure_reasons:
        return "failed_graceful_error_handling"

    if "tool_error" in judge_reason:
        return "tool_error_not_handled"

    if "programmatic_check_failed" in failure_reasons:
        return "incorrect_final_answer"

    return "unknown_failure"


def build_failure_taxonomy(results):
    category_counts = Counter()
    examples = defaultdict(list)

    total_results = len(results)

    for result in results:
        category = classify_failure(result)

        category_counts[category] += 1

        if len(examples[category]) < 3:
            examples[category].append(
                {
                    "task_id": result.get("task_id"),
                    "difficulty": result.get("difficulty"),
                    "expected_behavior": result.get("expected_behavior"),
                    "error": result.get("error"),
                    "failure_reasons": result.get("failure_reasons", []),
                    "judge_reason": result.get("judge_reason"),
                    "final_answer_preview": str(result.get("final_answer"))[:120],
                }
            )

    total_failures = sum(
        count
        for category, count in category_counts.items()
        if category != "success"
    )

    taxonomy = []

    for category, count in category_counts.most_common():
        taxonomy.append(
            {
                "category": category,
                "count": count,
                "percentage": count / total_results if total_results else 0.0,
                "examples": examples[category],
            }
        )

    return {
        "total_results": total_results,
        "total_failures": total_failures,
        "failure_rate": total_failures / total_results if total_results else 0.0,
        "taxonomy": taxonomy,
    }