"""지수 백오프 재시도 유틸리티"""
import time

_TRANSIENT_CODES = ("502", "503", "504")
_BASE_DELAY = 5  # seconds


def with_retry(fn, max_attempts: int = 5):
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
            delay = _BASE_DELAY * (2 ** attempt)
            print(f"[retry] {attempt + 1}/{max_attempts} 실패 ({str(e)[:80]}) — {delay}s 후 재시도")
            time.sleep(delay)
