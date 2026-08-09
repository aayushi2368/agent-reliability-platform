import json
from collections import Counter


def to_float_if_possible(value):
    try:
        return float(value)
    except Exception:
        return None


def answers_equal(predicted, expected, tol=0.01):
    if expected is None:
        return predicted is None

    if isinstance(expected, bool) or isinstance(predicted, bool):
        return predicted == expected

    expected_float = to_float_if_possible(expected)
    predicted_float = to_float_if_possible(predicted)

    if expected_float is not None and predicted_float is not None:
        return abs(predicted_float - expected_float) <= tol

    if isinstance(expected, dict):
        if not isinstance(predicted, dict):
            return False

        expected_dict = {str(key): value for key, value in expected.items()}
        predicted_dict = {str(key): value for key, value in predicted.items()}

        if set(expected_dict.keys()) != set(predicted_dict.keys()):
            return False

        return all(
            answers_equal(predicted_dict[key], expected_dict[key], tol)
            for key in expected_dict
        )

    if isinstance(expected, list):
        if not isinstance(predicted, list):
            return False

        if len(expected) != len(predicted):
            return False

        try:
            expected_sorted = sorted(
                expected,
                key=lambda item: json.dumps(item, sort_keys=True),
            )
            predicted_sorted = sorted(
                predicted,
                key=lambda item: json.dumps(item, sort_keys=True),
            )
        except Exception:
            expected_sorted = expected
            predicted_sorted = predicted

        return all(
            answers_equal(predicted_item, expected_item, tol)
            for predicted_item, expected_item in zip(
                predicted_sorted,
                expected_sorted,
            )
        )

    return predicted == expected


def programmatic_check(predicted, expected, tol=0.01):
    passed = answers_equal(predicted, expected, tol=tol)

    return {
        "passed": passed,
        "predicted": predicted,
        "expected": expected,
    }


def trajectory_check(trace, task):
    called_tools = []

    for step in trace.get("steps", []):
        if step.get("type") == "tool_call":
            called_tools.append(step.get("tool"))

    required_tools = task.get("required_tools", [])
    forbidden_tools = task.get("forbidden_tools", [])

    missing_tools = [
        tool
        for tool in required_tools
        if tool not in called_tools
    ]

    used_forbidden_tools = [
        tool
        for tool in forbidden_tools
        if tool in called_tools
    ]

    tool_counts = Counter(called_tools)

    looping_tools = [
        tool
        for tool, count in tool_counts.items()
        if count >= 4
    ]

    passed = (
        not missing_tools
        and not used_forbidden_tools
        and not looping_tools
        and trace.get("error") is None
    )

    return {
        "passed": passed,
        "called_tools": called_tools,
        "missing_tools": missing_tools,
        "used_forbidden_tools": used_forbidden_tools,
        "looping_tools": looping_tools,
    }


def graceful_error_check(final_answer):
    return (
        isinstance(final_answer, dict)
        and final_answer.get("status") == "error"
        and bool(final_answer.get("message"))
    )