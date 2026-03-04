# LAB05 — Configuration Management with Ansible

## 1. Architecture Overview

В рамках лабораторной работы была реализована автоматизированная настройка сервера и деплой приложения с использованием Ansible.

Архитектура состоит из:

- Локальная машина (WSL) — управление через Ansible
- Удалённая виртуальная машина в Yandex Cloud
- Docker контейнер с приложением
- Docker Hub как registry

Ansible используется как инструмент конфигурационного управления и деплоя.

---

## 2. Project Structure

Структура проекта:

```
ansible/

  ansible.cfg
  inventory/
    hosts.ini

  playbooks/
    provision.yml
    deploy.yml
    group_vars/
      all.yml (encrypted with Ansible Vault)

  roles/
    common/
    docker/
    app_deploy/

  docs/
    LAB05.md
    OUTPUT.txt
```

---

## 3. Roles Description

### 3.1 common

Назначение:

- Обновление apt cache
- Установка базовых пакетов
- Настройка timezone

Используются переменные:

- common_packages
- system_timezone

---

### 3.2 docker

Назначение:

- Добавление Docker repository
- Установка docker-ce, containerd, python3-docker
- Запуск и enable Docker service
- Добавление пользователя в docker group

Используется handler:

- restart docker

Переменные:

- docker_user

---

### 3.3 app_deploy

Назначение:

- Логин в Docker Hub (через vault переменные)
- Pull Docker image
- Запуск контейнера
- Проверка доступности через health endpoint

Используются:

- docker_login
- docker_image
- docker_container
- wait_for
- uri

Переменные:

- docker_username
- docker_token
- docker_image
- container_name
- app_port

---

## 4. Security

Для хранения чувствительных данных используется Ansible Vault.

Файл:
group_vars/all.yml

Содержит:

- docker_username
- docker_token

Файл зашифрован командой:

ansible-vault encrypt group_vars/all.yml

Vault пароль вводится при запуске playbook через:

ansible-playbook playbooks/deploy.yml --ask-vault-pass

Это предотвращает хранение токенов в открытом виде.

---

## 5. Idempotency Proof

Provision playbook был запущен дважды.

Первый запуск:

```
PLAY RECAP **************************************************************************************
vm1                        : ok=11   changed=8    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Последний(повторный) запуск:

```
PLAY RECAP **************************************************************************************
vm1                        : ok=10   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Это подтверждает идемпотентность ролей.

Аналогично deploy playbook при повторном запуске не вносит изменений, если конфигурация не изменилась.

---

## 6. Deployment Verification

После выполнения deploy.yml:

1. Контейнер запущен:
   docker ps

2. Приложение доступно:
   curl http://<VM_IP>:5000/health\
   тесты проведены на `VM_IP` 46.21.245.116

Возвращается

```
{"status":"healthy","timestamp":"2026-02-25T20:16:51.847876+00:00","uptime_seconds":61}
```

Это подтверждает успешный деплой.

---

## 7. Answers to Questions

### Why use roles?

Роли позволяют:

- Делить конфигурацию на логические блоки
- Повторно использовать код
- Делать структуру проекта масштабируемой
- Улучшать читаемость и поддержку

---

### Why use Ansible Vault?

Vault используется для:

- Защиты данных
- Безопасного хранения токенов
- Исключения хранения секретов в открытом виде в git

---

### What ensures idempotency?

Идемпотентность достигается за счёт:

- использования state: present
- update_cache с cache_valid_time
- использования docker_container вместо shell
- отсутствия raw команд
- корректной обработки сервисов

---

## 8. Conclusion

В рамках лабораторной работы реализовано:

- Полная автоматизация настройки сервера
- Установка Docker
- Автоматический деплой приложения
- Защита секретов через Vault
- Идемпотентная конфигурация
- Health check после деплоя

---
