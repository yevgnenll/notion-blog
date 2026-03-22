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
