"""
测试新的直接处理流程

现在的行为：
1. 用户上传文件 + 输入 prompt
2. AI 直接分析 prompt，识别 effects
3. 生成 AudioEngine plan（带所有参数）
4. 执行处理
5. 返回简单直接的成功消息 + 处理后的音频

不再有：
- ❌ 询问后续问题
- ❌ 对话式回复
- ❌ 调用 LLM 生成回复

只有：
- ✓ 直接处理
- ✓ 技术性总结
- ✓ 生成的代码在终端显示
"""

import requests
import os

BACKEND_URL = "http://localhost:5000"

def test_direct_processing():
    """Test that AI directly processes audio without asking questions."""

    print("=" * 70)
    print("测试：直接处理（无询问）")
    print("=" * 70)

    # Find test audio file
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    test_file = None

    for f in os.listdir(uploads_dir):
        if f.endswith((".mp3", ".wav")) and "Man" in f:
            test_file = os.path.join(uploads_dir, f)
            break

    if not test_file or not os.path.exists(test_file):
        print("❌ 错误: 找不到测试音频文件")
        return False

    print(f"\n使用测试文件: {os.path.basename(test_file)}")

    # Test 1: Natural language prompt
    print("\n" + "-" * 70)
    print("测试 1: 自然语言 prompt")
    print("-" * 70)

    with open(test_file, "rb") as f:
        files = {"audio": (os.path.basename(test_file), f, "audio/mp3")}
        data = {
            "text": "make it clearer and reduce background noise",
            "session_id": "test_direct_1"
        }

        print(f"发送请求: {data['text']}")
        resp = requests.post(f"{BACKEND_URL}/api/process", files=files, data=data)

        if resp.status_code == 200:
            result = resp.json()
            print(f"\n✓ 状态: 成功 (200)")
            print(f"✓ AI 回复: {result.get('reply', '')}")
            print(f"✓ 识别的效果: {result.get('known_effects', [])}")
            print(f"✓ 输出文件: {result.get('output_audio_path', 'None')}")
            print(f"✓ AudioEngine 运行: {result.get('audio_engine', {}).get('ran', False)}")

            # Check that reply is direct, not asking questions
            reply = result.get('reply', '').lower()
            is_asking = any(word in reply for word in ['?', 'would you like', 'do you want', 'should i', 'upload'])

            if is_asking:
                print(f"\n⚠️  警告: AI 似乎在询问问题而不是直接处理")
                print(f"   回复内容: {result.get('reply', '')}")
                return False
            else:
                print(f"\n✓ 确认: AI 没有询问，直接处理并返回结果")
                return True
        else:
            print(f"\n❌ 错误: {resp.status_code}")
            print(f"   响应: {resp.text[:200]}")
            return False

    return False

def test_command_format():
    """Test direct processing with command format."""

    print("\n" + "=" * 70)
    print("测试：命令格式 \\reverb(); \\compressor();")
    print("=" * 70)

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
    test_file = None

    for f in os.listdir(uploads_dir):
        if f.endswith((".mp3", ".wav")) and "Man" in f:
            test_file = os.path.join(uploads_dir, f)
            break

    if not test_file:
        print("❌ 错误: 找不到测试文件")
        return False

    with open(test_file, "rb") as f:
        files = {"audio": (os.path.basename(test_file), f, "audio/mp3")}
        data = {
            "text": "\\reverb(); \\compressor();",
            "session_id": "test_direct_2"
        }

        print(f"发送请求: {data['text']}")
        resp = requests.post(f"{BACKEND_URL}/api/process", files=files, data=data)

        if resp.status_code == 200:
            result = resp.json()
            print(f"\n✓ 状态: 成功 (200)")
            print(f"✓ AI 回复: {result.get('reply', '')}")
            print(f"✓ 识别的效果: {result.get('known_effects', [])}")
            print(f"✓ 输出文件: {result.get('output_audio_path', 'None')}")

            reply = result.get('reply', '').lower()
            is_asking = '?' in reply or 'would you' in reply

            if not is_asking:
                print(f"✓ 确认: 直接处理，无询问")
                return True
            else:
                print(f"⚠️  警告: 检测到询问")
                return False
        else:
            print(f"❌ 错误: {resp.status_code}")
            return False

# Skip during pytest runs: requires running backend server.
try:
    import pytest  # type: ignore

    pytest.skip("Integration test requires backend server on localhost:5000", allow_module_level=True)
except Exception:
    pass

if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "AI Agent 直接处理测试" + " " * 15 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = []

    # Test 1
    result1 = test_direct_processing()
    results.append(("自然语言直接处理", result1))

    # Test 2
    result2 = test_command_format()
    results.append(("命令格式直接处理", result2))

    # Summary
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {status}: {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("🎉 所有测试通过！" if all_passed else "⚠️  部分测试失败"))
    print()
