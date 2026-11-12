"""Shared HTTP helpers. Standard library only."""

import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.request


def env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}")
    return value


def redact(text):
    text = re.sub(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_.-]{10,}", "<jwt>", str(text))
    return re.sub(
        r'("(?:access_token|password|subject_token)"\s*:\s*")[^"]+', r"\1<hidden>", text
    )


def request(
    method,
    path,
    body=None,
    bearer=None,
    opener=None,
    headers=None,
    accept="application/json",
):
    h = {**(headers or {})}
    if accept is not None:
        h["Accept"] = accept
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    if bearer:
        h["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(
        env("JFROG_URL").rstrip("/") + path, data=data, headers=h, method=method
    )
    try:
        r = (opener or urllib.request.build_opener()).open(req, timeout=60)
        code, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read()
    try:
        return code, json.loads(raw)
    except ValueError:
        return code, raw[:300].decode("utf-8", "replace")


def ui_session():
    """Cookie session for the admin UI proxy."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    code, _ = request(
        "POST",
        "/ui/api/v1/ui/auth/login",
        {
            "user": env("JFROG_ADMIN_USER"),
            "password": env("JFROG_ADMIN_PASSWORD"),
            "type": "login",
        },
        opener=opener,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    if code != 200:
        raise SystemExit(f"admin UI login failed: {code}")
    return opener


def ui(opener, method, path, body=None):
    return request(
        method,
        path,
        body,
        opener=opener,
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
