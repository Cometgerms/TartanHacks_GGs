"""Test script to verify frontend-backend connection."""
import requests
import os

BACKEND_URL = "http://localhost:5000"

# Skip these tests during pytest runs because they require an external server process.
# Use `python test_connection.py` to run them manually.
try:
    import pytest  # type: ignore

    pytest.skip("Integration tests require running backend server on localhost:5000", allow_module_level=True)
except Exception:
    pass

def test_health():
    """Test health endpoint."""
    print("Testing /health endpoint...")
    try:
        resp = requests.get(f"{BACKEND_URL}/health")
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_api_health():
    """Test API health endpoint."""
    print("\nTesting /api/health endpoint...")
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health")
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def test_process_with_audio():
    """Test /api/process endpoint with audio file."""
    print("\nTesting /api/process endpoint with audio...")

    # Find test audio file
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    test_file = None

    for f in os.listdir(uploads_dir):
        if f.endswith((".mp3", ".wav")) and "Man" in f:
            test_file = os.path.join(uploads_dir, f)
            break

    if not test_file or not os.path.exists(test_file):
        print("  ERROR: No test audio file found")
        return False

    print(f"  Using test file: {os.path.basename(test_file)}")

    try:
        with open(test_file, "rb") as f:
            files = {"audio": (os.path.basename(test_file), f, "audio/mp3")}
            data = {
                "text": "make it clearer",
                "session_id": "test_session_123"
            }

            resp = requests.post(f"{BACKEND_URL}/api/process", files=files, data=data)
            print(f"  Status: {resp.status_code}")

            if resp.status_code == 200:
                result = resp.json()
                print(f"  Session ID: {result.get('session_id')}")
                print(f"  Reply: {result.get('reply', '')[:100]}...")
                print(f"  Output path: {result.get('output_audio_path')}")
                print(f"  Known effects: {result.get('known_effects')}")
                return True
            else:
                print(f"  Response: {resp.text[:200]}")
                return False

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Backend Connection Test")
    print("=" * 60)

    results = []
    results.append(("Health Check", test_health()))
    results.append(("API Health Check", test_api_health()))
    results.append(("Audio Processing", test_process_with_audio()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
