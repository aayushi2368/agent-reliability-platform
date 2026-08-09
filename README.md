# Agent Reliability Platform

This is an evaluation harness for a simple CSV data-analysis agent.

## What it does

- Runs an agent on CSV analysis tasks
- Records every tool call and LLM step
- Checks final answers programmatically
- Checks whether required tools were used
- Produces JSON and Markdown evaluation reports

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt