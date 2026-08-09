import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
TASK_DIR = ROOT / "tasks"

DATA_DIR.mkdir(parents=True, exist_ok=True)
TASK_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

regions = ["North", "South", "East", "West"]
categories = ["Electronics", "Groceries", "Clothing"]

rows = []

for i in range(1, 21):
    region = regions[i % len(regions)]
    category = categories[i % len(categories)]

    amount = round(100 + i * 13.25 + random.uniform(-10, 50), 2)

    rows.append(
        {
            "order_id": i,
            "region": region,
            "category": category,
            "amount": amount,
            "order_date": f"2026-08-{(i % 28) + 1:02d}",
        }
    )

df = pd.DataFrame(rows)

csv_path = DATA_DIR / "sales.csv"
df.to_csv(csv_path, index=False)


def make_task(
    task_id,
    difficulty,
    question,
    expected_answer,
    required_tools,
    forbidden_tools=None,
):
    return {
        "task_id": task_id,
        "difficulty": difficulty,
        "question": question,
        "expected_answer": expected_answer,
        "required_tools": required_tools,
        "forbidden_tools": forbidden_tools or [],
    }


tasks = []

row_count = int(len(df))
total_amount = float(df["amount"].sum())

total_amount_by_region = {
    str(region): float(value)
    for region, value in df.groupby("region")["amount"].sum().items()
}

average_amount_by_category = {
    str(category): float(value)
    for category, value in df.groupby("category")["amount"].mean().items()
}

maximum_amount_by_region = {
    str(region): float(value)
    for region, value in df.groupby("region")["amount"].max().items()
}

tasks.append(
    make_task(
        task_id="csv_easy_001",
        difficulty="easy",
        question="How many rows are in the sales table?",
        expected_answer=row_count,
        required_tools=["get_schema", "count_rows"],
    )
)

tasks.append(
    make_task(
        task_id="csv_easy_002",
        difficulty="easy",
        question="What is the total amount?",
        expected_answer=total_amount,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="csv_medium_001",
        difficulty="medium",
        question="What is the total amount by region?",
        expected_answer=total_amount_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="csv_medium_002",
        difficulty="medium",
        question="What is the average amount by category?",
        expected_answer=average_amount_by_category,
        required_tools=["get_schema", "aggregate"],
    )
)

tasks.append(
    make_task(
        task_id="csv_medium_003",
        difficulty="medium",
        question="What is the maximum amount by region?",
        expected_answer=maximum_amount_by_region,
        required_tools=["get_schema", "aggregate"],
    )
)

suite_path = TASK_DIR / "suite.jsonl"

with open(suite_path, "w", encoding="utf-8") as f:
    for task in tasks:
        f.write(json.dumps(task) + "\n")

print(f"Dataset written to: {csv_path}")
print(f"Task suite written to: {suite_path}")
print(f"Created {len(rows)} rows and {len(tasks)} tasks.")