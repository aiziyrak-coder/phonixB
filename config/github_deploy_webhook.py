"""
GitHub Webhooks orqali deploy (SSH / GitHub Actions secret shart emas).

Sozlash:
  1) .env: GITHUB_DEPLOY_WEBHOOK_SECRET=<uzun tasodifiy qiymat>
  2) GitHub → phonixB (yoki phonixF) → Settings → Webhooks → Add webhook
     Payload URL: https://api.ilmiyfaoliyat.uz/hooks/github/deploy/
     Content type: application/json
     Secret: xuddi shu GITHUB_DEPLOY_WEBHOOK_SECRET
     Events: Just the push event
  3) Gunicorn foydalanuvchisi deploy skriptini ishga tushira olishi kerak
     (odatda NOPASSWD sudo yoki skriptni deploy user uchun).

Xavfsizlik: secret bo‘lmasa endpoint 404; imzo noto‘g‘ri bo‘lsa 401.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
import threading
from typing import Any

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def _verify_github_signature(payload: bytes, secret: str, signature_header: str | None) -> bool:
    if not signature_header or not secret:
        return False
    if not signature_header.startswith('sha256='):
        return False
    sent = signature_header[7:].strip()
    expected = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, expected)


def _run_deploy_script() -> None:
    script = getattr(settings, 'DEPLOY_HOOK_SCRIPT', '/phonix/deploy_phonix.sh')
    env = {**os.environ, 'PHONIX_GIT_RESET': 'true'}
    try:
        proc = subprocess.run(
            ['/bin/bash', script],
            cwd='/phonix',
            env=env,
            timeout=3600,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            logger.error(
                'Deploy hook script exit %s stderr=%s stdout_tail=%s',
                proc.returncode,
                (proc.stderr or '')[:2000],
                (proc.stdout or '')[-2000:],
            )
        else:
            logger.info('Deploy hook finished OK (stdout tail): %s', (proc.stdout or '')[-500:])
    except Exception:
        logger.exception('Deploy hook subprocess failed')


@csrf_exempt
@require_POST
def github_deploy_webhook(request) -> HttpResponse:
    secret = getattr(settings, 'GITHUB_DEPLOY_WEBHOOK_SECRET', '') or ''
    if not secret:
        return HttpResponseNotFound()

    raw = request.body
    sig = request.META.get('HTTP_X_HUB_SIGNATURE_256')
    if not _verify_github_signature(raw, secret, sig):
        logger.warning('GitHub deploy webhook: invalid signature')
        return JsonResponse({'detail': 'invalid signature'}, status=401)

    event = request.headers.get('X-GitHub-Event') or ''
    if event != 'push':
        return JsonResponse({'ok': True, 'ignored': f'event:{event}'}, status=200)

    try:
        data: dict[str, Any] = json.loads(raw.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'invalid json'}, status=400)

    allowed_repos = getattr(settings, 'GITHUB_DEPLOY_REPOS', frozenset())
    repo_name = (data.get('repository') or {}).get('full_name') or ''
    if allowed_repos and repo_name not in allowed_repos:
        return JsonResponse({'ok': True, 'ignored': f'repo:{repo_name}'}, status=200)

    branch = (getattr(settings, 'GITHUB_DEPLOY_HOOK_BRANCH', 'master') or 'master').strip()
    ref = data.get('ref') or ''
    if ref != f'refs/heads/{branch}':
        return JsonResponse({'ok': True, 'ignored': f'ref:{ref}'}, status=200)

    t = threading.Thread(target=_run_deploy_script, name='github-deploy-hook', daemon=True)
    t.start()
    logger.info('GitHub deploy webhook: accepted push ref=%s repo=%s', ref, repo_name)
    return JsonResponse({'accepted': True, 'ref': ref}, status=202)

