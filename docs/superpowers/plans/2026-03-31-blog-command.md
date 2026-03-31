# Blog Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `blog` command to `mvp_notebooklm.py` that queries NotebookLM with a blog-format prompt, parses the response, and publishes it to Notion.

**Architecture:** All new logic lives in `mvp_notebooklm.py` as three helpers (`make_slug`, `generate_blog`, `post_to_notion`) wired into the existing `argparse` main. Notion integration uses direct `requests` calls (no SDK) against the REST API. NotebookLM queries reuse the existing `notebooklm_tools` MCP client pattern already in the file.

**Tech Stack:** Python 3, `notebooklm_tools` (MCP), `requests` (Notion REST API), `python-dotenv` (env vars already in use)

---

## File Map

| File | Action | What changes |
|------|--------|--------------|
| `mvp_notebooklm.py` | Modify | Add `make_slug`, `generate_blog`, `post_to_notion`, update `main()` |
| `requirements.txt` | Check/Modify | Ensure `requests` and `python-dotenv` are listed |
| `tests/test_blog_command.py` | Create | Unit tests for all new helpers |

---

## Task 1: Add `make_slug` helper + test

**Files:**
- Create: `tests/test_blog_command.py`
- Modify: `mvp_notebooklm.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_blog_command.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mvp_notebooklm import make_slug

def test_make_slug_english():
    assert make_slug("The Future of Quantum Computing") == "the-future-of-quantum-computing"

def test_make_slug_strips_special_chars():
    assert make_slug("Hello, World! (2024)") == "hello-world-2024"

def test_make_slug_collapses_hyphens():
    assert make_slug("A  B---C") == "a-b-c"

def test_make_slug_strips_leading_trailing():
    assert make_slug("  hello world  ") == "hello-world"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/yevgnenll/dev/blog-generator
python -m pytest tests/test_blog_command.py::test_make_slug_english -v
```
Expected: `ImportError` or `AttributeError: module 'mvp_notebooklm' has no attribute 'make_slug'`

- [ ] **Step 3: Implement `make_slug` in `mvp_notebooklm.py`**

Add after the imports block (after `from notebooklm_tools...` lines, before `print_header`):

```python
import re
from datetime import date


NOTEBOOK_ID = "b545cc09-cc49-4dd7-bd87-170c44c53ef6"


def make_slug(title: str) -> str:
    """Convert title to URL-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_blog_command.py -k "slug" -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mvp_notebooklm.py tests/test_blog_command.py tests/__init__.py
git commit -m "feat: add make_slug helper and tests"
```

---

## Task 2: Add response parser + tests

**Files:**
- Modify: `tests/test_blog_command.py`
- Modify: `mvp_notebooklm.py`

The parser must extract title (`# ...`), tags (`태그: a, b`), heading_2 blocks (`## ...`), and paragraphs from the NotebookLM response.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_blog_command.py`:

```python
from mvp_notebooklm import parse_blog_response

SAMPLE_RESPONSE = """# 양자컴퓨팅의 미래

태그: 기술, 과학, 컴퓨팅

## 들어가며
양자컴퓨팅은 고전적인 컴퓨팅의 한계를 넘어선다.

## 핵심 원리
중첩과 얽힘을 활용해 병렬 연산을 수행한다.
"""

def test_parse_title():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["title"] == "양자컴퓨팅의 미래"

def test_parse_tags():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["tags"] == ["기술", "과학", "컴퓨팅"]

def test_parse_blocks_count():
    result = parse_blog_response(SAMPLE_RESPONSE)
    # Two heading_2 + two paragraph blocks
    assert len(result["blocks"]) == 4

def test_parse_blocks_heading():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["blocks"][0] == ("heading_2", "들어가며")

def test_parse_blocks_paragraph():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["blocks"][1] == ("paragraph", "양자컴퓨팅은 고전적인 컴퓨팅의 한계를 넘어선다.")

def test_parse_no_title_raises():
    try:
        parse_blog_response("태그: x\n\n## 섹션\n내용")
        assert False, "Expected ValueError"
    except ValueError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_blog_command.py -k "parse" -v
```
Expected: `ImportError` — `parse_blog_response` not yet defined

- [ ] **Step 3: Implement `parse_blog_response` in `mvp_notebooklm.py`**

Add after `make_slug`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_blog_command.py -k "parse" -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add mvp_notebooklm.py tests/test_blog_command.py
git commit -m "feat: add parse_blog_response with title/tags/blocks extraction"
```

---

## Task 3: Add `post_to_notion` + test (mocked)

**Files:**
- Modify: `tests/test_blog_command.py`
- Modify: `mvp_notebooklm.py`

Uses `requests` directly. Notion properties from spec: `Name` (title), `태그` (multi_select), `공개여부` (checkbox=false), `작성일자` (date=today).

