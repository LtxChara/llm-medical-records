import asyncio
import logging
import json
from typing import Dict, Any, Tuple, Optional

from openai import OpenAI, RateLimitError, APIError, APIConnectionError
from med_prompt import system_prompt_templates, user_prompt_templates
from chat_memory import MedicalHistoryManager
from schemas import FIELD_SCHEMA_MAP
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from io import BytesIO

from config import settings

logger = logging.getLogger(__name__)

# Order of fields to process
FIELDS_ORDER = ["主诉", "现病史", "既往史", "过敏史", "诊断"]
# Maximum number of supplement rounds per field before forcing continuation
MAX_SUPPLEMENT_PER_FIELD = 3


class SessionStore:
    """Async-safe session store with per-session locks and TTL eviction."""

    def __init__(self, ttl_seconds: int):
        self._data: Dict[str, MedicalHistoryManager] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._last_access: Dict[str, float] = {}
        self.ttl_seconds = ttl_seconds

    def _now(self) -> float:
        return asyncio.get_event_loop().time()

    async def get_or_create(self, session_id: str) -> Tuple[MedicalHistoryManager, asyncio.Lock]:
        now = self._now()
        expired = [
            sid for sid, t in self._last_access.items()
            if now - t > self.ttl_seconds
        ]
        for sid in expired:
            self._data.pop(sid, None)
            self._locks.pop(sid, None)
            self._last_access.pop(sid, None)
            logger.info(f"Expired session removed: {sid}")

        if session_id not in self._data:
            self._data[session_id] = MedicalHistoryManager()
            self._locks[session_id] = asyncio.Lock()
        self._last_access[session_id] = now
        return self._data[session_id], self._locks[session_id]

    def exists(self, session_id: str) -> bool:
        return session_id in self._data


store = SessionStore(ttl_seconds=settings.session_ttl_seconds)

try:
    client = OpenAI(
        api_key=settings.siliconflow_api_key,
        base_url=settings.siliconflow_base_url,
        timeout=settings.llm_timeout,
    )
    logger.info(
        f"OpenAI client initialized for model: {settings.llm_model_name} "
        f"at {settings.siliconflow_base_url}"
    )
except Exception as e:
    logger.critical(f"Failed to initialize OpenAI client: {e}")
    client = None

# --- Core LLM Interaction Logic ---

