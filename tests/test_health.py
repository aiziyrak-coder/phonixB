import json

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_live_returns_200():
    c = Client()
    r = c.get('/health/')
    assert r.status_code == 200
    data = json.loads(r.content.decode())
    assert data.get('status') == 'ok'
    assert data.get('service') == 'phoenix-api'
    assert 'version' in data


@pytest.mark.django_db
def test_health_live_alias_path():
    c = Client()
    r = c.get('/health/live/')
    assert r.status_code == 200


@pytest.mark.django_db
def test_health_ready_returns_status():
    c = Client()
    r = c.get('/health/ready/')
    assert r.status_code in (200, 503)
    data = json.loads(r.content.decode())
    assert data.get('status') in ('ready', 'unready')
    assert 'checks' in data


@pytest.mark.django_db
def test_metrics_prometheus_text():
    c = Client()
    r = c.get('/metrics/')
    assert r.status_code == 200
    body = r.content.decode()
    assert 'phoenix_up' in body
    assert 'phoenix_uptime_seconds' in body


@pytest.mark.django_db
def test_metrics_secret_header(monkeypatch):
    monkeypatch.setenv('METRICS_SECRET', 'test-metrics-key')
    c = Client()
    assert c.get('/metrics/').status_code == 403
    ok = c.get('/metrics/', HTTP_X_METRICS_KEY='test-metrics-key')
    assert ok.status_code == 200
