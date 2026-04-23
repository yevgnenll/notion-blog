"""NotebookLM infographic 생성 및 URL 획득"""
import time

from utils.retry import with_retry

_POLL_INTERVAL = 5   # seconds between polls
_MAX_POLLS = 36      # up to 3 minutes total


def create_and_wait(notebook_id: str, topic: str) -> str | None:
    """
    Infographic 생성 요청 후 완료될 때까지 폴링.

    Returns:
        infographic_url string, or None if failed/timed out
    """
    from notebooklm_tools.mcp.tools._utils import get_client
    from notebooklm_tools.services import studio

    client = get_client()
    try:
        result = with_retry(lambda: studio.create_artifact(
            client,
            notebook_id,
            "infographic",
            focus_prompt=topic,
            language="en",
            orientation="landscape",
            detail_level="standard",
        ))
    except Exception as e:
        print(f"[infographic] 생성 요청 실패: {e}")
        return None

    artifact_id = result.get("artifact_id")
    if not artifact_id:
        print("[infographic] artifact_id 없음")
        return None

    print(f"[infographic] 생성 중... (artifact_id={artifact_id[:8]}...)")

    for i in range(_MAX_POLLS):
        time.sleep(_POLL_INTERVAL)
        try:
            artifacts = with_retry(lambda: client.poll_studio_status(notebook_id))
            for a in artifacts:
                if a.get("artifact_id") != artifact_id:
                    continue
                status = a.get("status")
                if status == "completed":
                    url = a.get("infographic_url")
                    if url:
                        print("[infographic] 완료! URL 획득")
                        return url
                    print("[infographic] 완료되었으나 URL 없음")
                    return None
                if status == "failed":
                    print("[infographic] 생성 실패")
                    return None
        except Exception as e:
            print(f"[infographic] 폴링 오류 (스킵): {e}")

        elapsed = (i + 1) * _POLL_INTERVAL
        print(f"[infographic] 대기 중... ({elapsed}s / {_MAX_POLLS * _POLL_INTERVAL}s)")

    print("[infographic] 타임아웃")
    return None
