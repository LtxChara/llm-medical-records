import requests
import json
import os
from datetime import datetime

# --- Configuration ---
BASE_URL = "http://localhost:5000"  # Your FastAPI server address
GENERATE_DOC_ENDPOINT = f"{BASE_URL}/generate_doc"
OUTPUT_DIR = "test_outputs" # Directory to save the generated document

# --- Sample Data (Replace with actual data from a successful workflow) ---
# This is critical: You need the structure matching the 'result' dictionary
# from a successful '/process' or '/supplement' call.
sample_medical_content = {
    "主诉": "间断性旋转性头晕3天，站立时加重。", # Example value
    "现病史": "患者3天前无明显诱因出现头晕，呈旋转性，站立时加重，卧床休息可稍缓解，无恶心呕吐，无耳鸣耳聋，未就诊。", # Example value
    "既往史": "否认高血压、糖尿病史。否认手术、外伤史。", # Example value
    "过敏史": "否认药物及食物过敏史。", # Example value
    "诊断": '初步诊断：考虑良性阵发性位置性眩晕可能。建议：行 Dix-Hallpike 等相关检查以明确诊断，注意休息，避免快速转头。' # Example value
    # Add other fields if your FIELDS_ORDER includes more
}

# Sample patient and visit info (adjust as needed)
sample_patient_info = {
    "name": "李四",
    "gender": "男",
    "age": 45,
    "id_card": "440xxxxxxxxxxxxxxx",
    "phone": "138xxxxxxxx",
    "address": "广东省广州市天河区"
}

sample_visit_info = {
    "visit_date": datetime.now().strftime('%Y-%m-%d'),
    "department": "康复医学科",
    "doctor": "王医生",
    "record_id": "KHFY123456"
}

# --- Construct Payload ---
# Ensure the structure matches the GenerateDocRequest Pydantic model in server.py
generate_doc_payload = {
    "input": {
        "patient_info": sample_patient_info,
        "visit_info": sample_visit_info,
        "medical_content": sample_medical_content
    }
}

print("--- Starting Document Generation Test ---")
print("Using payload:")
print(json.dumps(generate_doc_payload, indent=2, ensure_ascii=False))

# --- Call /generate_doc Endpoint ---
try:
    response = requests.post(GENERATE_DOC_ENDPOINT, json=generate_doc_payload, stream=True) # Use stream=True for file download

    print(f"\nResponse Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")

    response.raise_for_status() # Check for HTTP errors

    # Check content type
    content_type = response.headers.get('content-type', '').lower()
    expected_content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if expected_content_type not in content_type:
        print(f"[Warning] Unexpected content type: {content_type}. Expected: {expected_content_type}")
        print("Raw response content might not be a valid docx file:")
        # print(response.text) # Print text only if it's likely not binary
    else:
        print(f"Content type '{content_type}' received, attempting to save file.")

        # Create output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            print(f"Created output directory: {OUTPUT_DIR}")

        # Extract filename from headers if possible (optional, server creates one)
        # content_disposition = response.headers.get('content-disposition')
        # filename = "generated_document.docx" # Default
        # if content_disposition:
        #     # Basic parsing, might need improvement for complex headers
        #     parts = content_disposition.split('filename*=')
        #     if len(parts) > 1:
        #         encoded_name = parts[1].split("''")[-1]
        #         filename = requests.utils.unquote(encoded_name)
        #     else:
        #         parts = content_disposition.split('filename=')
        #         if len(parts) > 1:
        #             filename = parts[1].strip('"')

        # Create a unique local filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = os.path.join(OUTPUT_DIR, f"{sample_patient_info.get('name', 'patient')}_report_{timestamp}.docx")

        # Save the file content
        bytes_written = 0
        with open(output_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                bytes_written += len(chunk)

        if bytes_written > 0:
            print(f"\n[Success] Document saved successfully as '{output_filename}' ({bytes_written} bytes)")
        else:
            print("\n[Error] No content received from server to save.")


except requests.exceptions.RequestException as e:
    print(f"\n[Error] HTTP Request failed: {e}")
except Exception as e:
    print(f"\n[Error] An unexpected error occurred: {e}")

print("\n--- Document Generation Test Finished ---")