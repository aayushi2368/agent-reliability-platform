import json
import time
import uuid

from .parser import parse_agent_response
from .tools import TOOL_SCHEMAS, ToolError, execute_tool

SYSTEM_PROMPT = (
    "You are a data-analysis agent.\n"
    "You have access to the following tools:\n"
    f"{json.dumps(TOOL_SCHEMAS, indent=2)}\n\n"
    "Respond ONLY with JSON.\n\n"
    "If you need to call a tool, use this format:\n"
    '{"action": "tool_call", "tool": "<tool_name>", "args": { ... }}\n\n'
    "If you are ready to answer, use this format:\n"
    '{"action": "final_answer", "answer": <answer>}\n\n'
    "Rules:\n"
    "- Do not output any text outside JSON.\n"
    "- Use tools before answering.\n"
    "- Use only existing columns.\n"
    "- If a tool returns an error, try to recover.\n"
)


def run_agent(task, llm, agent_version="v1", max_steps=8):
    trace_id = str(uuid.uuid4())

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": task["question"],
        },
    ]

    trace = {
        "trace_id": trace_id,
        "task_id": task["task_id"],
        "agent_version": agent_version,
        "llm": llm.name,
        "steps": [],
        "total_tokens": 0,
        "total_latency_ms": 0.0,
        "error": None,
    }

    final_answer = None
    error = None

    for step in range(max_steps):
        llm_start = time.time()
        response = llm.generate(messages)
        llm_latency = (time.time() - llm_start) * 1000

        tokens = llm.estimate_tokens(messages) + len(response) // 4
        trace["total_tokens"] += tokens
        trace["total_latency_ms"] += llm_latency

        trace["steps"].append(
            {
                "type": "llm_call",
                "step": step,
                "latency_ms": llm_latency,
                "tokens": tokens,
                "response_preview": response[:200],
            }
        )

        messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        parsed = parse_agent_response(response)

        if not parsed["valid"]:
            error = parsed["error"]
            trace["error"] = error
            break

        if parsed["action"] == "final_answer":
            final_answer = parsed["answer"]
            trace["final_answer"] = final_answer
            break

        tool_name = parsed["tool"]
        tool_args = parsed.get("args", {})

        tool_start = time.time()

        try:
            tool_result = execute_tool(tool_name, tool_args)
            tool_error = False
        except ToolError as exc:
            tool_result = {"error": str(exc)}
            tool_error = True

        tool_latency = (time.time() - tool_start) * 1000
        trace["total_latency_ms"] += tool_latency

        tool_content = json.dumps(tool_result)

        trace["steps"].append(
            {
                "type": "tool_call",
                "step": step,
                "tool": tool_name,
                "args": tool_args,
                "latency_ms": tool_latency,
                "error": tool_error,
                "result_preview": tool_content[:200],
            }
        )

        messages.append(
            {
                "role": "tool",
                "content": tool_content,
            }
        )

    else:
        error = "max_steps_exceeded"
        trace["error"] = error

    trace["total_cost"] = trace["total_tokens"] * 0.000001

    return {
        "final_answer": final_answer,
        "trace": trace,
        "error": error,
    }