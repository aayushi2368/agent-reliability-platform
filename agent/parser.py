import json


def strip_code_fences(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()

        return "\n".join(lines[1:]).strip()

    return text


def parse_agent_response(text):
    try:
        cleaned = strip_code_fences(text)
        data = json.loads(cleaned)
    except Exception as exc:
        return {
            "valid": False,
            "error": f"invalid_json: {exc}",
        }

    action = data.get("action")

    if action == "tool_call":
        tool = data.get("tool")
        args = data.get("args", {})

        if not tool:
            return {
                "valid": False,
                "error": "missing_tool",
            }

        if not isinstance(args, dict):
            return {
                "valid": False,
                "error": "args_must_be_dict",
            }

        return {
            "valid": True,
            "action": "tool_call",
            "tool": tool,
            "args": args,
        }

    if action == "final_answer":
        return {
            "valid": True,
            "action": "final_answer",
            "answer": data.get("answer"),
        }

    return {
        "valid": False,
        "error": "unknown_action",
    }