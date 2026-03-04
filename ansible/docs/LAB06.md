# Lab 6: Advanced Ansible & CI/CD - Submission

**Name:** SfedBro
**Date:** 2026-03-04
**Lab Points:** 10/10 (bonus not implemented)

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
  - package block with `rescue` and `always`
  - user-management block
- `roles/docker/tasks/main.yml`
  - installation block
  - docker repository sub-block with retry `rescue`
  - runtime configuration block

### Tag strategy

- `common`, `packages`, `users`
- `docker`, `docker_install`, `docker_config`
- `web_app`, `app_deploy`, `compose`
- `web_app_wipe`

### Commands for selective execution

```bash
cd ansible
ansible-playbook playbooks/provision.yml --tags "docker"
ansible-playbook playbooks/provision.yml --skip-tags "common"
ansible-playbook playbooks/provision.yml --tags "packages"
ansible-playbook playbooks/provision.yml --tags "docker_install"
ansible-playbook playbooks/provision.yml --list-tags
```

---

## 3. Docker Compose Migration

### Role rename

- renamed `roles/app_deploy` to `roles/web_app`
- updated playbook role reference in `playbooks/deploy.yml`

### Compose template

- file: `roles/web_app/templates/docker-compose.yml.j2`
- supports dynamic vars:
  - `app_name`
  - `docker_image`
  - `docker_tag`
  - `app_port`
  - `app_internal_port`
  - `app_env`

### Role dependency

- file: `roles/web_app/meta/main.yml`
- dependency added:

```yaml
dependencies:
  - role: docker
```

### Deployment tasks

- file: `roles/web_app/tasks/main.yml`
- creates compose directory
- templates `docker-compose.yml`
- deploys via `community.docker.docker_compose_v2`
- verifies `/health` with retry loop

### Variable configuration

- file: `playbooks/group_vars/all.yml`
- uses compose variables (`docker_tag`, `compose_project_dir`, `app_internal_port`, `app_env`)

---

## 4. Wipe Logic

### Implementation

- defaults: `roles/web_app/defaults/main.yml`
  - `web_app_wipe: false`
- wipe tasks: `roles/web_app/tasks/wipe.yml`
  - compose down
  - remove compose file
  - remove app directory
- main flow: `roles/web_app/tasks/main.yml`
  - wipe include placed before deploy block

### Execution patterns

```bash
# normal deployment
ansible-playbook playbooks/deploy.yml

# wipe only
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe

# clean reinstall (wipe -> deploy)
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"

# safety check: tag only, variable false
ansible-playbook playbooks/deploy.yml --tags web_app_wipe
```

---

## 5. CI/CD Integration

### Workflow

- file: `.github/workflows/ansible-deploy.yml`
- triggers on `push`/`pull_request` for `ansible/**` changes
- excludes `ansible/docs/**`

### Jobs

1. `lint`
- installs Ansible + ansible-lint
- installs required collections
- runs `ansible-lint playbooks/*.yml`

2. `deploy` (push only)
- prepares SSH from secrets
- decrypts Vault password from secret
- runs `ansible-playbook playbooks/deploy.yml`
- verifies `/` and `/health` endpoints

### Badge

- added status badge in `ansible/README.md`

---

## 6. Testing Results

### Static validation done locally

- structure and references validated (`git status`, file audit)
- role rename and imports validated (`app_deploy` replaced by `web_app` in runtime files)
- compose dependency gap fixed: `docker-compose-plugin` added to Docker packages

### Runtime validation pending

`ansible-playbook` is not installed in current local shell, so actual remote execution output/screenshots must be captured in VM environment:

```bash
cd ansible
ansible-playbook playbooks/provision.yml --list-tags
ansible-playbook playbooks/deploy.yml
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true" --tags web_app_wipe
ansible-playbook playbooks/deploy.yml -e "web_app_wipe=true"
```

---

## 7. Challenges & Solutions

1. Role migration from container module to compose module
- solution: introduced compose template + project directory strategy.

2. Safe destructive operations
- solution: added explicit wipe variable default false and dedicated wipe tag.

3. CI path-noise reduction
- solution: workflow path filters with docs exclusion.

4. Compose runtime dependency
- solution: added `docker-compose-plugin` in Docker role package list.

---

## 8. Research Answers

### Task 1 research

1. **What happens if rescue block also fails?**
- Play execution fails unless that failing task is ignored.

2. **Can you have nested blocks?**
- Yes; Docker role uses nested block for repository setup and retry flow.

3. **How do tags inherit to tasks within blocks?**
- Tags set on the block apply to child tasks.

### Task 2 research

1. **`restart: always` vs `restart: unless-stopped`**
- `always` restarts even after manual stop or daemon restart; `unless-stopped` preserves intentional manual stop.

2. **Compose networks vs default bridge networks**
- Compose creates project-scoped managed networks and service DNS; plain bridge is generic and manually managed.

3. **Can you use Vault vars in template?**
- Yes, decrypted Vault values can be used directly in Jinja templates during playbook runtime.

### Task 3 research

1. **Why variable + tag?**
- Variable controls intent; tag enables targeted execution and safer operator workflow.

2. **Difference from `never` tag?**
- `never` blocks task in normal runs entirely; variable+tag pattern allows both wipe-only and clean reinstall flows.

3. **Why wipe before deploy?**
- Ensures deterministic clean reinstall in a single run.

4. **When clean reinstall vs rolling update?**
- Clean reinstall for drift/corruption; rolling update for low-downtime standard upgrades.

5. **How to extend wipe for images/volumes?**
- Add explicit cleanup tasks (`docker image rm`, volume removal) behind separate boolean flags and dedicated tags.

### Task 4 research

1. **Security implications of SSH keys in GitHub Secrets**
- Better than hardcoding, but repo/admin compromise can expose deployment access.

2. **How to do staging -> production pipeline?**
- Separate inventories/environments, gated approvals, and staged workflow jobs.

3. **How to support rollbacks?**
- Deploy immutable image tags, persist last successful release, and add rollback workflow/playbook input.

4. **How self-hosted runner changes security**
- Can reduce external SSH surface and improve network isolation if runner host is hardened.

---

## Files Changed

- `ansible/playbooks/deploy.yml`
- `ansible/playbooks/provision.yml`
- `ansible/playbooks/group_vars/all.yml`
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

Core Lab 6 scope is implemented in repository structure and code. Remaining part for final submission is runtime evidence collection (playbook outputs and screenshots) from target VM and GitHub Actions run logs.
