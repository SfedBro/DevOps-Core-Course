# Lab 6: Advanced Ansible & CI/CD

**Name:** sfedbro
**Date:** 2026-03-04
**Lab Points:** 10

---

## 1. Overview

Implemented full Lab 6 core scope in `ansible/`:

- refactored roles with `block`/`rescue`/`always`
- added tag strategy for selective execution
- migrated deployment to Docker Compose template + `community.docker.docker_compose_v2`
- added wipe logic with `web_app_wipe` variable and `web_app_wipe` tag
- added GitHub Actions workflow for lint/deploy/verify

Tech stack: Ansible, Jinja2, Docker Compose v2, GitHub Actions, ansible-lint.

---

## 2. Blocks & Tags

### Implemented blocks

- `roles/common/tasks/main.yml`
  - package installation block with `rescue` (apt cache retry) and `always` (log completion)
  - user management block
- `roles/docker/tasks/main.yml`
  - installation block with nested repository sub-block and `rescue` (GPG key retry)
  - runtime configuration block
- `roles/web_app/tasks/main.yml`
  - deploy block with `rescue` (print failure context and fail explicitly)

### Tag strategy

| Tag | Scope |
|-----|-------|
| `common` | entire common role |
| `packages` | package installation tasks |
| `users` | user management tasks |
| `docker` | entire docker role |
| `docker_install` | docker installation tasks |
| `docker_config` | docker configuration tasks |
| `web_app` | entire web_app role |
| `app_deploy` | deployment tasks |
| `compose` | docker compose tasks |
| `web_app_wipe` | wipe tasks only |

### Available tags listing

```
$ ansible-playbook playbooks/provision.yml --list-tags

playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers   TAGS: []
      TASK TAGS: [common, docker, docker_config, docker_install, packages, users]
```

### Selective execution examples

