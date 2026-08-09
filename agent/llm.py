import json


class BaseLLM:
    name = "base"

    def generate(self, messages):
        raise NotImplementedError

    def estimate_tokens(self, messages):
        total_chars = sum(
            len(str(message.get("content", "")))
            for message in messages
        )

        return max(1, total_chars // 4)


class MockLLM(BaseLLM):
    """
    This mock LLM lets you run the full Project B pipeline
    without paying for an API key.

    It is not intelligent. It only follows a scripted policy
    for the generated task suite.
    """

    name = "mock-llm"

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

        called_tools = []

        for message in assistant_messages:
            try:
                parsed = json.loads(message.get("content", ""))

                if parsed.get("action") == "tool_call":
                    called_tools.append(parsed.get("tool"))
            except Exception:
                pass

        last_tool_message = None

        for message in reversed(messages):
            if message.get("role") == "tool":
                last_tool_message = message
                break

        # Step 1: always inspect schema first.
        if len(assistant_messages) == 0:
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "get_schema",
                    "args": {},
                }
            )

        # Step 2: choose task-specific tool.
        if "how many rows" in question and "count_rows" not in called_tools:
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "count_rows",
                    "args": {},
                }
            )

        if (
            "total amount by region" in question
            and "aggregate" not in called_tools
        ):
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "aggregate",
                    "args": {
                        "agg_column": "amount",
                        "agg_function": "sum",
                        "group_column": "region",
                    },
                }
            )

        if (
            "average amount by category" in question
            and "aggregate" not in called_tools
        ):
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "aggregate",
                    "args": {
                        "agg_column": "amount",
                        "agg_function": "mean",
                        "group_column": "category",
                    },
                }
            )

        if (
            "maximum amount by region" in question
            and "aggregate" not in called_tools
        ):
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "aggregate",
                    "args": {
                        "agg_column": "amount",
                        "agg_function": "max",
                        "group_column": "region",
                    },
                }
            )

        if (
            "total amount" in question
            and "by" not in question
            and "aggregate" not in called_tools
        ):
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "aggregate",
                    "args": {
                        "agg_column": "amount",
                        "agg_function": "sum",
                    },
                }
            )

        # Step 3: convert latest tool result into final answer.
        if last_tool_message is not None:
            try:
                payload = json.loads(last_tool_message.get("content", "{}"))
            except Exception:
                payload = last_tool_message.get("content")

            if isinstance(payload, dict):
                if "error" in payload:
                    answer = None
                elif "row_count" in payload and len(payload) == 1:
                    answer = payload["row_count"]
                elif "value" in payload and len(payload) == 1:
                    answer = payload["value"]
                else:
                    answer = payload
            else:
                answer = payload

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": answer,
                }
            )

        return json.dumps(
            {
                "action": "final_answer",
                "answer": None,
            }
        )