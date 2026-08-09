import json

from .llm import BaseLLM


class MockLLMv2(BaseLLM):
    """
    Improved mock agent for Phase 2.

    It supports:
    - more aggregation tasks
    - invalid column tasks
    - unsupported aggregation tasks
    - graceful error handling
    """

    name = "mock-llm-v2"

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

        last_tool_payload = None

        for message in reversed(messages):
            if message.get("role") == "tool":
                try:
                    last_tool_payload = json.loads(message.get("content", "{}"))
                except Exception:
                    last_tool_payload = message.get("content")

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

        # Step 2: if latest tool returned an error, stop gracefully.
        if isinstance(last_tool_payload, dict) and last_tool_payload.get("error"):
            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": {
                        "status": "error",
                        "message": str(last_tool_payload["error"]),
                    },
                }
            )

        # Step 3: if we already called the task tool, produce final answer.
        if (
            "count_rows" in called_tools
            or "aggregate" in called_tools
        ) and last_tool_payload is not None:
            if isinstance(last_tool_payload, dict):
                if "row_count" in last_tool_payload and len(last_tool_payload) == 1:
                    answer = last_tool_payload["row_count"]
                elif "value" in last_tool_payload and len(last_tool_payload) == 1:
                    answer = last_tool_payload["value"]
                else:
                    answer = last_tool_payload
            else:
                answer = last_tool_payload

            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": answer,
                }
            )

        # Step 4: decide next action from the question.
        intent = self.extract_intent(question)

        if intent["type"] == "count_rows":
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "count_rows",
                    "args": {},
                }
            )

        if intent["type"] == "aggregate":
            return json.dumps(
                {
                    "action": "tool_call",
                    "tool": "aggregate",
                    "args": {
                        "agg_column": intent["agg_column"],
                        "agg_function": intent["agg_function"],
                        "group_column": intent["group_column"],
                    },
                }
            )

        # Unsupported question.
        return json.dumps(
            {
                "action": "final_answer",
                "answer": {
                    "status": "error",
                    "message": "unsupported_question",
                },
            }
        )

    def extract_intent(self, question):
        q = question.replace("?", "").strip()

        if "how many rows" in q:
            return {
                "type": "count_rows",
            }

        agg_function = None

        if "total" in q:
            agg_function = "sum"
        elif "average" in q or "mean" in q:
            agg_function = "mean"
        elif "maximum" in q or "max" in q:
            agg_function = "max"
        elif "minimum" in q or "min" in q:
            agg_function = "min"
        elif "median" in q:
            agg_function = "median"
        elif "how many orders" in q:
            agg_function = "count"

        if agg_function is None:
            return {
                "type": "unsupported",
            }

        if "how many orders" in q:
            agg_column = "order_id"
        elif "amount" in q:
            agg_column = "amount"
        elif "revenue" in q:
            agg_column = "revenue"
        elif "price" in q:
            agg_column = "price"
        else:
            agg_column = "amount"

        group_column = None

        if " by " in q:
            group_text = q.split(" by ", 1)[1].strip()

            if " and " in group_text:
                group_column = group_text
            elif "region" in group_text:
                group_column = "region"
            elif "category" in group_text:
                group_column = "category"
            elif "city" in group_text:
                group_column = "city"
            else:
                group_column = group_text

        return {
            "type": "aggregate",
            "agg_function": agg_function,
            "agg_column": agg_column,
            "group_column": group_column,
        }