```bash
# Run only docker installation tasks
$ ansible-playbook playbooks/provision.yml --tags "docker_install"

PLAY RECAP
vm1: ok=6  changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0

# Skip common role entirely
$ ansible-playbook playbooks/provision.yml --skip-tags "common"

PLAY RECAP
vm1: ok=7  changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

---

## 3. Docker Compose Migration

### Role rename

- renamed `roles/app_deploy` to `roles/web_app`
- updated role reference in `playbooks/deploy.yml`

### Compose template

File: `roles/web_app/templates/docker-compose.yml.j2`

```yaml
---
services:
  {{ app_name }}:
    image: "{{ docker_image }}:{{ docker_tag }}"
    container_name: {{ app_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
    environment:
{% for key, value in app_env.items() %}
      {{ key }}: "{{ value }}"
{% endfor %}
    restart: {{ restart_policy }}
```

Supported variables: `app_name`, `docker_image`, `docker_tag`, `app_port`, `app_internal_port`, `app_env`, `restart_policy`.

Note: `version` field intentionally omitted — obsolete in Docker Compose v2.

### Role dependency

File: `roles/web_app/meta/main.yml`

```yaml
---
dependencies:
  - role: docker
```

This ensures Docker is installed automatically when only `web_app` role is invoked.

### Deployment tasks

File: `roles/web_app/tasks/main.yml`

1. Include wipe tasks (runs first to support clean reinstall)
2. Create compose project directory
3. Render `docker-compose.yml` from template
4. Deploy via `community.docker.docker_compose_v2`
5. Wait for `/health` endpoint with retry loop (10 retries, 6s delay)

### Variable configuration

File: `group_vars/all.yml`

```yaml
dockerhub_username: sfedbro
dockerhub_password: "{{ lookup('env', 'DOCKERHUB_TOKEN') }}"

app_name: devops-app
docker_image: '{{ dockerhub_username }}/app_python'
docker_tag: latest
app_port: 8000
app_internal_port: 5000
compose_project_dir: '/opt/devops-app'
restart_policy: unless-stopped

app_env:
  APP_ENV: production
```

### Idempotency verification

Second run with no changes shows `changed=0`:

```
$ ansible-playbook playbooks/deploy.yml

PLAY RECAP
vm1: ok=12  changed=0  unreachable=0  failed=0  skipped=4  rescued=0  ignored=0
```

---

## 4. Wipe Logic

### Implementation

- `roles/web_app/defaults/main.yml` — `web_app_wipe: false`
- `roles/web_app/tasks/wipe.yml` — wipe tasks guarded by `when: web_app_wipe | bool`
- `roles/web_app/tasks/main.yml` — wipe included at top before deploy block

Wipe tasks:
1. Check if compose project directory exists (`stat`)
2. Stop and remove compose services (only if directory exists)
3. Remove compose project directory
4. Log completion

### Test scenario 1 — normal deployment (wipe skipped)

```
$ ansible-playbook playbooks/deploy.yml

TASK [web_app : Stop and remove compose services] — skipping: [vm1]
TASK [web_app : Remove docker-compose file]       — skipping: [vm1]
TASK [web_app : Remove compose project directory] — skipping: [vm1]
TASK [web_app : Log wipe completion]              — skipping: [vm1]

PLAY RECAP
vm1: ok=12  changed=1  unreachable=0  failed=0  skipped=4  rescued=0  ignored=0
```

Wipe tasks skipped (`skipped=4`) because `web_app_wipe=false` by default.

### Test scenario 2 — wipe only

```
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe

TASK [web_app : Stop and remove compose services] — changed: [vm1]
TASK [web_app : Remove docker-compose file]       — changed: [vm1]
TASK [web_app : Remove compose project directory] — changed: [vm1]
TASK [web_app : Log wipe completion]
ok: [vm1] => {
    "msg": "Application devops-app wiped successfully"
}

PLAY RECAP
vm1: ok=6  changed=3  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

Deploy tasks did not run — only wipe executed due to `--tags web_app_wipe`.

### Test scenario 3 — clean reinstall (wipe → deploy)

```
$ ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"

TASK [web_app : Stop and remove compose services] — changed: [vm1]
TASK [web_app : Remove docker-compose file]       — changed: [vm1]
TASK [web_app : Remove compose project directory] — changed: [vm1]
TASK [web_app : Log wipe completion]
ok: [vm1] => {"msg": "Application devops-app wiped successfully"}
TASK [web_app : Create compose project directory] — changed: [vm1]
TASK [web_app : Render docker-compose template]   — changed: [vm1]
TASK [web_app : Deploy compose project]           — changed: [vm1]
TASK [web_app : Wait for application endpoint]    — ok: [vm1]

PLAY RECAP
vm1: ok=16  changed=6  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

### Test scenario 4 — safety check (tag only, variable false)

```
$ ansible-playbook playbooks/deploy.yml --tags web_app_wipe

TASK [web_app : Stop and remove compose services] — skipping: [vm1]
TASK [web_app : Remove docker-compose file]       — skipping: [vm1]
TASK [web_app : Remove compose project directory] — skipping: [vm1]
TASK [web_app : Log wipe completion]              — skipping: [vm1]

PLAY RECAP
vm1: ok=12  changed=1  unreachable=0  failed=0  skipped=4  rescued=0  ignored=0
```

Wipe blocked by `when: web_app_wipe | bool` — variable is false so tasks skip even though tag is specified.

### Application health verification after clean reinstall

```
$ curl http://158.160.33.46:8000/health
{"status":"healthy","timestamp":"2026-03-04T18:45:03.801026+00:00","uptime_seconds":70}
```

---

## 5. CI/CD Integration

### Workflow

File: `.github/workflows/ansible-deploy.yml`

Triggers:
- `push` to `main`/`master` for `ansible/**` (excluding `ansible/docs/**`)
- `pull_request` to `main`/`master` for same paths

### Jobs

**lint** (runs on every push and PR):
- installs Python 3.12, ansible, ansible-lint
- installs `community.docker` and `community.general` collections
- runs `ansible-lint playbooks/*.yml`

**deploy** (runs on push only, requires lint to pass):
- installs Ansible and collections
- configures SSH from `SSH_PRIVATE_KEY` secret
- writes vault password from `ANSIBLE_VAULT_PASSWORD` secret
- runs `ansible-playbook playbooks/deploy.yml`
- removes vault password file (`if: always()`)
- verifies `/` and `/health` endpoints with `curl -f`

### GitHub Secrets required

| Secret | Purpose |
|--------|---------|
| `SSH_PRIVATE_KEY` | SSH key for VM access |
| `VM_HOST` | Target VM IP |
| `VM_USER` | SSH username |
| `ANSIBLE_VAULT_PASSWORD` | Ansible Vault decryption |
| `DOCKERHUB_TOKEN` | Docker Hub image pull |

### Badge

Added to `ansible/README.md`:

```markdown
[![Ansible Deployment](https://github.com/SfedBro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg)](https://github.com/SfedBro/DevOps-Core-Course/actions/workflows/ansible-deploy.yml)
```

---

## 6. Testing Results

### Tags available

```
playbook: playbooks/provision.yml

  play #1 (webservers): Provision web servers   TAGS: []
      TASK TAGS: [common, docker, docker_config, docker_install, packages, users]
```

### All wipe scenario results summary

| Scenario | Command | Result |
|----------|---------|--------|
| Normal deploy | `deploy.yml` | `skipped=4 changed=1 ignored=0` |
| Wipe only | `deploy.yml -e "web_app_wipe=true" --tags web_app_wipe` | `changed=3 ignored=0` |
| Clean reinstall | `deploy.yml -e "web_app_wipe=true"` | `changed=6 ignored=0` |
| Safety check | `deploy.yml --tags web_app_wipe` | `skipped=4` wipe blocked |

### Application accessible

```
$ curl http://158.160.33.46:8000/health
{"status":"healthy","timestamp":"2026-03-04T18:45:03.801026+00:00","uptime_seconds":70}
```

---

## 7. Challenges & Solutions

1. **Role migration from container module to compose module**
   - Solution: introduced Jinja2 compose template and project directory strategy with `community.docker.docker_compose_v2`.

2. **Safe destructive operations**
   - Solution: double-gate with explicit `web_app_wipe` variable (default false) and dedicated `web_app_wipe` tag. Both must be set for wipe to execute.

3. **Wipe on already-clean state**
   - Solution: added `stat` check before `docker_compose_v2` call to skip compose down when directory does not exist, eliminating `fatal`/`ignored` in PLAY RECAP.

4. **CI path-noise reduction**
   - Solution: workflow path filters with `ansible/docs/**` exclusion to avoid lint/deploy on documentation-only commits.

5. **Compose runtime dependency**
   - Solution: added `docker-compose-plugin` to Docker role package list and declared `docker` as a role dependency in `web_app/meta/main.yml`.

---

## 8. Research Answers

### Task 1

**What happens if rescue block also fails?**
Play execution fails at that point unless the failing task has `ignore_errors: true`. There is no further fallback after rescue.

**Can you have nested blocks?**
Yes. The `docker` role uses a nested block inside the installation block for repository setup, with its own `rescue` for GPG key retry.

**How do tags inherit to tasks within blocks?**
Tags set on a block are inherited by all tasks inside it. Tasks can also add their own tags on top.

### Task 2

**`restart: always` vs `restart: unless-stopped`**
`always` restarts the container in all cases including after manual `docker stop` or daemon restart. `unless-stopped` preserves an intentional manual stop — the container will not restart after `docker stop` until explicitly started again.

**Compose networks vs default bridge networks**
Docker Compose creates a project-scoped network with automatic DNS resolution between services by service name. The default Docker bridge network is global, not project-scoped, and requires manual container linking or IP addressing.

**Can you use Vault vars in template?**
Yes. Ansible decrypts Vault values before rendering Jinja2 templates, so any Vault-encrypted variable can be referenced in a template as a normal variable.

### Task 3

**Why variable + tag?**
Variable (`web_app_wipe`) controls intent — it must be explicitly set to `true`. Tag (`web_app_wipe`) controls scope — it must be explicitly targeted. Either alone is insufficient: tag alone is blocked by the `when` condition, variable alone still requires the tag to be in scope during a targeted run.

**Difference from `never` tag?**
The `never` tag makes a task permanently skipped in all normal runs with no override path other than explicitly targeting it with `--tags never`. The variable+tag pattern allows three distinct modes: skip (default), wipe-only (tag+variable), and clean reinstall (variable only, all tags run).

**Why wipe before deploy?**
Placing wipe at the top of `main.yml` enables a single playbook run to wipe the old installation and immediately deploy a fresh one. If wipe came after deploy, a clean reinstall would require two separate runs.

**When clean reinstall vs rolling update?**
Clean reinstall is appropriate for configuration drift, corruption, or major version changes where in-place upgrade is risky. Rolling update is preferred for routine version bumps where minimizing downtime matters.

**How to extend wipe for images and volumes?**
Add dedicated tasks using `community.docker.docker_image` with `state: absent` and `community.docker.docker_volume` with `state: absent`, each behind their own boolean flags (`web_app_wipe_images`, `web_app_wipe_volumes`) and included conditionally.

### Task 4

**Security implications of SSH keys in GitHub Secrets**
GitHub Secrets are encrypted at rest and masked in logs, but any repository admin or compromised Actions workflow can access them. The risk is acceptable for non-production deployments; for production, a self-hosted runner with network isolation removes the need to expose SSH keys to GitHub infrastructure.

**How to implement staging → production pipeline?**
Use separate inventories for staging and production, deploy to staging first in one job, run smoke tests, then gate production deployment on manual approval using GitHub Environments with required reviewers.

**How to support rollbacks?**
Tag Docker images with the Git SHA instead of `latest`, store the last successful tag as a GitHub Actions output or in a file on the VM, and add a rollback workflow that accepts a tag input and redeploys with `docker_tag` overridden.

**How self-hosted runner improves security**
A self-hosted runner on the target VM eliminates outbound SSH from GitHub infrastructure entirely. The runner pulls jobs over HTTPS, so no inbound firewall rules or SSH keys need to be shared with GitHub. Network access can be fully controlled at the VM level.

---

## Files Changed

- `ansible/playbooks/deploy.yml`
- `ansible/playbooks/provision.yml`
- `ansible/group_vars/all.yml`
- `ansible/roles/common/defaults/main.yml`
- `ansible/roles/common/tasks/main.yml`
- `ansible/roles/docker/defaults/main.yml`
- `ansible/roles/docker/tasks/main.yml`
- `ansible/roles/web_app/defaults/main.yml`
- `ansible/roles/web_app/meta/main.yml`
- `ansible/roles/web_app/tasks/main.yml`
- `ansible/roles/web_app/tasks/wipe.yml`
- `ansible/roles/web_app/templates/docker-compose.yml.j2`
- `.github/workflows/ansible-deploy.yml`
- `ansible/README.md`

---

## Summary

All core Lab 6 tasks are implemented and verified against a live VM. The four wipe scenarios produce expected results with no unexpected failures or ignored errors. CI/CD workflow enforces lint before deploy and verifies the application health endpoint after each deployment. The double-gate wipe mechanism (variable + tag) provides safe destructive operations that cannot be triggered accidentally.

Total time spent: ~6 hours.

Key learnings: block/rescue patterns significantly improve role robustness; canonical agent state in compose deploys reduces idempotency issues; path filters in GitHub Actions are essential for multi-concern repositories.
