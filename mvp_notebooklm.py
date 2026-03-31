#!/usr/bin/env python3
"""
NotebookLM MCP Connection MVP
=============================

This script demonstrates how to connect to NotebookLM via MCP and ask questions.
It provides a simple CLI interface for:
1. Listing notebooks
2. Creating a new notebook
3. Querying a notebook with AI

Setup:
------
1. Install: pip install notebooklm-mcp-cli
2. Authenticate: nlm login (or set NOTEBOOKLM_COOKIES environment variable)
3. Run: python mvp_notebooklm.py

Environment Variables:
---------------------
NOTEBOOKLM_COOKIES - Chrome cookies for authentication (optional)
NOTEBOOKLM_QUERY_TIMEOUT - Query timeout in seconds (default: 120)
"""

import os
import sys
import json
import argparse
import re
import requests
from datetime import date
from typing import Optional

# Import the MCP client utilities
from notebooklm_tools.mcp.tools._utils import get_client
from notebooklm_tools.services import notebooks, chat


NOTEBOOK_ID = "b545cc09-cc49-4dd7-bd87-170c44c53ef6"


def make_slug(title: str) -> str:
    """Convert title to URL-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


def parse_blog_response(text: str) -> dict:
    """
    Parse NotebookLM blog-format response.

    Returns:
        {
            "title": str,
            "tags": list[str],
            "blocks": list[tuple[str, str]]  # (type, content)
        }
    Raises:
        ValueError if no title found.
    """
    title = None
    tags = []
    blocks = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and title is None:
            title = stripped[2:].strip()
        elif stripped.startswith("# "):
            blocks.append(("paragraph", stripped[2:].strip()))
        elif stripped.lower().startswith("태그:"):
            raw = stripped.split(":", 1)[1]
            tags = [t.strip() for t in raw.split(",") if t.strip()]
        elif stripped.startswith("## "):
            blocks.append(("heading_2", stripped[3:].strip()))
        else:
            blocks.append(("paragraph", stripped))

    if title is None:
        raise ValueError("No title found in NotebookLM response (expected '# title' line)")

    return {"title": title, "tags": tags, "blocks": blocks}


def post_to_notion(title: str, tags: list, blocks: list, slug: str) -> dict:
    """
    Create a Notion page via REST API.

    Args:
        title: Page title
        tags: List of tag strings
        blocks: List of (type, content) tuples — ("heading_2"|"paragraph", text)
        slug: URL slug for cleanUrl code block

    Returns:
        Created page dict (id, url, ...)
    """
    api_key = os.environ.get("NOTION_INTEGRATION_KEY") or os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not api_key:
        raise ValueError("NOTION_INTEGRATION_KEY environment variable is required")
    if not database_id:
        raise ValueError("NOTION_DATABASE_ID environment variable is required")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # Build content blocks
    children = [
        {
            "object": "block",
            "type": "code",
            "code": {
                "language": "yaml",
                "rich_text": [{"type": "text", "text": {"content": f"cleanUrl: /posts/{slug}"}}],
            },
        }
    ]
    for block_type, content in blocks:
        if block_type == "heading_2":
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            })
        else:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": content}}]},
            })

    payload = {
        "parent": {"type": "database_id", "database_id": database_id},
        "properties": {
            "Name": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
            "태그": {
                "multi_select": [{"name": t} for t in tags]
            },
            "공개여부": {
                "checkbox": False
            },
            "작성일자": {
                "date": {"start": date.today().isoformat()}
            },
        },
        "children": children,
    }

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def list_notebooks():
    """List all available notebooks."""
    print_header("Your NotebookLM Notebooks")
    
    try:
        client = get_client()
        result = notebooks.list_notebooks(client)
        
        if not result["notebooks"]:
            print("No notebooks found. Create one using: python mvp_notebooklm.py create")
            return
        
        print(f"\nTotal notebooks: {result['count']}")
        print(f"  Owned: {result['owned_count']}")
        print(f"  Shared: {result['shared_count']}")
        print()
        
        for nb in result["notebooks"]:
            print(f"  ID: {nb['id']}")
            print(f"    Title: {nb['title']}")
            print(f"    Sources: {nb['source_count']}")
            print(f"    URL: {nb['url']}")
            print()
            
    except Exception as e:
        print(f"Error listing notebooks: {e}")
        print("\nMake sure you're authenticated with 'nlm login'")
        sys.exit(1)


def create_notebook(title: Optional[str] = None):
    """Create a new notebook."""
    if not title:
        title = input("Enter notebook title: ").strip()
        if not title:
            title = "Untitled Notebook"
    
    print_header(f"Creating Notebook: {title}")
    
    try:
        client = get_client()
        result = notebooks.create_notebook(client, title)
        
        print(f"\n✓ Notebook created successfully!")
        print(f"  ID: {result['notebook_id']}")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        
        return result["notebook_id"]
        
    except Exception as e:
        print(f"Error creating notebook: {e}")
        sys.exit(1)


def query_notebook(notebook_id: Optional[str] = None):
    """Ask a question to a notebook."""
    # Fixed notebook ID - always use this notebook
    notebook_id = NOTEBOOK_ID
    
    # Optional: Verify the notebook exists
    try:
        client = get_client()
        result = notebooks.list_notebooks(client)
        notebook_exists = any(nb["id"] == notebook_id for nb in result.get("notebooks", []))
        if not notebook_exists:
            print(f"Warning: Notebook ID {notebook_id} not found in your notebooks.")
            print("Make sure you have access to this notebook.")
    except Exception as e:
        print(f"Warning: Could not verify notebook: {e}")
    
    print_header("Query Notebook")
    print(f"Target Notebook ID: {notebook_id}")
    print("Type 'quit' or 'exit' to leave\n")
    
    conversation_id = None
    max_conversation_history = 10  # 대화 history 유지 제한
    
    while True:
        query = input("\nYour question: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        try:
            client = get_client()
            result = chat.query(
                client,
                notebook_id=notebook_id,
                query_text=query,
                conversation_id=conversation_id
            )
            
            print(f"\nAnswer:")
            print("-" * 60)
            print(result["answer"])
            print("-" * 60)
            
            # Update conversation_id for follow-up questions
            if result.get("conversation_id"):
                conversation_id = result["conversation_id"]
                
        except Exception as e:
            print(f"Error querying notebook: {e}")
            if "401" in str(e) or "403" in str(e):
                print("\nAuthentication error. Please run 'nlm login' to refresh your credentials.")


def add_source(notebook_id: Optional[str] = None):
    """Add a source (URL) to a notebook."""
    if not notebook_id:
        notebook_id = input("Enter notebook ID: ").strip()
        if not notebook_id:
            print("Notebook ID is required.")
            return
    
    url = input("Enter URL to add: ").strip()
    
    if not url:
        print("URL is required.")
        return
    
    print_header(f"Adding Source: {url}")
    
    try:
        from notebooklm_tools.services import sources
        
        client = get_client()
        result = sources.add_source(
            client,
            notebook_id=notebook_id,
            source_type="url",
            url=url
        )
        
        print(f"\n✓ Source added successfully!")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"Error adding source: {e}")


def show_help():
    """Show help message."""
    print("""
