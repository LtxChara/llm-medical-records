# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a medical record generation system (中山三院康复科医疗报告) that uses an LLM to extract structured medical information from patient descriptions and generates Word/PDF documents. It consists of a FastAPI backend and a Vue 3 frontend.

## Common Commands

### Backend
- Run the development server: `cd backend && python server.py`
  - Runs on `http://0.0.0.0:5000` with uvicorn reload enabled.
- Test the API workflow: `cd backend && python test_workflow.py`
- Test document generation: `cd backend && python test_generate_doc.py`

### Frontend
- Install dependencies: `cd frontend && npm install`
- Run dev server: `cd frontend && npm run dev`
  - Runs on `http://localhost:5173` (Vite default).
- Production build: `cd frontend && npm run build`
- Preview build: `cd frontend && npm run preview`

### Python Dependencies
There is no `requirements.txt`. The backend depends on:
- `fastapi`, `uvicorn`, `pydantic`
- `openai`
- `langchain-community`, `langchain-core`
- `json-repair`
- `python-docx`

## Architecture

### Backend (`backend/`)

- **`server.py`**: FastAPI entry point. Exposes three main endpoints:
  - `POST /process`: Takes `{session_id, text}` and starts the LLM extraction workflow.
  - `POST /supplement`: Takes `{session_id, field, text}` to provide missing info for an incomplete field.
  - `POST /generate_doc`: Takes `{input: {patient_info, visit_info, medical_content}}` and returns a `.docx` file stream.
- **`function.py`**: Core orchestration logic.
  - `getLLMReturn(session_id, initial_text)`: Iterates through `FIELDS_ORDER` (主诉 → 现病史 → 既往史 → 过敏史 → 诊断), calls the LLM for each field, and returns `status: "success"`, `"incomplete"`, or `"error"`.
  - `call_llm(field, history)`: Builds the prompt from `med_prompt.py` templates, calls the SiliconFlow API via the OpenAI client, and parses/repairs JSON responses.
  - `generate_word_document(params)`: Uses `python-docx` to generate a formatted medical report.
  - **Configuration**: API key, base URL (`https://api.siliconflow.cn/v1`), and model (`Qwen/Qwen3.5-4B`) are hardcoded near the top of the file.
  - **Session store**: An in-memory global `store: Dict[str, MedicalHistoryManager]`.
- **`chat_memory.py`**: `MedicalHistoryManager` wraps `langchain_community.chat_message_histories.ChatMessageHistory` to maintain separate conversation histories per medical field, with configurable `max_length` and system prompts.
- **`med_prompt.py`**: Contains `system_prompt_templates` and `user_prompt_templates` for each of the five medical fields. The LLM is instructed to return strict JSON like `{"主诉": "..."}` and to ask for supplements when information is insufficient.

### Frontend (`frontend/`)

- **Stack**: Vue 3 (Composition API with `<script setup>`), Vite, Element Plus, SCSS.
- **`App.vue`**: Two-column layout. Left = `PatientInfo`, Right = `AIMedicalPanel`.
- **`PatientInfo.vue`**: Displays the electronic medical record form with editable text areas for each section (主诉, 现病史, etc.). Receives generation updates via `handleGenerate`.
- **`AIMedicalPanel.vue`**: Input area for patient descriptions, model selector, medical section buttons, and action buttons (开始分析 / 打印病历). Communicates with the backend via `fetch`.
- **`PrintTemplate.vue`**: Renders a print-friendly A4 template and uses `html2canvas` + `jsPDF` to generate and download a PDF.

### Data Flow
1. User enters text in `AIMedicalPanel` and clicks "开始分析".
2. Frontend sends the text to `/process` with a `session_id`.
3. Backend iterates through the five fields. If the LLM response contains supplement keywords (e.g., "请补充", "信息不足"), it returns `status: "incomplete"` with the field name and message.
4. Frontend would (in a complete implementation) prompt the user for the missing info and call `/supplement`.
5. Once all fields succeed, the backend returns `status: "success"` with `result: {主诉, 现病史, ...}`.
6. "打印病历" generates a PDF client-side; the backend's `/generate_doc` endpoint can also generate a Word document.

## Important Notes for Development

- **API URL mismatch**: `AIMedicalPanel.vue` hardcodes `ANALYZE_API = 'http://localhost:5000/process/invoke/'` and `PRINT_API = 'http://localhost:5000/generate_doc/invoke/'`, but the backend defines routes at `/process` and `/generate_doc` (no `/invoke/` suffix).
- **CORS**: The backend allows `http://localhost:5173` and `http://127.0.0.1:5173`.
- **Logging**: Both backend and frontend log to `backend/server.log` and the console.
- **Tests**: `test_workflow.py` simulates a full `/process` → `/supplement` flow. `test_generate_doc.py` tests the document generation endpoint with sample data and saves to `backend/test_outputs/`.
