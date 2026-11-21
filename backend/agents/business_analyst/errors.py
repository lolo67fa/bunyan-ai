"""Turn any Business Analyst failure into a safe, user-facing error.

The API shows ``message`` (Arabic, no technical detail) and keeps ``code`` stable so
the frontend and tests can rely on it. ``detail`` is for server logs only: the
exception type, the API request id when there is one, and a short reason. No API
keys or prompt text ever reach any of the three.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

from .analyst import AnalysisError
from .config import ConfigError
from .direct_llm import LLMRefusal


@dataclass(frozen=True)
class Failure:
    code: str
    message: str        # Arabic, safe to show to the user
    retryable: bool     # True when sending the same request again may work
    detail: str = ""    # English, for logs only

    def as_error(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


_MESSAGES = {
    "ba_not_configured": ("خدمة التحليل بالذكاء الاصطناعي غير مهيّأة على الخادم. أبلغ مسؤول المنصة.", False),
    "invalid_input": ("تعذّر قراءة الفكرة أو الإجابات. راجعها وأرسلها مرة أخرى.", False),
    "ba_invalid_output": ("لم يُنتج المحلّل متطلبات صالحة هذه المرة. أعد المحاولة، أو اكتب الفكرة بتفصيل أوضح.", True),
    "ba_refused": ("رفضت خدمة الذكاء الاصطناعي تحليل هذا الطلب. أعد صياغة الفكرة وجرّب مرة أخرى.", False),
    "ba_output_truncated": ("كان رد المحلّل أطول من الحد المسموح فانقطع. بسّط الفكرة أو قلّل التفاصيل وأعد المحاولة.", True),
    "llm_auth_failed": ("تعذّر الاتصال بخدمة الذكاء الاصطناعي بسبب مشكلة في صلاحية مفتاح الخدمة. أبلغ مسؤول المنصة.", False),
    "llm_model_unavailable": ("نموذج الذكاء الاصطناعي المحدد غير متاح على الخادم. أبلغ مسؤول المنصة.", False),
    "llm_bad_request": ("رفضت خدمة الذكاء الاصطناعي الطلب بسبب خطأ في إعداداته. أبلغ مسؤول المنصة.", False),
    "llm_rate_limited": ("خدمة الذكاء الاصطناعي مزدحمة الآن. انتظر دقيقة ثم أعد المحاولة.", True),
    "llm_timeout": ("استغرقت خدمة الذكاء الاصطناعي وقتاً أطول من المسموح. أعد المحاولة بعد قليل.", True),
    "llm_unavailable": ("خدمة الذكاء الاصطناعي غير متاحة مؤقتاً. أعد المحاولة بعد قليل.", True),
    "ba_failed": ("تعذّر على المحلّل إكمال التحليل بسبب خطأ غير متوقع. أعد المحاولة.", True),
}


def _failure(code: str, detail: str) -> Failure:
    message, retryable = _MESSAGES[code]
    return Failure(code=code, message=message, retryable=retryable, detail=detail)


def _request_id(exc: BaseException) -> Optional[str]:
    return getattr(exc, "request_id", None) or getattr(getattr(exc, "response", None), "headers", {}).get("request-id")


def _sdk_failure(exc: BaseException) -> Optional[Failure]:
    """Classify Anthropic SDK errors, most specific first. None when the SDK is absent or it is not an SDK error."""
    try:
        import anthropic
    except ImportError:
        return None
    rid = _request_id(exc) if isinstance(exc, anthropic.APIStatusError) else None
    detail = f"{type(exc).__name__}" + (f" (request id {rid})" if rid else "")
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return _failure("llm_auth_failed", detail)
    if isinstance(exc, anthropic.NotFoundError):
        return _failure("llm_model_unavailable", detail)
    if isinstance(exc, anthropic.RateLimitError):
        return _failure("llm_rate_limited", detail)
    if isinstance(exc, anthropic.BadRequestError):
        return _failure("llm_bad_request", detail)
    if isinstance(exc, anthropic.APIStatusError):  # 5xx, 529 overloaded and any other status
        return _failure("llm_unavailable", f"{detail} status {exc.status_code}")
    if isinstance(exc, anthropic.APITimeoutError):  # a subclass of APIConnectionError: check it first
        return _failure("llm_timeout", detail)
    if isinstance(exc, anthropic.APIConnectionError):
        return _failure("llm_unavailable", detail)
    return None


def describe_failure(exc: BaseException) -> Failure:
    """Map an exception raised while analysing an idea to a safe Failure."""
    if isinstance(exc, ConfigError):
        return _failure("ba_not_configured", str(exc))
    if isinstance(exc, ValidationError):
        return _failure("invalid_input", f"{exc.error_count()} input validation error(s)")
    if isinstance(exc, AnalysisError):
        cause = exc.__cause__
        if isinstance(cause, LLMRefusal):
            code = "ba_output_truncated" if "max_tokens" in str(cause) else "ba_refused"
            return _failure(code, str(cause)[:300])
        return _failure("ba_invalid_output", "; ".join(exc.errors)[:500])
    if isinstance(exc, LLMRefusal):
        code = "ba_output_truncated" if "max_tokens" in str(exc) else "ba_refused"
        return _failure(code, str(exc)[:300])
    sdk = _sdk_failure(exc)
    if sdk is not None:
        return sdk
    return _failure("ba_failed", type(exc).__name__)
