# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI MVP for interacting with NotebookLM via the `notebooklm-mcp-cli` package. The single script `mvp_notebooklm.py` wraps the `notebooklm_tools` library with a user-friendly CLI.

## Setup & Running

```bash
pip install notebooklm-mcp-cli
nlm login   # authenticate via Chrome, or set NOTEBOOKLM_COOKIES env var
python mvp_notebooklm.py <command>
```

## Commands

```bash
python mvp_notebooklm.py list
python mvp_notebooklm.py create "My Research"
python mvp_notebooklm.py query
python mvp_notebooklm.py add <notebook_id> <url>
```

## Environment Variables

- `NOTEBOOKLM_COOKIES` — Chrome cookies for auth (alternative to `nlm login`)
- `NOTEBOOKLM_QUERY_TIMEOUT` — Query timeout in seconds (default: 120)

## Architecture

The script delegates all API work to the `notebooklm_tools` package:

- `notebooklm_tools.mcp.tools._utils.get_client()` — constructs the MCP client (called fresh per operation)
- `notebooklm_tools.services.notebooks` — list/create notebooks
- `notebooklm_tools.services.chat` — query a notebook with conversation tracking
- `notebooklm_tools.services.sources` — add URL sources to a notebook

The `query_notebook()` function maintains a `conversation_id` across turns (up to 10 messages) for follow-up questions. Note: the notebook ID is currently hardcoded at line 100 — replace with a dynamic value when extending beyond MVP.
