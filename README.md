# access-oidc-ci-lab

GitHub Actions OIDC token exchange lab.

## Setup

```sh
export JFROG_URL=https://your-instance.jfrog.io
export JFROG_ADMIN_USER=... JFROG_ADMIN_PASSWORD=...
export LAB_SUB='repo:<owner>@<owner id>/<repo>@<repo id>:ref:refs/heads/main'
python3 scripts/setup_lab.py
```

`LAB_SUB` is the `sub` claim of a main-branch run. A failed exchange prints it.

## Run

```sh
gh workflow run exchange-check --repo Defenz/access-oidc-ci-lab
gh run watch --repo Defenz/access-oidc-ci-lab
```

The workflow needs no JFrog credential. The only secret is `JFROG_URL`.

## Output

```
exchange: 200
exchange scope: applied-permissions/groups:readers applied-permissions/user
positive control, user + groups re-mint: 200
negative control, exchanged token on Access admin: 403
negative control, exchanged token on Artifactory admin: 403
DECISIVE mint, second unquoted groups:admin element: 200 applied-permissions/user applied-permissions/groups:readers applied-permissions/groups:admin
DECISIVE Access admin read with escalated token: 200
escalated token on Artifactory admin (expected 403, needs second mint): 403
DECISIVE mint real platform admin token: 200 applied-permissions/admin
Access admin read with real admin token: 200
Artifactory admin read with real admin token: 200
Artifactory admin write, create repo: 200
Artifactory admin write, delete repo: 200
```

## Cleanup

```sh
python3 scripts/cleanup_lab.py
```
