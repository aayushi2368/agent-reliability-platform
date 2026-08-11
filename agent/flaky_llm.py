import json
import random

from .mock_llm_v2 import MockLLMv2


class FlakyMockLLM(MockLLMv2):
    """
    This agent behaves like MockLLMv2 but sometimes fails randomly.

    It is used to demonstrate flaky task detection.
    """

    name = "flaky-mock-llm"

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

        # Guaranteed flaky task.
        if "average amount by region" in question:
            if random.random() < 0.5:
                return json.dumps(
                    {
                        "action": "final_answer",
                        "answer": "not sure",
                    }
                )

        # Random invalid JSON failure.
        if assistant_count == 0 and random.random() < 0.1:
            return "I am feeling unstable."

        # Random premature final answer failure.
        if random.random() < 0.1 and "what is" in question:
            return json.dumps(
                {
                    "action": "final_answer",
                    "answer": None,
                }
            )

        return super().generate(messages)