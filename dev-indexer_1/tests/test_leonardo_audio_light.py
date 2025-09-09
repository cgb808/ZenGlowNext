#!/usr/bin/env python3
"""
Quick test for Leonardo's voice integration
Tests TTS and speech recognition capabilities
"""

import os
import sys
from pathlib import Path

import pytest

SKIP_AUDIO = os.getenv("SKIP_AUDIO_TESTS") == "1"

pytestmark = pytest.mark.skipif(SKIP_AUDIO, reason="SKIP_AUDIO_TESTS=1")


def test_piper_tts():
    """Test Piper TTS installation (import only unless WANT_PIPER_FULL=1)."""
    print("🗣️  Testing Piper TTS (light mode)...")
    if os.getenv("SKIP_AUDIO_TESTS") == "1":
        print("↪️  Skipping Piper test due to SKIP_AUDIO_TESTS=1")
        return True
    try:
        import piper  # type: ignore

        print("✅ Piper TTS imported successfully")
        if os.getenv("WANT_PIPER_FULL") == "1":  # placeholder for future deeper validation
            print("(Full mode flag set; deeper validation could be added here)")
        return True
    except ImportError as e:
        print(f"❌ Piper TTS import failed: {e}")
        return False


def test_whisper(monkeypatch):
    """Lightweight Whisper test (import only by default).

    Full model load is expensive (memory + download) and was causing OOM / test kill.
    To force a real model load set env WANT_WHISPER_FULL=1.
    """
    print("🎤 Testing Whisper (light mode)...")
    try:
        import whisper  # type: ignore

        print("✅ Whisper imported successfully")
        if os.getenv("WANT_WHISPER_FULL") == "1":
            try:
                model = whisper.load_model("tiny")  # smallest model for speed
                print("✅ Whisper tiny model loaded (full mode)")
            except Exception as e:  # pragma: no cover - optional path
                print(f"⚠️ Whisper tiny model load failed: {e}")
                return False
        return True
    except Exception as e:
        print(f"❌ Whisper import failed: {e}")
        return False


def test_leonardo_endpoints():
    """Test Leonardo audio endpoints (filesystem presence only)."""
    print("🤖 Testing Leonardo endpoints (light mode)...")
    if os.getenv("SKIP_AUDIO_TESTS") == "1":
        print("↪️  Skipping Leonardo endpoint test due to SKIP_AUDIO_TESTS=1")
        return True
    try:
        leonardo_path = Path("app/leonardo")
        if not leonardo_path.exists():
            print("❌ Leonardo module directory not found")
            return False
        print("✅ Leonardo module directory exists")
        audio_router_path = leonardo_path / "audio_router.py"
        if not audio_router_path.exists():
            print("❌ Leonardo audio router not found")
            return False
        print("✅ Leonardo audio router found")
        return True
    except Exception as e:
        print(f"❌ Leonardo endpoint test failed: {e}")
        return False


def main():
    """Main test function"""
    print("🎤 Leonardo Voice Integration Test")
    print("=" * 40)

    tests = [
        ("Piper TTS", test_piper_tts),
        ("Whisper", test_whisper),
        ("Leonardo Endpoints", test_leonardo_endpoints),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if test_func():
            passed += 1
        print("-" * 40)

    print(f"\n🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Leonardo voice integration is ready.")
        print("\n📝 Next steps:")
        print("1. Start the FastAPI server: uvicorn app.main:app --reload")
        print(
            "2. Test Leonardo TTS: curl -X POST 'http://localhost:8000/leonardo/speak' -H 'Content-Type: application/json' -d '{\"text\":\"Hello, I am Leonardo, ready to think analytically.\"}'"
        )
        print("3. Use the frontend interface to interact with Leonardo's voice")
    else:
        print("⚠️  Some tests failed. Please check the installation.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
