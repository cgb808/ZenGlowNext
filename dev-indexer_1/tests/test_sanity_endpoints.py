import os
import shutil
import pytest
from fastapi.testclient import TestClient

from app.app_factory import create_app

app = create_app()
client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    # Accept either legacy {'ok': True} or simplified {'status': 'ok'} shape
    assert (data.get('ok') is True) or (data.get('status') == 'ok')


def test_profiles():
    r = client.get('/profiles')
    assert r.status_code == 200
    data = r.json()
    assert 'profiles' in data and 'count' in data


def test_phi3_ping():
    r = client.get('/phi3/ping')
    assert r.status_code == 200
    data = r.json()
    assert data.get('status') == 'ok'


def test_llm_disabled_all():
    # Force all backends disabled and call a simple generate
    os.environ['LLM_DISABLE'] = 'all'
    from app.rag.llm_client import LLMClient
    c = LLMClient()
    meta = c.generate_with_metadata('Test prompt', prefer='auto')
    assert meta['backend'] == 'disabled'
    assert meta['disabled'] is True


def test_config_binaries():
    r = client.get('/config/binaries')
    assert r.status_code == 200
    data = r.json()
    assert 'binaries' in data and isinstance(data['binaries'], dict)
    # Expect at least these keys to be present after ensure_cached attempts
    for name in ('ffmpeg', 'sox', 'curl'):
        # Presence of key (found may be false depending on environment)
        assert name in data['binaries']
        entry = data['binaries'][name]
        assert 'found' in entry and 'attempts' in entry


@pytest.mark.skipif(shutil.which('piper') is None, reason='piper binary not present')
def test_piper_tts():
    payload = {"text": "Hello world", "voice": None}
    r = client.post('/audio/piper/tts', json=payload)
    assert r.status_code == 200
    data = r.json()
    assert 'audio_base64' in data and data['mime'] == 'audio/wav'
