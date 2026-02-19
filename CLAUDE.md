# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SN-print** — Python 3.11 project. Virtual environment is in `.venv/` (excluded from version control).

## Environment

Activate the virtual environment before running any Python commands:

```bash
source .venv/Scripts/activate  # Windows (bash)
```

## Common Commands

As the project grows, add build, test, and lint commands here. For now:

```bash
python -m pytest          # run tests (once pytest is installed)
python -m ruff check .    # lint (once ruff is installed)
python -m ruff format .   # format
```
