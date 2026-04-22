"""单元测试脚本：验证MedicalHistoryManager和消息构建逻辑"""
from chat_memory import MedicalHistoryManager

def test_field_status_management():
    print('=== 字段状态管理测试 ===')
    mgr = MedicalHistoryManager()
    assert not mgr.is_field_completed('主诉')
    mgr.set_field_result('主诉', '头晕3天')
    mgr.mark_field_completed('主诉')
    assert mgr.is_field_completed('主诉')
    assert mgr.get_field_result('主诉') == '头晕3天'
    mgr.reset_field_status('主诉')
    assert not mgr.is_field_completed('主诉')
    print('  [PASS] 字段状态管理')

def test_conversation_history():
    print('\n=== 对话历史测试 ===')
    mgr = MedicalHistoryManager()
    mgr.add_message('主诉', 'user', '我头晕好几天了')
    mgr.add_message('主诉', 'ai', '请补充持续时间')
    mgr.add_message('主诉', 'user', '持续了3天')
    msgs = mgr.to_openai_format('主诉')
    roles = [m['role'] for m in msgs]
    assert roles == ['system', 'user', 'assistant', 'user'], f"Unexpected roles: {roles}"
    print(f"  [PASS] 历史消息角色序列: {roles}")

def test_user_input_aggregation():
    print('\n=== 用户输入聚合测试 ===')
    mgr = MedicalHistoryManager()
    mgr.add_message('主诉', 'user', '我头晕好几天了')
    mgr.add_message('主诉', 'user', '持续了3天')
    aggregated = mgr.get_user_all_input('主诉')
    assert '我头晕好几天了' in aggregated
    assert '持续了3天' in aggregated
    print(f"  [PASS] 聚合输入: {aggregated}")

def test_supplement_resets_status():
    print('\n=== 补充重置状态测试 ===')
    mgr = MedicalHistoryManager()
    mgr.mark_field_completed('主诉')
    assert mgr.is_field_completed('主诉')
    mgr.add_supplement('主诉', '还有恶心')
    assert not mgr.is_field_completed('主诉')
    assert mgr.get_supplement_count('主诉') == 1
    print('  [PASS] 补充后字段重置为未完成')

def test_initial_text_all_fields():
    print('\n=== 初始文本注入所有字段测试 ===')
    mgr = MedicalHistoryManager()
    initial = '患者头晕三天'
    fields = ['主诉', '现病史', '既往史', '过敏史', '诊断']
    for f in fields:
        mgr.add_message(f, 'user', initial)
    for f in fields:
        assert mgr.get_user_all_input(f) == initial, f"字段 {f} 未收到初始文本"
    print(f'  [PASS] 所有 {len(fields)} 个字段均收到初始文本')

def test_diagnosis_context_injection():
    print('\n=== 诊断上下文注入测试 ===')
    mgr = MedicalHistoryManager()
    # 模拟已完成字段
    for f in ['主诉', '现病史', '既往史', '过敏史']:
        mgr.set_field_result(f, f'{f}结果')
        mgr.mark_field_completed(f)
    # 注入诊断上下文
    ctx = '以下为患者已提取的医疗记录信息，请据此进行诊断：\n【主诉】主诉结果\n【现病史】现病史结果'
    mgr.add_message('诊断', 'user', ctx)
    msgs = mgr.to_openai_format('诊断')
    user_msgs = [m for m in msgs if m['role'] == 'user']
    assert len(user_msgs) == 1
    assert '主诉结果' in user_msgs[0]['content']
    print(f'  [PASS] 诊断上下文已注入，user消息数: {len(user_msgs)}')

def test_all_fields_completion():
    print('\n=== 全字段完成状态测试 ===')
    mgr = MedicalHistoryManager()
    for f in ['主诉', '现病史', '既往史', '过敏史', '诊断']:
        mgr.set_field_result(f, f'{f}内容')
        mgr.mark_field_completed(f)
    result = {f: mgr.get_field_result(f) for f in ['主诉', '现病史', '既往史', '过敏史', '诊断']}
    assert all(result.values()), f"部分字段为空: {result}"
    print(f'  [PASS] 全字段结果: {result}')

if __name__ == '__main__':
    test_field_status_management()
    test_conversation_history()
    test_user_input_aggregation()
    test_supplement_resets_status()
    test_initial_text_all_fields()
    test_diagnosis_context_injection()
    test_all_fields_completion()
    print('\n所有单元测试通过！')
