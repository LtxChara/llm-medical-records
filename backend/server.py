from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from urllib.parse import quote
from collections import defaultdict
import uvicorn
import logging
import logging.handlers
import asyncio
import time
from typing import Dict, Any

from function import (
    getLLMReturn, generate_word_document, store, FIELDS_ORDER,
    _sanitize_user_input,
)

# --- Logging Configuration ---
# 使用 RotatingFileHandler 防止日志文件无限增长，单文件上限5MB，保留3个备份
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'server.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Rate Limiting ---
# 基于内存的简单速率限制：同一session_id在5秒内只能请求一次
_request_timestamps: Dict[str, float] = defaultdict(float)
MIN_REQUEST_INTERVAL = 5.0  # 秒


def _check_request_interval(session_id: str):
    """检查同一session的请求间隔，防止恶意高频调用。"""
    now = time.time()
    last = _request_timestamps.get(session_id, 0)
    if now - last < MIN_REQUEST_INTERVAL:
        wait = int(MIN_REQUEST_INTERVAL - (now - last)) + 1
        logger.warning(f"Rate limit hit for session {session_id}. Need to wait {wait}s.")
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请等待 {wait} 秒后重试。"
        )
    _request_timestamps[session_id] = now


# --- Lifespan Events ---
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """使用 lifespan 事件管理器替代已弃用的 on_event，管理后台任务生命周期。"""
    store.start_cleanup()
    logger.info("FastAPI application startup complete.")
    yield
    store.stop_cleanup()
    logger.info("FastAPI application shutdown complete.")


# --- FastAPI Application Setup ---
app = FastAPI(
    title="Medical Recommendation API",
    version="1.1",
    description="API for generating medical recommendations with user supplementation.",
    openapi_tags=[
        {"name": "recommendation", "description": "Core recommendation workflow"},
        {"name": "utility", "description": "Helper endpoints"}
    ],
    lifespan=lifespan,
)

# --- CORS Middleware ---
# 生产环境中应将origins限制为确切的前端域名
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    expose_headers=["Content-Disposition"],
)


# --- API Endpoints ---

