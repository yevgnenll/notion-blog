# Blog Generator

NotebookLM과 Notion을 연동한 블로그 생성 에이전트

## 구조

```
blog-generator/
├── .env                          # Environment variables
├── requirements.txt
├── main.py                       # Entry point
├── server/                       # FastAPI 서버
│   ├── __init__.py
│   ├── main.py
│   └── routes/
│       ├── __init__.py
│       ├── blog.py
│       └── telegram.py
├── agent/                        # 에이전트 로직
│   ├── __init__.py
│   ├── notebooklm.py
│   └── brain.py
├── integrations/                 # 외부 API 연동
│   ├── __init__.py
│   ├── notion.py
│   └── telegram.py
└── utils/
    ├── __init__.py
    └── config.py
```

## 데모 실행

```bash
# requirements 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 확인)
# NOTION_INTEGRATION_KEY, NOTION_DB_URL, TELEGRAM_BOT_KEY, OPENAI_API_KEY, NOTEBOOKLM_NOTEBOOK_ID

# 서버 실행
python main.py
```

## API Endpoints

- `GET /` - Root
- `GET /health` - Health Check
- `POST /api/blog/query` - NotebookLM에 질문
- `POST /api/blog/improve` - 답변 개선
- `POST /api/blog/generate` - 블로그 생성
- `POST /api/telegram/webhook` - Telegram Webhook

## Google Search Console (SEO) 설정

블로그 포스팅 후 구글에 사이트맵을 수동으로 제출하기 위해 다음 설정이 필요합니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 및 **Google Search Console API** 활성화
2. **OAuth 클라이언트 ID (데스크톱 앱)**를 생성하고 JSON 파일을 다운로드하여 프로젝트 루트에 `client_secrets.json`으로 저장
3. **OAuth 동의 화면** 설정에서 **Test users**에 본인의 구글 계정 이메일 추가

### 사이트맵 수동 제출 실행 (CLI)

포스팅 내용을 직접 검수한 뒤, 구글 색인 생성을 요청하려면 다음 명령어를 실행하세요:

```bash
# 최초 실행 시 브라우저 로그인 창이 열립니다.
python cli_seo.py
```

- **대상 사이트**: `https://blog.yevgnenll.me`
- **사이트맵 주소**: `https://blog.yevgnenll.me/sitemap.xml`
- 인증 정보는 `token.json`에 저장되어 이후 실행 시에는 로그인 없이 동작합니다.

## Notion DB 설정

`.env` 파일에 다음을 설정하세요:

```
NOTION_INTEGRATION_KEY=your_integration_key
NOTION_DB_URL=https://www.notion.so/workspace/page_id
NOTION_DATABASE_ID=page_id_without_hyphens
```

## NotebookLM 설정

`.env` 파일에 다음을 설정하세요:

```
NOTEBOOKLM_NOTEBOOK_ID=your_notebook_id
```

NotebookLM API 키는 브라우저에서 https://notebooklm.google.com/settings/api 에서 발급 가능

## Telegram Bot 설정

`.env` 파일에 다음을 설정하세요:

```
TELEGRAM_BOT_KEY=your_bot_token
```

BotFather를 통해 봇을 생성하고 토큰을 받아주세요.
# notion-blog
