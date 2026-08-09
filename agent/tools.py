from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "sales.csv"

_df = None


class ToolError(Exception):
    pass


def get_df():
    global _df

    if _df is None:
        if not CSV_PATH.exists():
            raise ToolError(
                f"Dataset not found at {CSV_PATH}. "
                "Run: python scripts/generate_data.py"
            )

        _df = pd.read_csv(CSV_PATH)

    return _df


TOOL_SCHEMAS = [
    {
        "name": "get_schema",
        "description": "Get table schema, column names, dtypes, and row count.",
        "args": {},
    },
    {
        "name": "count_rows",
        "description": "Count the number of rows in the table.",
        "args": {},
    },
    {
        "name": "aggregate",
        "description": (
            "Aggregate a numeric column. Optionally group by another column. "
            "Supported agg_function values: sum, mean, count, min, max."
        ),
        "args": {
            "agg_column": "string, required",
            "agg_function": "string, required",
            "group_column": "string or null, optional",
        },
    },
]


def get_schema(args):
    df = get_df()

    return {
        "columns": list(df.columns),
        "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "row_count": int(len(df)),
    }


def count_rows(args):
    df = get_df()
    return {"row_count": int(len(df))}


def aggregate(args):
    df = get_df()

    agg_column = args.get("agg_column")
    agg_function = args.get("agg_function")
    group_column = args.get("group_column")

    if not agg_column:
        raise ToolError("agg_column is required.")

    if not agg_function:
        raise ToolError("agg_function is required.")

    if agg_column not in df.columns:
        raise ToolError(f"Column '{agg_column}' not found.")

    valid_functions = {"sum", "mean", "count", "min", "max"}

    if agg_function not in valid_functions:
        raise ToolError(
            f"agg_function must be one of {sorted(valid_functions)}."
        )

    if group_column:
        if group_column not in df.columns:
            raise ToolError(f"Group column '{group_column}' not found.")

        grouped = df.groupby(group_column)[agg_column].agg(agg_function)

        result = {}

        for key, value in grouped.items():
            if pd.isna(value):
                result[str(key)] = None
            elif agg_function == "count":
                result[str(key)] = int(value)
            else:
                result[str(key)] = float(value)

        return result

    value = getattr(df[agg_column], agg_function)()

    if pd.isna(value):
        return {"value": None}

    if agg_function == "count":
        return {"value": int(value)}

    return {"value": float(value)}


def execute_tool(name, args):
    args = args or {}

    if name == "get_schema":
        return get_schema(args)

    if name == "count_rows":
        return count_rows(args)

    if name == "aggregate":
        return aggregate(args)

    raise ToolError(f"Unknown tool: {name}")