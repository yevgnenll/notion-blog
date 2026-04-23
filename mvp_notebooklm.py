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
NOTION_INTEGRATION_KEY - Notion Integration token (required for Notion integration)
NOTION_DATABASE_ID - Blog posts database ID (required for Notion integration)
"""

import os
import sys
import json
import argparse
import re
import time
import requests
from pathlib import Path
from datetime import date
from typing import Optional

# Import the MCP client utilities
from notebooklm_tools.mcp.tools._utils import get_client
from notebooklm_tools.services import notebooks, chat
from agent.fetch_references import fetch_references, print_references


NOTEBOOK_ID = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID", "")


def make_slug(title: str) -> str:
    """Convert title to URL-safe slug. Falls back to Ollama for non-ASCII titles."""
    from utils.ollama import translate_title_to_slug

    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")

    if not slug:
        try:
            slug = translate_title_to_slug(title)
        except Exception:
            pass

    return slug or date.today().isoformat()


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
    in_code_block = False
    code_lines: list = []
    after_blank = False  # 빈 줄 이후 여부 (리스트 컨텍스트 초기화용)

    for line in text.splitlines():
        stripped = line.strip()

        # 코드 블록 내부: ``` 닫힘 줄까지 내용 수집
        if in_code_block:
            if stripped.startswith("```"):
                blocks.append(("code", "\n".join(code_lines)))
                in_code_block = False
                code_lines = []
            else:
                code_lines.append(line)
            continue

        # 코드 블록 시작
        if stripped.startswith("```"):
            in_code_block = True
            code_lines = []
            continue

        if not stripped:
            after_blank = True  # 빈 줄 → 리스트 컨텍스트 초기화
            continue
        # 빈 줄 없이 이어지는 줄이 리스트 항목의 continuation인지 확인
        if (
            not after_blank
            and blocks
            and blocks[-1][0] in ("numbered_list_item", "bulleted_list_item")
            and not re.match(r'^[#*\-`]', stripped)
            and not re.match(r'^\d+\.\s+', stripped)
            and not re.match(r'^(태그|tags)\s*:', stripped, re.IGNORECASE)
        ):
            last_type, last_content = blocks[-1]
            blocks[-1] = (last_type, last_content + " " + stripped)
            continue

        after_blank = False  # 일반 줄 처리 시 리셋

        if stripped.startswith("# ") and title is None:
            title = stripped[2:].strip()
        elif stripped.startswith("# "):
            blocks.append(("paragraph", stripped[2:].strip()))
        elif re.match(r'^(태그|tags)\s*:', stripped, re.IGNORECASE):
            raw = re.split(r':', stripped, 1)[1]
            tags = [t.strip() for t in raw.split(",") if t.strip()]
        elif stripped.startswith("### "):
            blocks.append(("heading_3", stripped[4:].strip()))
        elif stripped.startswith("## "):
            blocks.append(("heading_2", stripped[3:].strip()))
        elif re.match(r'^\*\s+', stripped) or re.match(r'^-\s+', stripped):
            content = re.sub(r'^[*-]\s+', '', stripped)
            blocks.append(("bulleted_list_item", content))
        elif re.match(r'^\d+\.\s+', stripped):
            content = re.sub(r'^\d+\.\s+', '', stripped)
            blocks.append(("numbered_list_item", content))
        else:
            blocks.append(("paragraph", stripped))

    if title is None:
        raise ValueError("No title found in NotebookLM response (expected '# title' line)")

    return {"title": title, "tags": tags, "blocks": blocks}


def parse_inline_markdown(text: str) -> list:
    """
    Convert markdown inline syntax to Notion rich_text segments.

    Handles: **bold**, *italic*, `code`, $latex$
    Returns a list of Notion rich_text objects.
    """
    pattern = re.compile(
        r'\*\*(.+?)\*\*'  # bold
        r'|\*(.+?)\*'      # italic
        r'|`(.+?)`'        # inline code
        r'|\$(.+?)\$'      # latex equation
    )

    segments = []
    last_end = 0

    for match in pattern.finditer(text):
        if match.start() > last_end:
            segments.append({"type": "text", "text": {"content": text[last_end:match.start()]}})

        bold, italic, code, latex = match.groups()
        if bold:
            segments.append({"type": "text", "text": {"content": bold}, "annotations": {"bold": True}})
        elif italic:
            segments.append({"type": "text", "text": {"content": italic}, "annotations": {"italic": True}})
        elif code:
            segments.append({"type": "text", "text": {"content": code}, "annotations": {"code": True}})
        elif latex:
            segments.append({"type": "equation", "equation": {"expression": latex}})

        last_end = match.end()

    if last_end < len(text):
        segments.append({"type": "text", "text": {"content": text[last_end:]}})

    return segments or [{"type": "text", "text": {"content": text}}]


def post_to_notion(title: str, tags: list, blocks: list, slug: str, cover_url: str = "") -> dict:
    """
    Create a Notion page via REST API.

    Args:
        title: Page title
        tags: List of tag strings
        blocks: List of (type, content) tuples — ("heading_2"|"paragraph", text)
        slug: URL slug for cleanUrl code block
        cover_url: External image URL for page cover and first image block

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
    children = []
    if cover_url:
        children.append({
            "object": "block",
            "type": "image",
            "image": {"type": "external", "external": {"url": cover_url}},
        })
    children += [
        {
            "object": "block",
            "type": "code",
            "code": {
                "language": "yaml",
                "rich_text": [{"type": "text", "text": {"content": f"cleanUrl: /posts/{slug}"}}],
            },
        },
        {
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {},
        },
    ]
    for block_type, content in blocks:
        rich_text = parse_inline_markdown(content)
        if block_type == "heading_2":
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": rich_text},
            })
        elif block_type == "heading_3":
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": rich_text},
            })
        elif block_type == "code":
            children.append({
                "object": "block",
                "type": "code",
                "code": {
                    "language": "plain text",
                    "rich_text": [{"type": "text", "text": {"content": content}}],
                },
            })
        elif block_type == "bulleted_list_item":
            children.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich_text},
            })
        elif block_type == "numbered_list_item":
            children.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": rich_text},
            })
        else:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text},
            })

    payload = {
        "parent": {"type": "database_id", "database_id": database_id},
        **({"cover": {"type": "external", "external": {"url": cover_url}}} if cover_url else {}),
        "properties": {
            "제목": {
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

    CHUNK_SIZE = 100

    # 첫 요청: 페이지 생성 (최대 100개 블록)
    payload["children"] = children[:CHUNK_SIZE]
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=payload,
    )
    if not resp.ok:
        raise ValueError(f"Notion API error {resp.status_code}: {resp.text}")
    page = resp.json()

    # 나머지 블록을 100개씩 append
    remaining = children[CHUNK_SIZE:]
    while remaining:
        chunk, remaining = remaining[:CHUNK_SIZE], remaining[CHUNK_SIZE:]
        append_resp = requests.patch(
            f"https://api.notion.com/v1/blocks/{page['id']}/children",
            headers=headers,
            json={"children": chunk},
        )
        if not append_resp.ok:
            raise ValueError(f"Notion API error (append) {append_resp.status_code}: {append_resp.text}")

    return page


_SEO_GUIDE_PATH = Path(__file__).parent / "docs" / "seo-strategy.md"


def _load_seo_guide() -> str:
    """Load the SEO strategy guide if available."""
    try:
        return _SEO_GUIDE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


BLOG_PROMPT_TEMPLATE = """\
다음 주제로 블로그 포스트를 작성해줘.
길이는 3000자 이상으로 아래 SEO 전략 가이드를 반드시 준수해줘.

--- SEO 전략 가이드 시작 ---
{seo_guide}
--- SEO 전략 가이드 끝 ---

그리고 반드시 아래 형식을 따라줘:

# 제목

태그: tag1, tag2, tag3

## 소제목1
내용...

## 소제목2
내용...

주제: {topic}"""

BLOG_PROMPT_TEMPLATE_EN = """\
IMPORTANT: You MUST write the ENTIRE response in ENGLISH only. Do not use Korean anywhere.

Write a blog post on the following topic.
The post must be at least 2000 words and strictly follow the SEO strategy guide below.

--- SEO STRATEGY GUIDE START ---
{seo_guide}
--- SEO STRATEGY GUIDE END ---

Follow this exact format (all content in English):

# Title

태그: tag1, tag2, tag3

## Section 1
Content...

## Section 2
Content...

Topic: {topic}"""


def build_reference_blocks(references: list, citations: dict, source_title_map: dict, lang: str = "ko") -> list:
    """
    Build Notion blocks for the references section.

    Args:
        references: List of {source_id, citation_number, cited_text?} dicts
        citations: Dict mapping citation_number -> source_id
        source_title_map: Dict mapping source_id -> source title

    Returns:
        List of (type, content) tuples to append to blocks
    """
    if not citations:
        return []

    heading = "References" if lang == "en" else "참고문헌"
    ref_blocks = [("heading_2", heading)]
    for ref in references:
        num = ref["citation_number"]
        source_id = ref["source_id"]
        raw_title = source_title_map.get(source_id, source_id)
        source_title = os.path.splitext(raw_title)[0]
        cited_text = ref.get("cited_text", "")
        if cited_text:
            # Truncate long cited text to keep blocks readable
            excerpt = cited_text[:300] + ("…" if len(cited_text) > 300 else "")
            ref_blocks.append(("paragraph", f"[{num}] {source_title} — {excerpt}"))
        else:
            ref_blocks.append(("paragraph", f"[{num}] {source_title}"))
    return ref_blocks


_TRANSIENT_CODES = ("502", "503", "504")
_RETRY_BASE_DELAY = 5  # seconds


def _with_retry(fn, max_attempts: int = 5):
    """
    Exponential backoff retry for transient HTTP errors (502/503/504).
    Delays: 5s, 10s, 20s, 40s between attempts.
    """
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            is_transient = any(code in str(e) for code in _TRANSIENT_CODES)
            if not is_transient or attempt == max_attempts - 1:
                raise
            delay = _RETRY_BASE_DELAY * (2 ** attempt)
            print(f"[retry] {attempt + 1}/{max_attempts} 실패 ({str(e)[:80]}) — {delay}s 후 재시도")
            time.sleep(delay)


def _fetch_blog_text(topic: str, lang: str) -> dict:
    """
    NotebookLM에 블로그 텍스트를 요청하고 파싱. Notion 게시는 하지 않음.

    Returns:
        dict with title, tags, blocks, citations, references
    """
    template = BLOG_PROMPT_TEMPLATE_EN if lang == "en" else BLOG_PROMPT_TEMPLATE
    prompt = template.replace("{seo_guide}", _load_seo_guide()).replace("{topic}", topic)

    client = get_client()
    result = _with_retry(lambda: chat.query(
        client,
        notebook_id=NOTEBOOK_ID,
        query_text=prompt,
        conversation_id=None,
    ))
    parsed = parse_blog_response(result["answer"])
    return {
        "title": parsed["title"],
        "tags": parsed["tags"],
        "blocks": parsed["blocks"],
        "citations": result.get("citations", {}),
        "references": result.get("references", []),
    }


def _publish_blog(
    fetched: dict,
    lang: str,
    slug: str,
    fallback_citations: Optional[dict] = None,
    fallback_references: Optional[list] = None,
    cover_url: str = "",
) -> dict:
    """
    파싱된 블로그 데이터를 Notion에 게시.

    Returns:
        dict with title, slug, tags, notion_url, notion_id, citations, references
    """
    citations = fetched["citations"]
    references = fetched["references"]

    if not citations and fallback_citations:
        citations = fallback_citations
        references = fallback_references or []
        print(f"[debug] using fallback citations: {len(citations)}")

    title = fetched["title"]
    tags = fetched["tags"]
    blocks = list(fetched["blocks"])

    print(f"[debug] citations count: {len(citations)}, references count: {len(references)}")
    if citations:
        source_title_map = {}
        try:
            client = get_client()
            nb_detail = notebooks.get_notebook(client, NOTEBOOK_ID)
            for src in nb_detail.get("sources", []):
                source_title_map[src["id"]] = src["title"]
        except Exception as e:
            print(f"[debug] get_notebook failed: {e}")
        blocks += build_reference_blocks(references, citations, source_title_map, lang=lang)
    else:
        print("[debug] citations empty — reference section skipped")

    page = post_to_notion(title=title, tags=tags, blocks=blocks, slug=slug, cover_url=cover_url)

    return {
        "title": title,
        "slug": slug,
        "tags": tags,
        "notion_url": page.get("url", ""),
        "notion_id": page.get("id", ""),
        "citations": citations,
        "references": references,
    }


def generate_blog(
    topic: str,
    lang: str = "ko",
    fallback_citations: Optional[dict] = None,
    fallback_references: Optional[list] = None,
    slug_override: str = "",
    cover_url: str = "",
) -> dict:
    """
    NotebookLM에서 블로그를 생성하고 Notion에 게시.

    Args:
        topic: Blog post topic
        lang: Language code — "ko" (Korean) or "en" (English)
        fallback_citations: Use these citations if the query returns none
        fallback_references: Use these references if the query returns none
        slug_override: Use this slug instead of deriving one from the title
        cover_url: External image URL for page cover and image block

    Returns:
        dict with title, slug, tags, notion_url, notion_id, citations, references
    """
    fetched = _fetch_blog_text(topic, lang)
    slug = slug_override or make_slug(fetched["title"]) or date.today().isoformat()
    return _publish_blog(
        fetched,
        lang=lang,
        slug=slug,
        fallback_citations=fallback_citations,
        fallback_references=fallback_references,
        cover_url=cover_url,
    )


def generate_blog_bilingual(topic: str) -> dict:
    """
    인포그래픽·한글·영어 블로그를 병렬로 생성한 뒤 각각 Notion에 게시.

    Args:
        topic: Blog post topic (used for both languages)

    Returns:
        dict with ko/en results
    """
    from concurrent.futures import ThreadPoolExecutor
    from utils.infographic import create_and_wait

    topic_ascii = re.sub(r"[^a-z0-9\s-]", "", topic.lower().strip())
    topic_ascii = re.sub(r"[\s-]+", "-", topic_ascii).strip("-")

    print("  [병렬] 인포그래픽 + 한글/영어 블로그 텍스트 동시 생성 중...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        infographic_future = executor.submit(create_and_wait, NOTEBOOK_ID, topic)
        ko_future = executor.submit(_fetch_blog_text, topic, "ko")
        en_future = executor.submit(_fetch_blog_text, topic, "en")

        ko_fetched = ko_future.result()
        print("  [1/3] 한글 블로그 텍스트 완료")
        en_fetched = en_future.result()
        print("  [2/3] 영어 블로그 텍스트 완료")
        cover_url = infographic_future.result() or ""
        if cover_url:
            print("  [3/3] 인포그래픽 완료!")
        else:
            print("  [3/3] 인포그래픽 실패 — 이미지 없이 진행")

    ko_slug = topic_ascii or make_slug(ko_fetched["title"]) or date.today().isoformat()
    ko_result = _publish_blog(ko_fetched, lang="ko", slug=ko_slug, cover_url=cover_url)

    en_result = _publish_blog(
        en_fetched,
        lang="en",
        slug=make_slug(en_fetched["title"]) or date.today().isoformat(),
        fallback_citations=ko_result.get("citations"),
        fallback_references=ko_result.get("references"),
        cover_url=cover_url,
    )

    return {"ko": ko_result, "en": en_result}


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

            # Print references if available
            if result.get("citations"):
                print("\nReferences:")
                refs = []
                source_title_map = {}
                try:
                    nb_detail = notebooks.get_notebook(client, notebook_id)
                    for src in nb_detail.get("sources", []):
                        source_title_map[src["id"]] = os.path.splitext(src["title"])[0]
                except Exception:
                    pass
                for ref in result.get("references", []):
                    refs.append({
                        "citation_number": ref["citation_number"],
                        "source_title": source_title_map.get(ref["source_id"], ref["source_id"]),
                        "cited_text": ref.get("cited_text", ""),
                    })
                print_references(refs)

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
  blog [topic]      Generate a blog post (optionally with topic)

Examples:
  python mvp_notebooklm.py list
  python mvp_notebooklm.py create "My Research"
  python mvp_notebooklm.py query
  python mvp_notebooklm.py query abc123def456 "What is this about?"
  python mvp_notebooklm.py add abc123def456 https://example.com
  python mvp_notebooklm.py blog "양자컴퓨팅의 미래"
  python mvp_notebooklm.py blog

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
        choices=["list", "create", "query", "add", "blog", "bilingual", "help"],
        default="help",
        help="Command to run: list, create, query, add, blog, bilingual, help"
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
    elif args.command == "blog":
        topic = args.args[0] if args.args else input("블로그 주제를 입력하세요: ").strip()
        if not topic:
            print("주제가 필요합니다.")
            sys.exit(1)
        print_header(f"블로그 생성: {topic}")
        try:
            result = generate_blog(topic)
            print(f"\n✓ 블로그 포스트가 Notion에 게시되었습니다!")
            print(f"  제목:  {result['title']}")
            print(f"  슬러그: {result['slug']}")
            print(f"  Tags:  {', '.join(result['tags'])}")
            print(f"  URL:  {result['notion_url']}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.command == "bilingual":
        topic = args.args[0] if args.args else input("블로그 주제를 입력하세요: ").strip()
        if not topic:
            print("주제가 필요합니다.")
            sys.exit(1)
        print_header(f"한글/영어 블로그 생성: {topic}")
        try:
            result = generate_blog_bilingual(topic)
            ko, en = result["ko"], result["en"]
            print(f"\n✓ 두 버전 모두 Notion에 게시되었습니다!")
            print(f"\n  [한글]")
            print(f"  제목:  {ko['title']}")
            print(f"  슬러그: {ko['slug']}")
            print(f"  URL:  {ko['notion_url']}")
            print(f"\n  [English]")
            print(f"  Title: {en['title']}")
            print(f"  Slug:  {en['slug']}")
            print(f"  URL:  {en['notion_url']}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
