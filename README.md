# Agent Reliability Platform

An evaluation and regression-testing harness for LLM-style tool-calling agents.

This project builds a small CSV data-analysis agent and, more importantly, a reliability system around it.

The goal is not just to build an agent, but to answer:

```text
Is the agent reliable?
Did a prompt/code change make it worse?
Which tasks are flaky?
Why does it fail?
How much does it cost?
```

---

## Project Overview

This project contains:

- A hand-rolled agent loop
- Tool calling and tool execution
- CSV analysis tasks with verifiable ground truth
- Span-level tracing
- Programmatic answer checking
- Trajectory checking
- Graceful error handling
- Heuristic judge scoring
- Failure taxonomy
- Regression comparison
- Repeated runs and flaky task detection
- CI quality gate

The current version uses mock LLMs so the full evaluation pipeline can run without external API keys.

A real LLM can be plugged in later.

---

## Core Idea

```text
Task Suite
    |
    v
Agent Runner
    |
    v
LLM / MockLLM
    |
    v
Tool Calls
    |
    v
Tool Executor
    |
    v
Observations
    |
    v
Final Answer
    |
    v
Trace Logger
    |
    v
Evaluators
    |
    v
Judge
    |
    v
Failure Taxonomy
    |
    v
Regression Comparison
```

---

## What the Agent Does

The agent answers questions from a small CSV dataset.

Example questions:

```text
How many rows are in the sales table?
What is the total amount?
What is the total amount by region?
What is the average amount by category?
What is the maximum amount by region?
```

The agent uses tools such as:

```text
get_schema
count_rows
aggregate
```

---

## Task Suite

The suite contains:

```text
Easy tasks
Medium tasks
Adversarial tasks
Graceful error tasks
```

Example adversarial tasks:

```text
What is the total revenue by region?
What is the average price by category?
What is the total amount by city?
What is the median amount by region?
```

These tasks test whether the agent can fail gracefully instead of hallucinating.

---

## Evaluation Layers

### 1. Programmatic Checks

These checks verify whether the final answer matches the ground truth.

Examples:

```text
numeric comparison
dictionary comparison
tolerance-based comparison
graceful error checking
```

### 2. Trajectory Checks

These checks verify whether the agent used tools correctly.

Examples:

```text
Did it call required tools?
Did it skip important tools?
Did it use forbidden tools?
Did it loop?
```

### 3. Judge Scoring

A judge scores each run from 0 to 3.

Current judge:

```text
HeuristicJudge
```

Future judge:

```text
LLM-as-judge with calibration
```

---

## Failure Taxonomy

The project classifies failures into categories such as:

```text
invalid_response_format
missing_required_tools
agent_looping
incorrect_final_answer
tool_error_not_handled
failed_graceful_error_handling
forbidden_tool_usage
unknown_failure
```

This helps prioritize fixes instead of only looking at pass rate.

---

## Regression Comparison

The comparison script compares two agent versions.

It checks:

```text
pass rate difference
judge score difference
cost difference
latency difference
failure category changes
regressed tasks
improved tasks
statistical significance using paired bootstrap
```

Example:

```bash
python scripts/compare_versions.py \
  --baseline reports/v3-judge_results.json \
  --candidate reports/v4-broken_results.json
```

---

## Repeated Runs and Flaky Detection

LLM agents can be non-deterministic.

The repeated runner runs each task multiple times and detects flaky tasks.

A task is marked flaky if:

```text
it passes at least once
and fails at least once
```

Example:

```bash
python scripts/run_repeated_suite.py \
  --suite tasks/suite_v2.jsonl \
  --agent-version v6-flaky \
  --llm flaky \
  --judge heuristic \
  --runs 5
```

---

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Generate Dataset and Tasks

```bash
python scripts/generate_data.py
python scripts/generate_suite_v2.py
```

---

## Run Evaluation

Run the stable mock agent:

```bash
python scripts/run_suite.py \
  --suite tasks/suite_v2.jsonl \
  --agent-version v3-judge \
  --llm mockv2 \
  --judge heuristic
```

Run the broken agent:

```bash
python scripts/run_suite.py \
  --suite tasks/suite_v2.jsonl \
  --agent-version v4-broken \
  --llm broken \
  --judge heuristic
```

Run failure taxonomy:

```bash
python scripts/run_failure_analysis.py \
  --results reports/v4-broken_results.json \
  --output-prefix v4-broken
```

Run regression comparison:

```bash
python scripts/compare_versions.py \
  --baseline reports/v3-judge_results.json \
  --candidate reports/v4-broken_results.json
```

Run repeated flaky evaluation:

```bash
python scripts/run_repeated_suite.py \
  --suite tasks/suite_v2.jsonl \
  --agent-version v6-flaky \
  --llm flaky \
  --judge heuristic \
  --runs 5
```

---

## Outputs

Reports are saved in:

```text
reports/
```

Examples:

```text
v3-judge_results.json
v3-judge_report.md
v4-broken_failure_taxonomy.md
v3-judge_vs_v4-broken_comparison.md
v6-flaky_repeated_report.md
```

Traces are saved in:

```text
reports/traces/
```

---

## Project Phases Completed

### Phase 1

Built the MVP:

```text
CSV dataset generator
task suite generator
tool executor
agent loop
trace logging
programmatic checks
trajectory checks
report generation
```

### Phase 2

Expanded the harness:

```text
easy, medium, adversarial tasks
graceful error handling
failure reason tracking
improved mock agent
difficulty-wise reporting
```

### Phase 3

Added judge system:

```text
BaseJudge
HeuristicJudge
judge score
judge reason
judge pass rate
```

### Phase 4

Added failure taxonomy:

```text
failure classification
failure examples
broken agent demonstration
failure report
```

### Phase 5

Added regression comparison:

```text
baseline vs candidate
pass rate delta
judge score delta
failure category delta
paired bootstrap confidence interval
```

### Phase 6

Added repeated runs:

```text
multiple runs per task
task stability
flaky task detection
repeated-run reporting
```

### Phase 7

Finalized project:

```text
CI quality gate
GitHub Action
README polish
project freeze
```

---

## Future Work

Possible next improvements:

```text
Plug in a real LLM
Add LLM-as-judge
Calibrate judge using human labels and Cohen's kappa
Add more adversarial tasks
Add cost-aware agent improvements
Add prompt version tracking
Add model comparison dashboard
Add deployment evaluation
```

---

## Note

This repository currently uses mock LLMs so the full evaluation system can run without API costs.

The main focus is the reliability harness, not the intelligence of the mock agent.