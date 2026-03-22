"""FastAPI 서버 모듈"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routes import blog, telegram

app = FastAPI(
    title="Blog Generator API",
    description="NotebookLM과 Notion을 연동한 블로그 생성 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 포함
app.include_router(blog.router, prefix="/api/blog", tags=["blog"])
app.include_router(telegram.router, prefix="/api/telegram", tags=["telegram"])


@app.get("/")
async def root():
    return {"message": "Blog Generator API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