@app.get("/", tags=["utility"], summary="API Root/Health Check")
async def root():
    """Provides basic API information and status."""
    logger.info("Root endpoint accessed.")
    return JSONResponse(
        content={
            "message": "Medical Recommendation API is running.",
            "version": app.version,
            "docs_url": "/docs"
        },
        status_code=200
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Handles browser favicon requests."""
    return Response(status_code=204)


# --- Recommendation Workflow Endpoints ---

class ProcessRequest(BaseModel):
    session_id: str
    text: str


class SupplementRequest(BaseModel):
    session_id: str
    field: str
    text: str


class GenerateDocRequestInput(BaseModel):
    patient_info: Dict[str, Any]
    visit_info: Dict[str, Any]
    medical_content: Dict[str, Any]


class GenerateDocRequest(BaseModel):
    input: GenerateDocRequestInput


# 文本长度上限常量
MAX_INPUT_LENGTH = 4000


@app.post("/process",
          tags=["recommendation"],
          summary="Start or continue recommendation process",
          response_description="JSON containing processing status and result/prompt")
async def process_text_endpoint(
    payload: ProcessRequest = Body(...)
) -> Dict[str, Any]:
    """
    Handles the initial user input or subsequent turns in the recommendation process.
    Triggers the LLM analysis and returns the result or a prompt for more info.
    """
    session_id = payload.session_id
    text = payload.text

    if not session_id or not session_id.strip():
        logger.warning("Empty session_id received")
        raise HTTPException(status_code=400, detail="Session ID cannot be empty.")
    if not text or not text.strip():
        logger.warning(f"Empty text received for session {session_id}")
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    # 输入长度限制与清理
    if len(text) > MAX_INPUT_LENGTH:
        logger.warning(f"Input text too long for session {session_id}: {len(text)} chars")
        raise HTTPException(status_code=400, detail=f"输入文本过长，请限制在 {MAX_INPUT_LENGTH} 字符以内。")
    text = _sanitize_user_input(text)

    # 速率限制
    _check_request_interval(session_id)

    logger.info(f"Processing request for session_id: {session_id}")
    try:
        history_manager, lock = await store.get_or_create(session_id)
        async with lock:
            # 初始文本注入所有字段的历史记录，确保每个字段都有原始患者描述
            result = await getLLMReturn(
                session_id=session_id,
                initial_text=text,
                history_manager=history_manager,
            )

        status = result.get("status")
        if status == "success":
            logger.info(f"Successfully processed session {session_id}.")
        elif status == "incomplete":
            logger.info(f"Processing incomplete for session {session_id}, field: {result.get('field')}")
        elif status == "error":
            logger.error(f"Error processing session {session_id}: {result.get('message')}")
            raise HTTPException(status_code=500, detail=result.get("message", "Internal server error during processing."))
        else:
            logger.error(f"Unknown status '{status}' returned from getLLMReturn for session {session_id}")
            raise HTTPException(status_code=500, detail="Internal server error: Unknown processing status.")

        return result

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in /process endpoint for session {session_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/supplement",
          tags=["recommendation"],
          summary="Provide supplementary information",
          response_description="JSON containing processing status after supplementation")
async def supplement_text_endpoint(
    payload: SupplementRequest = Body(...)
) -> Dict[str, Any]:
    """
    Receives supplementary information from the user for a specific field
    and re-triggers the LLM processing with the updated context.
    """
    session_id = payload.session_id
    field = payload.field
    supplement_text = payload.text

    # --- Input Validation ---
    if not session_id or not session_id.strip():
        logger.warning("Supplement request validation failed: Empty session_id")
        raise HTTPException(status_code=400, detail="Session ID cannot be empty.")
    if not field or not field.strip():
        logger.warning(f"Supplement request validation failed: Empty field (Session: {session_id})")
        raise HTTPException(status_code=400, detail="Field cannot be empty.")
    if not supplement_text or not supplement_text.strip():
        logger.warning(f"Supplement request validation failed: Empty text (Session: {session_id}, Field: {field})")
        raise HTTPException(status_code=400, detail="Supplementary text cannot be empty.")
    if len(supplement_text) > MAX_INPUT_LENGTH:
        logger.warning(f"Supplement text too long for session {session_id}, field {field}: {len(supplement_text)} chars")
        raise HTTPException(status_code=400, detail=f"补充文本过长，请限制在 {MAX_INPUT_LENGTH} 字符以内。")

    if field not in FIELDS_ORDER:
        logger.warning(f"Invalid field '{field}' provided for supplementation (Session: {session_id})")
        raise HTTPException(status_code=400, detail=f"Invalid field '{field}'. Valid fields are: {', '.join(FIELDS_ORDER)}")

    if not store.exists(session_id):
        logger.error(f"Session not found for supplementation: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found. Please start a new process.")

    # 输入清理
    supplement_text = _sanitize_user_input(supplement_text)

    # 速率限制
    _check_request_interval(session_id)

    logger.info(f"Processing supplement request for session_id: {session_id}, field: {field}")
    try:
        history_manager, lock = await store.get_or_create(session_id)
        async with lock:
            history_manager.add_supplement(field, supplement_text)

            # 仅重新处理目标字段及其后续未完成字段，避免重复调用已成功的字段
            result = await getLLMReturn(
                session_id=session_id,
                history_manager=history_manager,
                target_field=field,
            )

        status = result.get("status")
        if status == "success":
            logger.info(f"Successfully processed supplement for session {session_id}.")
        elif status == "incomplete":
            logger.info(f"Processing still incomplete after supplement for session {session_id}, field: {result.get('field')}")
        elif status == "error":
            logger.error(f"Error processing supplement for session {session_id}: {result.get('message')}")
            raise HTTPException(status_code=500, detail=result.get("message", "Internal server error during supplementation."))
        else:
            logger.error(f"Unknown status '{status}' returned from getLLMReturn after supplement for session {session_id}")
            raise HTTPException(status_code=500, detail="Internal server error: Unknown processing status after supplement.")

        return result

    except ValueError as ve:
        logger.warning(f"Value error during supplement processing for session {session_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in /supplement endpoint for session {session_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- Document Generation Endpoint ---

@app.post("/generate_doc",
          tags=["utility"],
          summary="Generate Word document from recommendation results",
          response_description="A Word document (.docx) file stream")
async def generate_doc_endpoint(
    payload: GenerateDocRequest = Body(...)
) -> StreamingResponse:
    """
    Generates a patient report in Word (.docx) format based on the provided
    patient information, visit details, and medical content (recommendation results).
    """
    patient_name = "未知患者"
    try:
        data_input = payload.input
        patient_info = data_input.patient_info
        patient_name = patient_info.get('name', '未知患者')
        logger.info(f"Generating Word document for patient: {patient_name}")

        # 文档生成是CPU密集型同步操作，使用 asyncio.to_thread 防止阻塞事件循环
        docx_buffer = await asyncio.to_thread(generate_word_document, data_input.model_dump())

        safe_patient_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_patient_name}_康复医疗报告_{timestamp}.docx"
        filename_encoded = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
        }

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    except ValueError as ve:
        logger.error(f"Data validation failed during document generation for {patient_name}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to generate Word document for patient: {patient_name}")
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {e}")


# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        log_level="info"
    )
