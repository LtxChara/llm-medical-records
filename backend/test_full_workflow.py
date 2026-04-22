"""完整工作流测试：验证从/process到多轮supplement再到最终success的闭环。"""
import requests
import json
import uuid

BASE_URL = "http://localhost:5000"
PROCESS_ENDPOINT = f"{BASE_URL}/process"
SUPPLEMENT_ENDPOINT = f"{BASE_URL}/supplement"

SESSION_ID = f"test_session_{uuid.uuid4()}"
print(f"--- Starting Full Workflow Test with Session ID: {SESSION_ID} ---\n")

# Step 1: 提供较完整的初始描述，但可能仍缺少某些字段
initial_text = "患者男性，45岁，头晕3天，呈旋转性，站立时加重，休息可缓解。无恶心呕吐。否认高血压、糖尿病史。否认药物及食物过敏史。未就诊。"
print(f"[Step 1] Calling /process with text: '{initial_text}'")

r1 = requests.post(PROCESS_ENDPOINT, json={"session_id": SESSION_ID, "text": initial_text})
r1.raise_for_status()
res1 = r1.json()
print(json.dumps(res1, indent=2, ensure_ascii=False))

round_num = 1
while res1.get("status") == "incomplete" and round_num <= 5:
    field = res1["field"]
    msg = res1["message"]
    print(f"\n[Supplement Round {round_num}] Field '{field}' needs supplement: {msg}")

    # 根据字段提供合理的补充
    if field == "主诉":
        supplement = "间断性头晕3天。"
    elif field == "现病史":
        supplement = "3天前无明显诱因出现头晕，呈旋转性，站立时加重，卧床休息可稍缓解，无恶心呕吐，无耳鸣耳聋。"
    elif field == "既往史":
        supplement = "否认高血压、糖尿病史。否认手术、外伤史。否认肝炎、结核等传染病史。"
    elif field == "过敏史":
        supplement = "否认药物及食物过敏史。"
    elif field == "诊断":
        supplement = "患者无其他特殊不适。"
    else:
        supplement = "请继续分析。"

    r_sup = requests.post(SUPPLEMENT_ENDPOINT, json={"session_id": SESSION_ID, "field": field, "text": supplement})
    r_sup.raise_for_status()
    res1 = r_sup.json()
    print(f"[Supplement Round {round_num} Response]")
    print(json.dumps(res1, indent=2, ensure_ascii=False))
    round_num += 1

if res1.get("status") == "success":
    print("\n[Result] Workflow completed successfully!")
    result = res1.get("result", {})
    for k, v in result.items():
        print(f"  {k}: {v}")
    # 断言所有字段非空
    expected_fields = ["主诉", "现病史", "既往史", "过敏史", "诊断"]
    missing = [f for f in expected_fields if not result.get(f)]
    if missing:
        print(f"\n[Warning] Fields with empty values: {missing}")
    else:
        print("\n[PASS] All fields have content.")
elif res1.get("status") == "incomplete":
    print("\n[Result] Workflow still incomplete after max rounds.")
else:
    print(f"\n[Result] Workflow ended with status: {res1.get('status')}")

print(f"\n--- Test Finished ---")