NotebookLM MCP Connection MVP
=============================

Usage: python mvp_notebooklm.py <command> [options]

Commands:
  list              List all your notebooks
  create [title]    Create a new notebook (optionally with title)
  query [id]        Ask questions to a notebook
  add <id> <url>    Add a URL source to a notebook
  
Examples:
  python mvp_notebooklm.py list
  python mvp_notebooklm.py create "My Research"
  python mvp_notebooklm.py query
  python mvp_notebooklm.py query abc123def456 "What is this about?"
  python mvp_notebooklm.py add abc123def456 https://example.com

Environment Variables:
  NOTEBOOKLM_COOKIES   Chrome cookies for authentication
  NOTEBOOKLM_QUERY_TIMEOUT  Query timeout in seconds (default: 120)

Authentication:
  Run 'nlm login' to authenticate with NotebookLM via Chrome,
  or set the NOTEBOOKLM_COOKIES environment variable.

More info: https://github.com/jacob-bd/notebooklm-mcp-cli
""")


def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM MCP Connection MVP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mvp_notebooklm.py list
  python mvp_notebooklm.py create "My Research"
  python mvp_notebooklm.py query
  python mvp_notebooklm.py add <notebook_id> <url>
"""
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "create", "query", "add", "help"],
        default="help",
        help="Command to run: list, create, query, add, help"
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Command arguments (title, notebook_id, etc.)"
    )
    
    args = parser.parse_args()
    
    if args.command == "help":
        show_help()
    elif args.command == "list":
        list_notebooks()
    elif args.command == "create":
        create_notebook(args.args[0] if args.args else None)
    elif args.command == "query":
        query_notebook(args.args[0] if args.args else None)
    elif args.command == "add":
        if len(args.args) >= 2:
            add_source(args.args[0], args.args[1])
        else:
            print("Usage: python mvp_notebooklm.py add <notebook_id> <url>")
            sys.exit(1)


if __name__ == "__main__":
    main()
