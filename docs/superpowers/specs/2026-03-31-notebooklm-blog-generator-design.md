# NotebookLM Blog Generator — Design Spec

**Date:** 2026-03-31
**Status:** Approved

---

## Overview

Add a `blog` command to `mvp_notebooklm.py` that queries a fixed NotebookLM notebook with a blog-format prompt, parses the response, and publishes the result as a Notion page.

---

## User Flow

```
python mvp_notebooklm.py blog "양자컴퓨팅의 미래"
# 또는 인자 없이 실행 시 주제 입력 프롬프트
python mvp_notebooklm.py blog
```

1. 사용자가 주제(topic)를 입력
2. 블로그 형식 프롬프트를 구성해 NotebookLM에 쿼리
3. 응답을 파싱해 제목/태그/본문 추출
4. 제목으로 slug 생성
5. Notion API로 페이지 생성

---

## NotebookLM Prompt Template

```
다음 주제로 블로그 포스트를 작성해줘.
반드시 아래 형식을 따라줘:

# 제목

태그: tag1, tag2, tag3

## 소제목1
내용...

## 소제목2
내용...

주제: {topic}
```

---

## Response Parsing Rules

| 패턴 | 처리 |
|------|------|
| `# 텍스트` | 페이지 제목 (Title property) |
| `태그: a, b, c` | Tags multi_select |
| `## 텍스트` | Notion heading_2 블록 |
| 나머지 줄 | Notion paragraph 블록 (빈 줄 무시) |

**Slug 생성:** 제목을 영문 소문자로 변환, 공백/특수문자 → 하이픈
예: `"양자컴퓨팅의 미래"` → 파싱된 영문 제목 기준으로 생성

---

## Notion Page Structure

### Properties

| 속성명 | 타입 | 값 |
|--------|------|-----|
| Name | title | 파싱된 제목 |
| 태그 | multi_select | 파싱된 태그 리스트 |
| 공개여부 | checkbox | `false` (MVP 기본값) |
| 작성일자 | date | 실행 당일 날짜 |

### Content Blocks (순서)

1. **Code block** (language: `yaml`)
   ```yaml
   cleanUrl: /posts/<slug>
   ```
2. **Heading 2** + **Paragraph** 블록 반복 (파싱된 본문)

---

## Environment Variables

```
NOTION_API_KEY=secret_xxx        # Notion Integration 토큰
NOTION_DATABASE_ID=xxx           # 블로그 포스트 저장 DB ID
```

기존 변수:
```
NOTEBOOKLM_COOKIES               # 인증 (기존)
NOTEBOOKLM_QUERY_TIMEOUT         # 타임아웃 (기존)
```

---

## Implementation Scope

- `mvp_notebooklm.py`에 다음 추가:
  - `generate_blog(topic)` 함수
  - `post_to_notion(title, tags, blocks)` 함수
  - `make_slug(title)` 헬퍼
  - `main()` 파서에 `blog` 커맨드 추가
- 외부 라이브러리: `requests` (Notion REST API 직접 호출, 별도 SDK 없음)
- NotebookLM 고정 notebook ID: `b545cc09-cc49-4dd7-bd87-170c44c53ef6`

---

## Out of Scope (MVP)

- 공개여부 CLI 인자 지원
- 기존 페이지 업데이트
- 이미지/파일 첨부
- 태그 자동 번역
