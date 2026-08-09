import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "sales.csv"
TASK_DIR = ROOT / "tasks"

TASK_DIR.mkdir(parents=True, exist_ok=True)

if not CSV_PATH.exists():
    raise SystemExit(
        "Dataset not found. Run first: python scripts/generate_data.py"
    )

df = pd.read_csv(CSV_PATH)


def make_task(
    task_id,
    difficulty,
    question,
    expected_answer,
    required_tools,
    forbidden_tools=None,
    expected_behavior="answer",
):
    return {
        "task_id": task_id,
        "difficulty": difficulty,
        "question": question,
        "expected_answer": expected_answer,
        "required_tools": required_tools,
        "forbidden_tools": forbidden_tools or [],
        "expected_behavior": expected_behavior,
    }


def series_to_dict(series, cast=float):
    result = {}

    for key, value in series.items():
        if pd.isna(value):
            result[str(key)] = None
        else:
            result[str(key)] = cast(value)

    return result


tasks = []

# -----------------------
# Easy tasks
# -----------------------

row_count = int(len(df))
total_amount = float(df["amount"].sum())

tasks.append(
    make_task(
        task_id="v2_easy_001",
        difficulty="easy",
        question="How many rows are in the sales table?",
        expected_answer=row_count,
        required_tools=["get_schema", "count_rows"],
    )
)

tasks.append(
    make_task(
        task_id="v2_easy_002",
        difficulty="easy",
        question="What is the total amount?",
        expected_answer=total_amount,
        required_tools=["get_schema", "aggregate"],
    )
)

# -----------------------
# Medium tasks
# -----------------------

total_by_region = series_to_dict(
    df.groupby("region")["amount"].sum(),
    cast=float,
)

average_by_category = series_to_dict(
    df.groupby("category")["amount"].mean(),
    cast=float,
)

maximum_by_region = series_to_dict(
    df.groupby("region")["amount"].max(),
    cast=float,
)

minimum_by_category = series_to_dict(
    df.groupby("category")["amount"].min(),
    cast=float,
)

total_by_category = series_to_dict(
    df.groupby("category")["amount"].sum(),
    cast=float,
)

average_by_region = series_to_dict(
    df.groupby("region")["amount"].mean(),
    cast=float,
)

count_orders_by_region = series_to_dict(
    df.groupby("region")["order_id"].count(),
    cast=int,
)

tasks.append(
    make_task(
        task_id="v2_medium_001",
        difficulty="medium",
        question="What is the total amount by region?",
        expected_answer=total_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_002",
        difficulty="medium",
        question="What is the average amount by category?",
        expected_answer=average_by_category,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_003",
        difficulty="medium",
        question="What is the maximum amount by region?",
        expected_answer=maximum_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_004",
        difficulty="medium",
        question="What is the minimum amount by category?",
        expected_answer=minimum_by_category,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_005",
        difficulty="medium",
        question="What is the total amount by category?",
        expected_answer=total_by_category,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_006",
        difficulty="medium",
        question="What is the average amount by region?",
        expected_answer=average_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="v2_medium_007",
        difficulty="medium",
        question="How many orders are there by region?",
        expected_answer=count_orders_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

# -----------------------
# Adversarial tasks
# -----------------------

tasks.append(
    make_task(
        task_id="v2_adv_001",
        difficulty="adversarial",
        question="What is the total revenue by region?",
        expected_answer=None,
        required_tools=["get_schema", "aggregate"],
        expected_behavior="graceful_error",
    )
)

tasks.append(
    make_task(
        task_id="v2_adv_002",
        difficulty="adversarial",
        question="What is the average price by category?",
        expected_answer=None,
        required_tools=["get_schema", "aggregate"],
        expected_behavior="graceful_error",
    )
)

tasks.append(
    make_task(
        task_id="v2_adv_003",
        difficulty="adversarial",
        question="What is the total amount by city?",
        expected_answer=None,
        required_tools=["get_schema", "aggregate"],
        expected_behavior="graceful_error",
    )
)

tasks.append(
    make_task(
        task_id="v2_adv_004",
        difficulty="adversarial",
        question="What is the median amount by region?",
        expected_answer=None,
        required_tools=["get_schema", "aggregate"],
        expected_behavior="graceful_error",
    )
)

tasks.append(
    make_task(
        task_id="v2_adv_005",
        difficulty="adversarial",
        question="What is the total amount by region and category?",
        expected_answer=None,
        required_tools=["get_schema", "aggregate"],
        expected_behavior="graceful_error",
    )
)

suite_path = TASK_DIR / "suite_v2.jsonl"

with open(suite_path, "w", encoding="utf-8") as f:
    for task in tasks:
        f.write(json.dumps(task) + "\n")

print(f"Created {len(tasks)} tasks.")
print(f"Task suite written to: {suite_path}")