Content blocks: first a `code` block (yaml, `cleanUrl: /posts/<slug>`), then heading_2 and paragraph blocks from parsed response.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_blog_command.py`:

```python
from unittest.mock import patch, MagicMock
from mvp_notebooklm import post_to_notion

def test_post_to_notion_sends_correct_payload():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": "page-123", "url": "https://notion.so/page-123"}

    blocks = [("heading_2", "들어가며"), ("paragraph", "내용입니다.")]

    with patch("mvp_notebooklm.requests.post", return_value=mock_resp) as mock_post, \
         patch.dict("os.environ", {"NOTION_INTEGRATION_KEY": "secret_test", "NOTION_DATABASE_ID": "db-id-abc"}):
        result = post_to_notion(
            title="양자컴퓨팅의 미래",
            tags=["기술", "과학"],
            blocks=blocks,
            slug="quantum-computing-future"
        )

    assert result["id"] == "page-123"

    call_args = mock_post.call_args
    payload = call_args.kwargs["json"] if "json" in call_args.kwargs else call_args[1]["json"]

    # Check properties
    props = payload["properties"]
    assert props["Name"]["title"][0]["text"]["content"] == "양자컴퓨팅의 미래"
    assert props["태그"]["multi_select"] == [{"name": "기술"}, {"name": "과학"}]
    assert props["공개여부"]["checkbox"] is False

    # Check first content block is yaml code block
    children = payload["children"]
    assert children[0]["type"] == "code"
    assert children[0]["code"]["language"] == "yaml"
    assert "cleanUrl: /posts/quantum-computing-future" in children[0]["code"]["rich_text"][0]["text"]["content"]

    # Check heading_2 block
    assert children[1]["type"] == "heading_2"
    assert children[2]["type"] == "paragraph"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_blog_command.py::test_post_to_notion_sends_correct_payload -v
```
Expected: `ImportError` — `post_to_notion` not yet defined

- [ ] **Step 3: Implement `post_to_notion` in `mvp_notebooklm.py`**

Add `import requests` at the top of the imports section. Then add after `parse_blog_response`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_blog_command.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add mvp_notebooklm.py tests/test_blog_command.py
git commit -m "feat: add post_to_notion with direct REST API calls"
```

---

## Task 4: Add `generate_blog` function

**Files:**
- Modify: `mvp_notebooklm.py`
- Modify: `tests/test_blog_command.py`

`generate_blog(topic)` sends the blog-format prompt to NotebookLM, parses the response, generates slug, posts to Notion.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_blog_command.py`:

```python
from unittest.mock import patch, MagicMock
from mvp_notebooklm import generate_blog

MOCK_NLM_RESPONSE = """# 양자컴퓨팅의 미래

태그: 기술, 과학, 미래

## 서론
양자컴퓨팅은 매우 혁신적인 기술이다.

## 결론
앞으로 더 발전할 것이다.
"""

def test_generate_blog_calls_notebooklm_and_notion():
    mock_chat_result = {"answer": MOCK_NLM_RESPONSE, "conversation_id": "conv-1"}

    with patch("mvp_notebooklm.chat.query", return_value=mock_chat_result) as mock_query, \
         patch("mvp_notebooklm.get_client") as mock_get_client, \
         patch("mvp_notebooklm.post_to_notion", return_value={"id": "pg-1", "url": "https://notion.so/pg-1"}) as mock_notion:
        result = generate_blog("양자컴퓨팅의 미래")

    mock_query.assert_called_once()
    call_kwargs = mock_query.call_args
    # Prompt must contain the topic
    query_text = call_kwargs.kwargs.get("query_text") or call_kwargs[1].get("query_text") or call_kwargs[0][2]
    assert "양자컴퓨팅의 미래" in query_text

    mock_notion.assert_called_once()
    notion_kwargs = mock_notion.call_args.kwargs if mock_notion.call_args.kwargs else mock_notion.call_args[1]
    assert notion_kwargs["title"] == "양자컴퓨팅의 미래"
    assert "기술" in notion_kwargs["tags"]

    assert result["notion_url"] == "https://notion.so/pg-1"
    assert result["title"] == "양자컴퓨팅의 미래"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_blog_command.py::test_generate_blog_calls_notebooklm_and_notion -v
```
Expected: `ImportError` — `generate_blog` not yet defined

- [ ] **Step 3: Implement `generate_blog` in `mvp_notebooklm.py`**

Add after `post_to_notion`:

```python
BLOG_PROMPT_TEMPLATE = """\
다음 주제로 블로그 포스트를 작성해줘.
반드시 아래 형식을 따라줘:

# 제목

태그: tag1, tag2, tag3

## 소제목1
내용...

## 소제목2
내용...

주제: {topic}"""


