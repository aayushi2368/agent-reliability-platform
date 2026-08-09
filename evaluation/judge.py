class BaseJudge:
    name = "base-judge"

    def score(self, task, run, programmatic, trajectory):
        raise NotImplementedError


def has_tool_error(trace):
    for step in trace.get("steps", []):
        if step.get("type") == "tool_call" and step.get("error"):
            return True

    return False


def final_is_graceful_error(final_answer):
    return (
        isinstance(final_answer, dict)
        and final_answer.get("status") == "error"
        and bool(final_answer.get("message"))
    )


class HeuristicJudge(BaseJudge):
    """
    Rule-based judge.

    This is a placeholder until you add a real LLM judge.

    Scoring:
    0 = bad
    1 = weak
    2 = acceptable
    3 = strong
    """

    name = "heuristic-judge"

    def score(self, task, run, programmatic, trajectory):
        expected_behavior = task.get("expected_behavior", "answer")

        if run.get("error"):
            return {
                "judge_score": 0,
                "judge_reason": f"run_error:{run['error']}",
            }

        if expected_behavior == "graceful_error":
            if final_is_graceful_error(run.get("final_answer")):
                return {
                    "judge_score": 3,
                    "judge_reason": "graceful_error_handled",
                }

            if has_tool_error(run.get("trace", {})):
                return {
                    "judge_score": 1,
                    "judge_reason": "tool_error_but_no_graceful_final_answer",
                }

            return {
                "judge_score": 0,
                "judge_reason": "expected_error_but_no_error",
            }

        # Normal answer tasks.
        if programmatic["passed"] and trajectory["passed"]:
            return {
                "judge_score": 3,
                "judge_reason": "correct_and_proper_trajectory",
            }

        if programmatic["passed"] and not trajectory["passed"]:
            return {
                "judge_score": 2,
                "judge_reason": "correct_answer_but_trajectory_issue",
            }

        if not programmatic["passed"] and trajectory["passed"]:
            if has_tool_error(run.get("trace", {})):
                return {
                    "judge_score": 1,
                    "judge_reason": "wrong_answer_after_tool_error",
                }

            return {
                "judge_score": 1,
                "judge_reason": "trajectory_ok_but_wrong_answer",
            }

        return {
            "judge_score": 0,
            "judge_reason": "failed_programmatic_and_trajectory",
        }