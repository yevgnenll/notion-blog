"""Ollama 로컬 LLM 클라이언트"""
import os
import re
import requests


def translate_title_to_slug(
    title: str,
    host: str | None = None,
    model: str | None = None,
    timeout: int = 30,
) -> str:
    """
    Ollama를 사용해 제목을 영문 URL slug로 변환.

    Args:
        title: 번역할 제목
        host: Ollama 서버 주소 (기본값: OLLAMA_HOST 환경변수 또는 http://localhost:11434)
        model: 사용할 모델 (기본값: OLLAMA_MODEL 환경변수 또는 qwen3-coder:30b)
        timeout: 요청 타임아웃(초)

    Returns:
        영문 slug 문자열. 실패 시 빈 문자열 반환.
    """
    host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = model or os.environ.get("OLLAMA_MODEL", "gemma4-openclaw:latest")

    resp = requests.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": (
                f'Convert a Korean blog title into a short, SEO-friendly English URL slug.\n'
                f'\n'
                f'Rules:\n'
                f'- Translate the MEANING into natural English (do NOT romanize Korean sounds)\n'
                f'- Keep only the 3-5 most important keywords\n'
                f'- Remove stop words (a, the, to, and, for, of, in)\n'
                f'- Lowercase, hyphens between words, no special characters\n'
                f'- Reply with ONLY the slug, nothing else\n'
                f'\n'
                f'Examples:\n'
                f'Korean: "자바 동시성 프로그램 테스트 완벽 가이드" → java-concurrency-testing-guide\n'
                f'Korean: "데이터베이스 정규화 완벽 가이드 함수적 종속성부터 3NF까지" → database-normalization-3nf-guide\n'
                f'\n'
                f'Korean: "{title}"\n'
                f'Slug:'
            ),
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()

    raw = resp.json().get("response", "").strip().lower()
    # <think>...</think> 태그 제거 (reasoning 모델 대응)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    slug = re.sub(r"[^a-z0-9-]", "-", raw)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
