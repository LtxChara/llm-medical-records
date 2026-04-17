import requests
import json
import uuid

# --- Configuration ---
BASE_URL = "http://localhost:5000"  # Your FastAPI server address
PROCESS_ENDPOINT = f"{BASE_URL}/process"
SUPPLEMENT_ENDPOINT = f"{BASE_URL}/supplement"

# Generate a unique session ID for this test run
SESSION_ID = f"test_session_{uuid.uuid4()}"
print(f"--- Starting Test Workflow with Session ID: {SESSION_ID} ---")

# --- Step 1: Initial Call to /process ---
initial_text = "我头晕好几天了。" # Intentionally somewhat vague input
print(f"\n[Step 1] Calling /process with initial text: '{initial_text}'")

process_payload = {
    "session_id": SESSION_ID,
    "text": initial_text
}

try:
    response_process = requests.post(PROCESS_ENDPOINT, json=process_payload)
    response_process.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    result_process = response_process.json()

    print("[Step 1] Response from /process:")
    print(json.dumps(result_process, indent=2, ensure_ascii=False))

    # --- Step 2: Check response and potentially call /supplement ---
    if result_process.get("status") == "incomplete":
        print("\n[Step 2] Initial process requires supplementation.")
        field_to_supplement = result_process.get("field")
        supplement_message = result_process.get("message") # The message from LLM asking for info

        if not field_to_supplement:
            print("[Error] Incomplete status but no 'field' provided in response.")
        else:
            # Simulate user providing the requested information based on the prompt
            # NOTE: The actual supplemental text will depend on the LLM's specific prompt message
            # Example: If message asks about duration and nature, provide that.
            print(f"LLM requests supplement for field: '{field_to_supplement}'")
            print(f"LLM's message: {supplement_message}")

            # --- !!! Simulate user input based on the prompt !!! ---
            # This is an EXAMPLE, adjust based on actual LLM prompts
            supplemental_text = ""
            if "持续时间" in supplement_message:
                supplemental_text += "头晕大概持续了3天。 "
            if "性质" in supplement_message or "特点" in supplement_message:
                supplemental_text += "是那种旋转的感觉，站起来的时候特别明显。"
            if not supplemental_text: # Fallback if keywords not found
                 supplemental_text = "补充信息：头晕是旋转性的，持续3天了，站立时加重。"

            print(f"Simulated supplemental text: '{supplemental_text}'")

            supplement_payload = {
                "session_id": SESSION_ID,
                "field": field_to_supplement,
                "text": supplemental_text
            }

            print(f"\n[Step 2] Calling /supplement for field '{field_to_supplement}'...")
            response_supplement = requests.post(SUPPLEMENT_ENDPOINT, json=supplement_payload)
            response_supplement.raise_for_status()
            result_supplement = response_supplement.json()

            print("[Step 2] Response from /supplement:")
            print(json.dumps(result_supplement, indent=2, ensure_ascii=False))

            # Check final status after supplementation
            if result_supplement.get("status") == "success":
                print("\n[Result] Workflow completed successfully after supplementation.")
                # Store the final result if needed for document generation test
                FINAL_RESULT = result_supplement.get("result")
            elif result_supplement.get("status") == "incomplete":
                print("\n[Result] Workflow still requires more information after supplementation.")
            else:
                print("\n[Result] Workflow ended with status:", result_supplement.get("status"))


    elif result_process.get("status") == "success":
        print("\n[Result] Workflow completed successfully on the first call.")
        # Store the final result if needed for document generation test
        FINAL_RESULT = result_process.get("result")
    else:
        print("\n[Result] Workflow ended with status:", result_process.get("status"))

except requests.exceptions.RequestException as e:
    print(f"\n[Error] HTTP Request failed: {e}")
except json.JSONDecodeError as e:
    print(f"\n[Error] Failed to decode JSON response: {e}")
    # Print raw text if JSON decoding fails
    if 'response_process' in locals() and response_process:
        print("Raw response text (process):", response_process.text)
    if 'response_supplement' in locals() and response_supplement:
        print("Raw response text (supplement):", response_supplement.text)
except Exception as e:
     print(f"\n[Error] An unexpected error occurred: {e}")

print(f"\n--- Test Workflow for Session ID: {SESSION_ID} Finished ---")