def generate_blog(topic: str) -> dict:
    """
    Query NotebookLM with a blog-format prompt, parse the response,
    and publish to Notion.

    Args:
        topic: Blog post topic

    Returns:
        dict with title, slug, tags, notion_url
    """
    prompt = BLOG_PROMPT_TEMPLATE.format(topic=topic)

    client = get_client()
    result = chat.query(
        client,
        notebook_id=NOTEBOOK_ID,
        query_text=prompt,
        conversation_id=None,
    )
    response_text = result["answer"]

    parsed = parse_blog_response(response_text)
    title = parsed["title"]
    tags = parsed["tags"]
    blocks = parsed["blocks"]
    slug = make_slug(title)

    page = post_to_notion(title=title, tags=tags, blocks=blocks, slug=slug)

    return {
        "title": title,
        "slug": slug,
        "tags": tags,
        "notion_url": page.get("url", ""),
        "notion_id": page.get("id", ""),
    }
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_blog_command.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add mvp_notebooklm.py tests/test_blog_command.py
git commit -m "feat: add generate_blog orchestrator function"
```

---

## Task 5: Wire `blog` command into `main()`

**Files:**
- Modify: `mvp_notebooklm.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_blog_command.py`:

```python
import subprocess

def test_blog_command_help_shows_in_help():
    result = subprocess.run(
        ["python", "mvp_notebooklm.py", "--help"],
        cwd="/Users/yevgnenll/dev/blog-generator",
        capture_output=True, text=True
    )
    assert "blog" in result.stdout or "blog" in result.stderr
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_blog_command.py::test_blog_command_help_shows_in_help -v
```
Expected: FAIL — `blog` not in help output

- [ ] **Step 3: Update `main()` in `mvp_notebooklm.py`**

In the `parser.add_argument("command", ...)` call, add `"blog"` to the choices list:

```python
    parser.add_argument(
        "command",
        nargs="?",
        choices=["list", "create", "query", "add", "blog", "help"],
        default="help",
        help="Command to run: list, create, query, add, blog, help"
    )
```

Add the `blog` handler in the `if/elif` chain at the bottom of `main()`, after the `add` block:

```python
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
            print(f"  태그:  {', '.join(result['tags'])}")
            print(f"  URL:  {result['notion_url']}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
```

Also update `show_help()` epilog to document the new command:

```python
  python mvp_notebooklm.py blog "양자컴퓨팅의 미래"
  python mvp_notebooklm.py blog
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_blog_command.py -v
```
Expected: all tests PASS

- [ ] **Step 5: Verify CLI manually (no real API calls)**

```bash
python mvp_notebooklm.py --help
```
Expected: `blog` appears in choices

- [ ] **Step 6: Commit**

```bash
git add mvp_notebooklm.py
git commit -m "feat: wire blog command into CLI main()"
```

---

## Task 6: Verify `requirements.txt` and env vars

**Files:**
- Modify: `requirements.txt` (if needed)

- [ ] **Step 1: Read current requirements.txt**

```bash
cat requirements.txt
```

- [ ] **Step 2: Ensure `requests` is listed**

If `requests` is not in `requirements.txt`, add it. If it already is, skip.

Example final requirements (add only what's missing):
```
requests
python-dotenv
```

- [ ] **Step 3: Verify env var documentation in script docstring**

Top of `mvp_notebooklm.py` docstring must mention:
```
NOTION_INTEGRATION_KEY=secret_xxx   # Notion Integration token
NOTION_DATABASE_ID=xxx              # Blog posts database ID
```

Update the docstring's `Environment Variables` section to include these two.

- [ ] **Step 4: Commit if changed**

```bash
git add requirements.txt mvp_notebooklm.py
git commit -m "chore: ensure requests in requirements, document env vars"
```

---

## Self-Review

### Spec Coverage Check

| Spec requirement | Covered by |
|------------------|-----------|
| `blog` CLI command | Task 5 |
| Topic from arg or stdin prompt | Task 5 |
| Blog-format prompt template | Task 4 (`BLOG_PROMPT_TEMPLATE`) |
| `# title` → page title | Task 2 (`parse_blog_response`) |
| `태그: a, b` → multi_select | Task 2 + Task 3 |
| `## text` → heading_2 block | Task 2 + Task 3 |
| Other lines → paragraph (empty lines ignored) | Task 2 |
| `make_slug` from title | Task 1 |
| `Name` property (title) | Task 3 |
| `태그` property (multi_select) | Task 3 |
| `공개여부` checkbox = false | Task 3 |
| `작성일자` date = today | Task 3 |
| Code block yaml `cleanUrl: /posts/<slug>` | Task 3 |
| Heading_2 + paragraph blocks in order | Task 3 |
| Fixed notebook ID `b545cc09-...` | Task 4 (`NOTEBOOK_ID` constant) |
| `requests` only, no Notion SDK | Task 3 |
| `NOTION_INTEGRATION_KEY` env var | Task 3 |
| `NOTION_DATABASE_ID` env var | Task 3 |

All spec requirements covered. ✓
