import json

from .llm import BaseLLM


class BrokenMockLLM(BaseLLM):
    """
    This agent intentionally makes common LLM-agent mistakes.

    Failure modes:
    - invalid JSON
    - premature final answer
    - tool argument hallucination
    - unknown tool usage
    - looping
    - missing required tools
    - wrong final answer
    - poor graceful error handling
    """

    name = "broken-mock-llm"

    def generate(self, messages):
        user_message = next(
            (
                message.get("content", "")
                for message in messages
                if message.get("role") == "user"
            ),
            "",
        )

        question = user_message.lower()

        assistant_messages = [
            message
            for message in messages
            if message.get("role") == "assistant"
        ]

        assistant_count = len(assistant_messages)

        called_tools = []

        for message in assistant_messages:
            try:
                parsed = json.loads(message.get("content", ""))

                if parsed.get("action") == "tool_call":
                    called_tools.append(parsed.get("tool"))
            except Exception:
                pass

        # Failure 1: invalid JSON response.
        if "how many rows" in question and assistant_count == 0:
            return "I will count the rows now."

        # Failure 2: premature final answer without using tools.
        if "total amount" in question and "by" not in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "final_answer",
                        "answer": 999999,
                    }
                )

        # Failure 3: tool argument hallucination.
        if "total amount by region" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "get_schema",
                        "args": {},
                    }
                )

            if "aggregate" not in called_tools:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "aggregate",
                        "args": {
                            "agg_column": "revenue",
                            "agg_function": "sum",
                            "group_column": "region",
                        },
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "North": 0,
                    },
                }
            )

        # Failure 4: unknown tool usage.
        if "average amount by category" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "get_schema",
                        "args": {},
                    }
                )

            if "magic_average" not in called_tools:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "magic_average",
                        "args": {},
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "Electronics": 0,
                    },
                }
            )

        # Failure 5: looping.
        if "maximum amount by region" in question:
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "get_schema",
                    "args": {},
                }
            )

        # Failure 6: wrong final answer after correct tool usage.
        if "minimum amount by category" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "get_schema",
                        "args": {},
                    }
                )

            if "aggregate" not in called_tools:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "aggregate",
                        "args": {
                            "agg_column": "amount",
                            "agg_function": "min",
                            "group_column": "category",
                        },
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "Clothing": 999999,
                    },
                }
            )

        # Failure 7: missing required schema tool.
        if "total amount by category" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "aggregate",
                        "args": {
                            "agg_column": "amount",
                            "agg_function": "sum",
                            "group_column": "category",
                        },
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "Electronics": 0,
                    },
                }
            )

        # Failure 8: wrong answer type.
        if "average amount by region" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "get_schema",
                        "args": {},
                    }
                )

            if "aggregate" not in called_tools:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "aggregate",
                        "args": {
                            "agg_column": "amount",
                            "agg_function": "mean",
                            "group_column": "region",
                        },
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": "not sure",
                }
            )

        # Failure 9: wrong tool for grouped count.
        if "how many orders" in question:
            if assistant_count == 0:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "get_schema",
                        "args": {},
                    }
                )

            if "count_rows" not in called_tools:
                return json.dumps(
                    {
                        "action": "tool_call",
                        "tool": "count_rows",
                        "args": {},
                    }
                )

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "North": 0,
                    },
                }
            )

        # Failure 10: bad graceful error handling.
        return json.dumps(
            {
                "action": "final_answer",
                "answer": {
                    "status": "success",
                    "message": "guess",
                },
            }
        )