async def call_llm(
    field: str,
    history: MedicalHistoryManager
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Calls the LLM for a specific field using conversation history.

    Args:
        field: The medical field to query (e.g., "主诉").
        history: The MedicalHistoryManager instance for the current session.

    Returns:
        A tuple: (parsed_json_response, error_message).
        If successful, parsed_json_response is the dict, error_message is None.
        If failed, parsed_json_response is None, error_message contains the error detail.
    """
    if not client:
        return None, "LLM client not initialized."
    if field not in history.histories:
         return None, f"History type '{field}' not found in history manager."

    schema_cls = FIELD_SCHEMA_MAP.get(field)
    user_prompt_template = user_prompt_templates.get(field)
    system_prompt = system_prompt_templates.get(field)

    if not schema_cls or not user_prompt_template or not system_prompt:
        return None, f"Prompt template or schema missing for field: {field}"

    user_input_history = history.get_user_all_input(history_type=field)
    if not user_input_history.strip():
        logger.warning(f"No user input history found for field '{field}'. Skipping LLM call.")
        return {field: ""}, None

    # Inject schema into system prompt for better compliance with JSON Mode
    schema_json = schema_cls.model_json_schema()
    enhanced_system_prompt = (
        f"{system_prompt}\n\n"
        f"你必须严格按照以下 JSON Schema 输出，不要添加任何其他说明文字：\n"
        f"{json.dumps(schema_json, ensure_ascii=False, indent=2)}"
    )

    messages = [
        {"role": "system", "content": enhanced_system_prompt},
        {"role": "user", "content": user_prompt_template + user_input_history + "'''"}
    ]

    logger.debug(f"Calling LLM for field '{field}' with messages: {messages}")

    max_retries = settings.llm_max_retries
    base_delay = 1  # Base delay in seconds for retries

    for attempt in range(max_retries + 1):
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=settings.llm_model_name,
                messages=messages,
                temperature=0.5,
                top_p=0.9,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            logger.debug(f"LLM raw response for '{field}': {content}")

            if not content:
                logger.warning(f"LLM returned empty content for field '{field}'.")
                return {field: ""}, None

            try:
                validated = schema_cls.model_validate_json(content)
                return validated.model_dump(), None
            except Exception as parse_e:
                logger.error(
                    f"Failed to parse/repair LLM response JSON for '{field}'. "
                    f"Error: {parse_e}. Raw content: '{content}'"
                )
                return None, f"Failed to parse LLM response: {parse_e}"

        except RateLimitError as rle:
            logger.warning(f"Rate limit hit calling LLM for '{field}'. Attempt {attempt + 1}/{max_retries + 1}. Error: {rle}")
            if attempt >= max_retries: return None, f"Rate limit exceeded after {max_retries + 1} attempts."
            await asyncio.sleep(base_delay * (2 ** attempt))
        except (APIError, APIConnectionError) as apie:
            logger.error(f"API error calling LLM for '{field}'. Attempt {attempt + 1}/{max_retries + 1}. Error: {apie}")
            if attempt >= max_retries: return None, f"API error after {max_retries + 1} attempts: {apie}"
            await asyncio.sleep(base_delay * (2 ** attempt))
        except Exception as e:
            logger.exception(f"Unexpected error calling LLM for '{field}'. Attempt {attempt + 1}/{max_retries + 1}. Error: {e}")
            if attempt >= max_retries: return None, f"Unexpected error after {max_retries + 1} attempts: {e}"
            await asyncio.sleep(base_delay)

    return None, f"LLM call failed for field '{field}' after {max_retries + 1} attempts."


async def getLLMReturn(
    session_id: str,
    initial_text: Optional[str] = None,
    history_manager: Optional[MedicalHistoryManager] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the process of calling the LLM for all required fields,
    handles the user supplementation workflow.

    Args:
        session_id: The unique identifier for the user session.
        initial_text: The initial user input (only provided on the first call via /process).
        history_manager: The MedicalHistoryManager for this session. If None, a new one
                         will be created from the global store (legacy behavior).

    Returns:
        A dictionary representing the API response:
        - {"status": "success", "result": {...}} if all fields complete.
        - {"status": "incomplete", "field": "...", "message": "..."} if supplementation needed.
        - {"status": "error", "message": "..."} if a critical error occurs.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        return {"status": "error", "message": "Session ID cannot be empty."}

    # Get or create history manager for the session
    if history_manager is None:
        history_manager, _ = await store.get_or_create(session_id)
        logger.info(f"Creating new MedicalHistoryManager for session_id: {session_id}")

    # If initial_text is provided (first call), add it to the relevant history
    # Determining the "relevant" history for initial text is tricky.
    # Option 1: Add to all fields? Noisy.
    # Option 2: Add only to the first field ("主诉")? Simple.
    # Option 3: Add a generic "initial_input" history type? More complex.
    # Let's go with Option 2 for simplicity.
    if initial_text and isinstance(initial_text, str) and initial_text.strip():
         try:
             # Assuming the first field in FIELDS_ORDER is the primary target for initial input
             first_field = FIELDS_ORDER[0]
             history_manager.add_message(first_field, "user", initial_text)
             logger.info(f"Added initial text to '{first_field}' history for session {session_id}.")
         except (ValueError, IndexError) as e:
              logger.error(f"Failed to add initial text for session {session_id}: {e}")
              return {"status": "error", "message": "Failed to process initial input."}


    collected_results: Dict[str, Any] = {}

    # Helper to handle a single field result and update history
    def _handle_field_result(field: str, llm_result: Optional[Dict[str, Any]], error_msg: Optional[str]):
        if error_msg:
            logger.error(f"Error processing field '{field}' for session {session_id}: {error_msg}")
            return {"status": "error", "message": f"Failed to process field '{field}': {error_msg}"}

        if llm_result is None:
            logger.error(f"LLM result was None but no error message for field '{field}' (session {session_id}).")
            return {"status": "error", "message": f"Internal error processing field '{field}'."}

        field_value = llm_result.get(field, "")
        needs_supplement = bool(llm_result.get("needs_supplement", False))
        supplement_question = llm_result.get("supplement_question") or field_value

        if needs_supplement:
            supplement_count = history_manager.get_supplement_count(field)
            if supplement_count >= MAX_SUPPLEMENT_PER_FIELD:
                logger.warning(
                    f"Max supplement reached for field '{field}' in session {session_id} "
                    f"(count={supplement_count}). Forcing continuation."
                )
                collected_results[field] = field_value
                try:
                    history_manager.add_message(field, "ai", supplement_question)
                except ValueError as e:
                    logger.error(f"Failed to add AI message to history for field '{field}' (session {session_id}): {e}")
                return None

            logger.info(f"Supplementation needed for field '{field}' in session {session_id}. Message: {supplement_question}")
            try:
                history_manager.add_message(field, "ai", supplement_question)
            except ValueError as e:
                logger.error(f"Failed to add AI supplement message to history for field '{field}' (session {session_id}): {e}")
            return {
                "status": "incomplete",
                "field": field,
                "message": supplement_question,
            }
        else:
            collected_results[field] = field_value
            logger.debug(f"Field '{field}' processed successfully for session {session_id}. Value: {field_value}")
            try:
                ai_response_content = json.dumps(field_value, ensure_ascii=False) if not isinstance(field_value, str) else field_value
                history_manager.add_message(field, "ai", ai_response_content)
            except ValueError as e:
                logger.error(f"Failed to add AI message to history for field '{field}' (session {session_id}): {e}")
        return None

    # --- Phase 1: Concurrent extraction of independent fields ---
    independent_fields = FIELDS_ORDER[:-1]  # 主诉, 现病史, 既往史, 过敏史
    logger.info(f"Phase 1: Concurrently processing fields {independent_fields} for session {session_id}...")

    # Build tasks
    tasks = [call_llm(field, history_manager) for field in independent_fields]
    independent_results = await asyncio.gather(*tasks, return_exceptions=True)

    for field, result in zip(independent_fields, independent_results):
        if isinstance(result, Exception):
            logger.exception(f"Unexpected exception during concurrent processing of field '{field}' for session {session_id}: {result}")
            return {"status": "error", "message": f"Unexpected error processing field '{field}': {result}"}

        llm_result, error_msg = result
        outcome = _handle_field_result(field, llm_result, error_msg)
        if outcome is not None:
            return outcome

    # --- Phase 2: Sequential diagnosis (depends on previous fields) ---
    diagnosis_field = FIELDS_ORDER[-1]  # 诊断
    logger.info(f"Phase 2: Processing field '{diagnosis_field}' for session {session_id}...")

    # Inject aggregated context from previous fields into diagnosis history
    diagnosis_user_input = history_manager.get_user_all_input(diagnosis_field).strip()
    if not diagnosis_user_input:
        context_lines = [f"【{k}】{v}" for k, v in collected_results.items() if k != diagnosis_field]
        if context_lines:
            aggregated_context = "\n".join(context_lines)
            context_message = (
                f"以下为患者已提取的医疗记录信息，请据此进行诊断：\n{aggregated_context}"
            )
            try:
                history_manager.add_message(diagnosis_field, "user", context_message)
                logger.info(f"Injected aggregated context into '{diagnosis_field}' for session {session_id}.")
            except ValueError as e:
                logger.error(f"Failed to inject diagnosis context for session {session_id}: {e}")

    llm_result, error_msg = await call_llm(diagnosis_field, history_manager)
    outcome = _handle_field_result(diagnosis_field, llm_result, error_msg)
    if outcome is not None:
        return outcome

    # --- Final Response ---
    logger.info(f"All fields processed successfully for session {session_id}.")
    return {
        "status": "success",
        "result": collected_results,
        "message": "处理成功",
    }


# --- Document Generation ---

def generate_word_document(params: Dict[str, Any]) -> BytesIO:
    """Generates a formatted Word document from structured patient data."""
    logger.info("Starting Word document generation.")
    try:
        # Validate input structure
        patient_info = params.get('patient_info', {})
        visit_info = params.get('visit_info', {})
        medical_content = params.get('medical_content', {}) # This now comes from collected_results

        if not patient_info or not visit_info or not medical_content:
             logger.warning("Missing required data sections (patient_info, visit_info, medical_content) for document generation.")
             # Decide how to handle: raise error or generate partial doc? Raise error for now.
             raise ValueError("Missing required data for document generation.")

        doc = Document()
        # Set default font for Chinese characters
        doc.styles['Normal'].font.name = u'宋体'
        doc.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), u'宋体')

        # Title
        title = doc.add_heading('中山三院康复科医疗报告', level=0) # Assuming this title is static
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        # Spacing after title
        doc.add_paragraph()

        # Patient Info Section
        doc.add_heading('患者基本信息', level=1).style.font.size = Pt(14)
        patient_mapping = {
            'name': '姓名', 'gender': '性别', 'age': '年龄',
            'id_card': '身份证号', 'phone': '电话号码', 'address': '家庭住址'
        }
        patient_data = []
        for key, label in patient_mapping.items():
             value = patient_info.get(key, '未提供') # Provide default if missing
             patient_data.append(f"{label}: {value}")
        # Format patient info (e.g., two items per line)
        for i in range(0, len(patient_data), 2):
            line = '    '.join(patient_data[i:i+2]) # Use spaces for separation
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(6) # Add some space after paragraph

        # Visit Info Section
        doc.add_heading('就诊信息', level=1).style.font.size = Pt(14)
        visit_mapping = {
            'visit_date': '就诊日期', 'department': '科室', 'doctor': '医生姓名'
        }
        visit_data = []
        for key, label in visit_mapping.items():
            value = visit_info.get(key, '未提供')
            visit_data.append(f"{label}: {value}")
        for i in range(0, len(visit_data), 2):
            line = '    '.join(visit_data[i:i+2])
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(6)

        # Medical Content Section (Using FIELDS_ORDER for consistency)
        doc.add_heading('医疗记录', level=1).style.font.size = Pt(14)
        # Use a mapping if display names differ from field keys
        medical_display_mapping = {
             "主诉": "主诉", "现病史": "现病史", "既往史": "既往史",
             "过敏史": "过敏史", "诊断": "初步诊断及建议" # Example of different display name
             # Add mappings for any other fields in medical_content
        }

        for field in FIELDS_ORDER:
             label = medical_display_mapping.get(field, field) # Default to field key if no mapping
             # Get value from medical_content (which corresponds to collected_results)
             value = medical_content.get(field, '未记录') # Provide default if field not in results
             # Ensure value is a string for display
             if not isinstance(value, str):
                  try:
                       value_str = json.dumps(value, ensure_ascii=False)
                  except Exception:
                       value_str = str(value) # Fallback to simple string conversion
             else:
                 value_str = value

             doc.add_paragraph(f"{label}:", style='Intense Quote') # Use a style for emphasis
             doc.add_paragraph(value_str if value_str else "无") # Add content, display '无' if empty
             doc.add_paragraph() # Add space between sections

        # --- Add other sections as needed (e.g., Recommendations, Prescriptions) ---
        # Example:
        # if 'prescription' in medical_content:
        #     doc.add_heading('处方建议', level=1).style.font.size = Pt(14)
        #     doc.add_paragraph(medical_content['prescription'])


        # Save to buffer
        docx_buffer = BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        logger.info("Word document generated successfully.")
        return docx_buffer

    except ValueError as ve:
        logger.error(f"Value error during document generation: {ve}")
        raise # Re-raise validation errors
    except Exception as e:
        logger.exception("Unexpected error during Word document generation.") # Log traceback
        raise # Re-raise unexpected errors