"""
Section 2: Upload router streaming in-memory extraction and LLM parsing over SSE.
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import StreamingResponse

from app.section1_foundation_and_providers.providers.base import LLMProviderError
from app.section1_foundation_and_providers.providers.registry import get_provider
from app.section1_foundation_and_providers.schemas.sse import SSEEvent, SSEEventType
from app.section1_foundation_and_providers.security.security import register_secret, redact_text
from app.section2_parsing_and_upload.services.parsing import (
    ParsingError,
    extract_resume_text,
    parse_resume_with_llm,
)

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)


@router.post("")
async def upload_resume(
    file: UploadFile = File(...),
    provider: str = Form("gemini"),
    model: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    x_llm_key: Optional[str] = Header(None, alias="X-LLM-Key"),
):
    """
    Uploads PDF or DOCX file (up to 5 MB), extracts text in RAM,
    parses into structured profile via BYOK LLM, and streams progress over SSE.
    """
    effective_key = x_llm_key or api_key
    if effective_key:
        register_secret(effective_key)

    # Read file content entirely into memory
    file_bytes = await file.read()

    async def sse_event_stream() -> AsyncGenerator[str, None]:
        try:
            # 1. Validation & Reading Stage
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "reading",
                    "percent": 15,
                    "message": f"Validating {file.filename or 'resume'} in memory...",
                },
            ).to_sse_format()
            await asyncio.sleep(0.05)

            # 2. Text Extraction Stage
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "extracting",
                    "percent": 40,
                    "message": "Extracting text from document...",
                },
            ).to_sse_format()

            resume_text = await extract_resume_text(file_bytes)

            # 3. LLM Analysis Stage
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "analyzing",
                    "percent": 70,
                    "message": f"Analyzing profile with {provider}...",
                },
            ).to_sse_format()

            llm = get_provider(
                provider_id=provider,
                api_key=effective_key,
                model=model,
                custom_url=base_url,
            )
            parsed_profile = await parse_resume_with_llm(llm, resume_text)

            # 4. Complete & Emit Result
            yield SSEEvent(
                event=SSEEventType.PROGRESS,
                data={
                    "stage": "complete",
                    "percent": 100,
                    "message": "Profile parsed successfully.",
                },
            ).to_sse_format()

            yield SSEEvent(
                event=SSEEventType.RESULT,
                data=parsed_profile.model_dump(),
            ).to_sse_format()

        except ParsingError as e:
            logger.warning("Upload parsing error: %s", e.message)
            yield SSEEvent(
                event=SSEEventType.ERROR,
                data={"message": redact_text(e.message), "code": "PARSING_ERROR"},
            ).to_sse_format()
        except LLMProviderError as e:
            logger.warning("Upload LLM error: %s", e.message)
            yield SSEEvent(
                event=SSEEventType.ERROR,
                data={"message": redact_text(e.message), "code": "LLM_ERROR"},
            ).to_sse_format()
        except Exception as e:
            logger.error("Unexpected error during resume processing: %s", str(e))
            yield SSEEvent(
                event=SSEEventType.ERROR,
                data={
                    "message": "An error occurred while processing your resume. Please try again.",
                    "code": "INTERNAL_ERROR",
                },
            ).to_sse_format()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
