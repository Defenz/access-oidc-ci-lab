"""Remove the demo objects. Run locally with the same environment."""

import base64

from common import env, request, ui, ui_session

PROVIDER = "lab-github-oidc"
MAPPING = "lab-ci-mapping"
USER = "lab-ci-user"
UI_OIDC = "/ui/api/v1/access/api/v1/oidc"


def basic():
    raw = env("JFROG_ADMIN_USER") + ":" + env("JFROG_ADMIN_PASSWORD")
    return "Basic " + base64.b64encode(raw.encode()).decode()


def art(method, path):
    return request(method, path, headers={"Authorization": basic()}, accept=None)


def main():
    s = ui_session()
    print(
        "delete mapping:",
        ui(s, "DELETE", f"{UI_OIDC}/{PROVIDER}/identity_mappings/{MAPPING}")[0],
    )
    print("delete provider:", ui(s, "DELETE", f"{UI_OIDC}/{PROVIDER}")[0])
    print("delete user:", ui(s, "DELETE", "/ui/api/v1/access/api/v2/users/" + USER)[0])
    code, repos = art("GET", "/artifactory/api/repositories")
    if code == 200:
        for r in repos:
            if r.get("key", "").startswith("lab-r06-"):
                print(
                    "delete leftover repo:",
                    r["key"],
                    art("DELETE", "/artifactory/api/repositories/" + r["key"])[0],
                )
    print("providers left:", ui(s, "GET", UI_OIDC)[1])


if __name__ == "__main__":
    main()
