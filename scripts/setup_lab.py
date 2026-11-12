"""Create the demo objects. Needs JFROG_URL, JFROG_ADMIN_USER, JFROG_ADMIN_PASSWORD, LAB_SUB.
Run cleanup_lab.py first if objects from an earlier run exist."""

import os
import secrets
import sys

from common import env, ui, ui_session

PROVIDER = "lab-github-oidc"
MAPPING = "lab-ci-mapping"
USER = "lab-ci-user"
ISSUER = "https://token.actions.githubusercontent.com"
UI_OIDC = "/ui/api/v1/access/api/v1/oidc"


def main():
    aud = os.environ.get("OIDC_AUDIENCE", "jfrog-lab-aud")
    s = ui_session()
    failed = False

    code, _ = ui(
        s,
        "POST",
        "/ui/api/v1/access/api/v2/users",
        {
            "username": USER,
            "password": "Aa1!" + secrets.token_urlsafe(12),
            "email": USER + "@example.invalid",
            "groups": [],
            "admin": False,
            "profile_updatable": True,
            "disable_ui_access": False,
            "internal_password_disabled": False,
        },
    )
    print("create user:", code)
    code, _ = ui(
        s,
        "PATCH",
        "/ui/api/v1/access/api/v2/groups/readers/members",
        {"remove": [USER]},
    )
    print("take user out of readers:", code)

    code, groups = ui(s, "GET", "/ui/api/v1/access/api/v2/groups?limit=500")
    print("groups on tenant:", groups if code == 200 else code)
    print("real 'admin' group exists:", "admin" in str(groups))

    code, d = ui(
        s,
        "POST",
        UI_OIDC,
        {
            "name": PROVIDER,
            "issuer_url": ISSUER,
            "description": "lab, safe to delete",
            "provider_type": "generic",
            "audience": aud,
        },
    )
    print("create provider:", code, "" if code < 300 else d)
    failed |= code >= 300

    code, d = ui(
        s,
        "POST",
        f"{UI_OIDC}/{PROVIDER}/identity_mappings",
        {
            "name": MAPPING,
            "description": "lab, main branch of this repo only",
            "priority": 1,
            "claims": {"sub": env("LAB_SUB")},
            "token_spec": {
                "username": USER,
                "scope": "applied-permissions/groups:readers",
                "expires_in": 300,
            },
        },
    )
    print("create mapping:", code, "" if code < 300 else d)
    failed |= code >= 300

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
