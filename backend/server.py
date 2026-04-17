from fastapi import FastAPI, HTTPException, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime
from urllib.parse import quote
import uvicorn
import logging
from typing import Dict, Any

from function import getLLMReturn, generate_word_document, store, FIELDS_ORDER

# --- Logging Configuration ---
# Ensure logging is configured early
logging.basicConfig(
    level=logging.INFO, # Use INFO for production, DEBUG for development
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log', encoding='utf-8'), # Ensure UTF-8 encoding
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Medical Recommendation API",
    version="1.0",
    description="API for generating medical recommendations with user supplementation.",
    # Add documentation tags if desired
    openapi_tags=[
        {"name": "recommendation", "description": "Core recommendation workflow"},
        {"name": "utility", "description": "Helper endpoints"}
    ]
)

# --- CORS Middleware ---
# Configure allowed origins specifically for production environments
# For development, ["*"] or specific local origins like "http://localhost:5173" are fine.
allowed_origins = [
    "http://localhost:5173", # Example frontend origin
    "http://127.0.0.1:5173", # Added localhost IP origin
    # Add other allowed origins (e.g., production frontend URL)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all standard methods
    allow_headers=["*"], # Allows all headers
    expose_headers=["Content-Disposition"], # Expose header for file downloads
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

# Define request body models for clarity and validation
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
     medical_content: Dict[str, Any] # This should match the output of 'getLLMReturn' success result

class GenerateDocRequest(BaseModel):
     input: GenerateDocRequestInput


@app.post("/process",
          tags=["recommendation"],
          summary="Start or continue recommendation process",
          response_description="JSON containing processing status and result/prompt")
async def process_text_endpoint(
    # Use Pydantic model for automatic validation
    payload: ProcessRequest = Body(...)
) -> Dict[str, Any]:
    """
    Handles the initial user input or subsequent turns in the recommendation process.
    Triggers the LLM analysis and returns the result or a prompt for more info.
    """
    session_id = payload.session_id
    text = payload.text

    if not text or not text.strip():
        logger.warning(f"Empty text received for session {session_id}")
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    if not session_id or not session_id.strip():
         logger.warning("Empty session_id received")
         raise HTTPException(status_code=400, detail="Session ID cannot be empty.")


    logger.info(f"Processing request for session_id: {session_id}")
    try:
        history_manager, lock = await store.get_or_create(session_id)
        async with lock:
            # Pass initial_text only for the first logical turn handled by /process
            # Subsequent calls might also use /process if the frontend design prefers it,
            # in which case initial_text should perhaps be the *latest* user utterance.
            # The current implementation adds initial_text only once per session effectively.
            result = await getLLMReturn(
                session_id=session_id,
                initial_text=text,
                history_manager=history_manager,
            )

        # Log based on status
        status = result.get("status")
        if status == "success":
            logger.info(f"Successfully processed session {session_id}.")
        elif status == "incomplete":
            logger.info(f"Processing incomplete for session {session_id}, field: {result.get('field')}")
        elif status == "error":
            logger.error(f"Error processing session {session_id}: {result.get('message')}")
            # Convert internal error status to HTTP error response
            raise HTTPException(status_code=500, detail=result.get("message", "Internal server error during processing."))
        else:
            logger.error(f"Unknown status '{status}' returned from getLLMReturn for session {session_id}")
            raise HTTPException(status_code=500, detail="Internal server error: Unknown processing status.")

        return result # Return success or incomplete status directly

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        logger.exception(f"Unexpected error in /process endpoint for session {session_id}") # Log traceback
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/supplement",
          tags=["recommendation"],
          summary="Provide supplementary information",
          response_description="JSON containing processing status after supplementation")
async def supplement_text_endpoint(
    # Use Pydantic model for automatic validation
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
         logger.warning(f"Supplement request validation failed: Empty session_id")
         raise HTTPException(status_code=400, detail="Session ID cannot be empty.")
    if not field or not field.strip():
         logger.warning(f"Supplement request validation failed: Empty field (Session: {session_id})")
         raise HTTPException(status_code=400, detail="Field cannot be empty.")
    if not supplement_text or not supplement_text.strip():
        logger.warning(f"Supplement request validation failed: Empty text (Session: {session_id}, Field: {field})")
        raise HTTPException(status_code=400, detail="Supplementary text cannot be empty.")


    if field not in FIELDS_ORDER: # Use FIELDS_ORDER from function.py as the source of truth
        logger.warning(f"Invalid field '{field}' provided for supplementation (Session: {session_id})")
        raise HTTPException(status_code=400, detail=f"Invalid field '{field}'. Valid fields are: {', '.join(FIELDS_ORDER)}")

    if not store.exists(session_id):
        logger.error(f"Session not found for supplementation: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found. Please start a new process.")

    logger.info(f"Processing supplement request for session_id: {session_id}, field: {field}")
    try:
        history_manager, lock = await store.get_or_create(session_id)
        async with lock:
            # Add the supplementary text to the history
            history_manager.add_supplement(field, supplement_text)

            # Re-run the entire recommendation process with updated history
            # Do not pass initial_text here, as the supplement is now in history
            result = await getLLMReturn(
                session_id=session_id,
                history_manager=history_manager,
            )

        # Log and handle status similar to /process
        status = result.get("status")
        if status == "success":
            logger.info(f"Successfully processed supplement for session {session_id}.")
        elif status == "incomplete":
            # This could happen if supplementing one field reveals need for another
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

@app.post("/generate_doc", # Simplified route name
          tags=["utility"],
          summary="Generate Word document from recommendation results",
          response_description="A Word document (.docx) file stream")
async def generate_doc_endpoint(
     # Use Pydantic model for the nested structure
     payload: GenerateDocRequest = Body(...)
) -> StreamingResponse:
    """
    Generates a patient report in Word (.docx) format based on the provided
    patient information, visit details, and medical content (recommendation results).
    """
    patient_name = "未知患者" # Default name
    try:
        # Pydantic model handles the presence of 'input' key and its structure
        data_input = payload.input

        # Extract data using model attributes for type safety
        patient_info = data_input.patient_info
        visit_info = data_input.visit_info # Added extraction
        medical_content = data_input.medical_content

        patient_name = patient_info.get('name', '未知患者') # Default name if missing
        logger.info(f"Generating Word document for patient: {patient_name}")

        # Call the generation function - pass the input dictionary directly
        docx_buffer = generate_word_document(data_input.model_dump()) # Pass dict representation

        # Prepare filename and headers for download
        # Sanitize patient name for filename
        safe_patient_name = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).rstrip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{safe_patient_name}_康复医疗报告_{timestamp}.docx"
        # Ensure filename is properly encoded for headers
        filename_encoded = quote(filename)
        headers = {
            # Use filename* for broader compatibility with non-ASCII characters
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
        }

        return StreamingResponse(
            docx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    # Catch Pydantic validation errors if using models
    # except ValidationError as e:
    #     logger.warning(f"Generate document request validation failed: {e.errors()}")
    #     raise HTTPException(status_code=422, detail=e.errors())
    except ValueError as ve: # Catch specific errors from generate_word_document
        logger.error(f"Data validation failed during document generation for {patient_name}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly if needed (e.g., validation failed before generation)
        raise http_exc
    except Exception as e:
        logger.exception(f"Failed to generate Word document for patient: {patient_name}") # Log traceback
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {e}")


# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Starting FastAPI server...")
    # Consider using environment variables for host and port configuration
    # For development, allow connections from any interface on the machine:
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=True, log_level="info")
    # For production, bind to a specific interface if needed
    # uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")