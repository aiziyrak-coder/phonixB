"""GitHub deploy webhook — imzo va ref tekshiruvlari."""

import hashlib
import hmac
import json
import time
from unittest import mock

import pytest
from django.test import Client


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    return f'sha256={digest}'


@pytest.mark.django_db
def test_webhook_disabled_returns_404(settings):
    settings.GITHUB_DEPLOY_WEBHOOK_SECRET = ''
    client = Client()
    r = client.post('/hooks/github/deploy/', b'{}', content_type='application/json')
    assert r.status_code == 404


@pytest.mark.django_db
@mock.patch('config.github_deploy_webhook._run_deploy_script')
def test_push_accepted_starts_deploy(mock_run, settings):
    settings.GITHUB_DEPLOY_WEBHOOK_SECRET = 'whsec_test'
    settings.GITHUB_DEPLOY_REPOS = frozenset({'aiziyrak-coder/phonixB'})
    settings.GITHUB_DEPLOY_HOOK_BRANCH = 'master'
    settings.DEPLOY_HOOK_SCRIPT = '/phonix/deploy_phonix.sh'

    payload = {
        'ref': 'refs/heads/master',
        'repository': {'full_name': 'aiziyrak-coder/phonixB'},
    }
    body = json.dumps(payload).encode('utf-8')
    client = Client()
    r = client.post(
        '/hooks/github/deploy/',
        data=body,
        content_type='application/json',
        HTTP_X_GITHUB_EVENT='push',
        HTTP_X_HUB_SIGNATURE_256=_sign(body, 'whsec_test'),
    )
    assert r.status_code == 202
    assert r.json().get('accepted') is True
    time.sleep(0.15)
    mock_run.assert_called_once()


@pytest.mark.django_db
def test_wrong_signature_401(settings):
    settings.GITHUB_DEPLOY_WEBHOOK_SECRET = 'whsec_test'
    settings.GITHUB_DEPLOY_REPOS = frozenset({'aiziyrak-coder/phonixB'})
    body = b'{}'
    client = Client()
    r = client.post(
        '/hooks/github/deploy/',
        data=body,
        content_type='application/json',
        HTTP_X_GITHUB_EVENT='push',
        HTTP_X_HUB_SIGNATURE_256='sha256=deadbeef',
    )
    assert r.status_code == 401
