# opal-api

[![Validate OpenAPI contracts](https://github.com/PatMartin/opal-api/actions/workflows/openapi-validate.yml/badge.svg)](https://github.com/PatMartin/opal-api/actions/workflows/openapi-validate.yml)
![OpenAPI 3.1.0](https://img.shields.io/badge/OpenAPI-3.1.0-6BA539)
![Contract Version 1.7.1](https://img.shields.io/badge/contracts-v1.7.1-blue)
![License: ISC](https://img.shields.io/badge/license-ISC-lightgrey)

Published OpenAPI 3.1.0 contracts and validation tooling for the OPAL suite — five local microservices for visual perception (`look`), speech recognition (`listen`), guarded reasoning (`think`), event routing & action execution (`event`), and speech synthesis (`say`), all built on a shared kernel contract (`openapi/shared/opal_kernel.yaml`).

## Table of Contents

- [Overview](#overview)
- [Highlights](#highlights)
- [Architecture & Project Structure](#architecture--project-structure)
  - [The Five Services & Shared Kernel](#the-five-services--shared-kernel)
  - [Cross-Service Data & Control Flow](#cross-service-data--control-flow)
  - [Repository Layout](#repository-layout)
- [Contract Conventions (OPAL Suite Standard v1.2)](#contract-conventions-opal-suite-standard-v12)
- [REST Route Tree](#rest-route-tree)
- [CLI Contract (`x-opal-cli`)](#cli-contract-x-opal-cli)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart & Usage](#quickstart--usage)
  - [Validate, Lint, Bundle, and Test](#validate-lint-bundle-and-test)
  - [Load a Resolved Contract in Python](#load-a-resolved-contract-in-python)
  - [Example CLI Workflows](#example-cli-workflows)
- [Configuration & Rulesets](#configuration--rulesets)
- [Development & Extending Contracts](#development--extending-contracts)
- [Testing & Validation Pipeline](#testing--validation-pipeline)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

`opal-api` is the single source of truth for the REST and CLI interfaces of the **OPAL** suite. It is a **contracts-and-validation repository only** — no service runtime code lives here. Each OPAL service is specified as an OpenAPI 3.1.0 YAML document under [`openapi/`](openapi/) that mounts shared path items, parameters, headers, error envelopes, and schemas from [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml).

The contracts serve three audiences simultaneously:

1. **Service implementations** (`opal-event-svc`, `opal-listen-svc`, `opal-look-svc`, `opal-say-svc`, `opal-think-svc`), which implement the HTTP routes, status codes, ETag concurrency semantics, and ZeroMQ event envelopes defined here.
2. **Generated Typer CLI & SPA clients**, which call only the public REST surface and derive their command tree directly from each operation's `x-opal-cli` extension metadata.
3. **Contract authors**, who use the repository's 14-stage validation pipeline (Redocly structural checks, four Spectral rulesets, dereferenced bundling, and seven Python regression suites) to evolve the suite without breaking cross-service invariants.

All five service contracts and the shared kernel are currently at version **1.7.1**, encoding **OPAL Suite Standard v1.2**.

---

## Highlights

- **Single shared kernel (`opal_kernel.yaml`)** — common routes (`/api/v1/health/`, `/api/v1/info/`, `/api/v1/setting/`, `/api/v1/backup/`, `/api/v1/profile/`, `/api/v1/persona/`, `/api/v1/service/`, `/api/v1/engine/`), correlation headers, `OpalError` responses, and schemas are defined once and mounted via `$ref`.
- **End-to-end correlation propagation** — every request and response (including errors, binary downloads, and SSE/PCM streams) carries `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, and `X-Opal-Causation-Id`, which also propagate into the two-frame ZeroMQ `BusEvent` wire envelope (`data.metadata`).
- **Optimistic concurrency everywhere** — mutable configuration routes return strong ETags and require `If-Match` (`^"[^"]+"$`), returning `428 Precondition Required` when missing, `412 Precondition Failed` when stale, and `422 Unprocessable Entity` for weak/wildcard tags.
- **Portable personas (`x-opal-persona`)** — `opal-think` acts as the authoritative persona registry while every service supports standalone local CRUD (`origin: local | owner`), resolving settings in strict order: **explicit request field > persona binding > active profile > service default**.
- **Self-describing, least-privilege tool execution** — `opal-think` has no internal tool executor; it discovers and invokes registered `opal-event` actions (`shell`, `http`, `python`) under a scoped `think` principal (`actions:read`, `actions:execute`, `executions:read`) with JSON Schema Draft 2020-12 input validation (`ActionInputSchema`).
- **Normative CLI bindings (`x-opal-cli`)** — every operation maps to a canonical `opal <service> [parent] [group] <command>` command, verified by Spectral rules and Python parity tests.
- **Self-testing lint rules** — [`tests/test_lint.py`](tests/test_lint.py) mutates copies of the specs and asserts that every custom Spectral rule fires on violations.

---

## Architecture & Project Structure

### The Five Services & Shared Kernel

| File | Title | Version | Default Server | Responsibility & Key Resources |
| --- | --- | --- | --- | --- |
| [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) | OPAL Suite Kernel | `1.7.1` | *(mounted via `$ref`)* | Correlation headers/params, `If-Match`, `Idempotency-Key`, `OpalError` envelope, `BearerAuth`, and reusable `pathItems` for `health`, `info`, `setting`, `backup`, `profile`, `engine`, and `service`. |
| [`openapi/opal_event.yaml`](openapi/opal_event.yaml) | Opal Event API | `1.7.1` | `http://127.0.0.1:8080` | REST event ingress & management for the ZeroMQ XSUB/XPUB broker: `EventInput`/`Event`, `topic/`, `Rule` (`Condition` predicates, `.*` prefix matching), discriminated `Action` (`ShellAction`, `HttpAction`, `PythonAction` with `ActionInputSchema`), `Execution` records (`queued`, `running`, `succeeded`, `failed`, `timed_out`, `dropped`), and `stats/`. |
| [`openapi/opal_listen.yaml`](openapi/opal_listen.yaml) | Voice Intent API | `1.7.1` | `http://localhost:8000` | Wakeword detection, STT (+ async `stt_refiner`), intent matching, and slot extraction: `wakeword/`, `intent/` + `phrase`, `slot/` + `value` + `alias`, live `recognition/` (`start`, `stop`, `status`, SSE `stream`, diagnostic `test_text`/`test_audio`), `failed_utterance/` (`promote`), `regression/` (`run`), `performance/`, and `health/audio_devices`. |
| [`openapi/opal_look.yaml`](openapi/opal_look.yaml) | OPAL Look — MVP Plus Visual Observation API | `1.7.1` | `http://127.0.0.1:8082` | Visual observation: optional discoverable detection `engine/` (+ `discover`, `capabilities`), engine-owned `model/` (`load`/`unload`), single-image `predict`, compute `hardware/`, and ephemeral RTSP `stream/` (202 admission, SSE `events`, MJPEG `video`, `snapshot`, `metrics`, `stop`; video-only streams need no engine; source credentials redacted). |
| [`openapi/opal_say.yaml`](openapi/opal_say.yaml) | OPAL Say API | `1.7.1` | `http://127.0.0.1:8080` | Host-installed TTS engine abstraction (Piper, Kokoro, etc.): discovered `engine/`, registered `voice/` (`validate`, `test`), `generate` (completed WAV or raw `s16le` mono PCM with `X-Opal-Sample-Rate`), and `generate/stream` (progressive raw PCM). |
| [`openapi/opal_think.yaml`](openapi/opal_think.yaml) | OPAL Think API | `1.7.1` | `http://127.0.0.1:8080` | Guarded reasoning service: asynchronous `task/` (`202 Accepted` + `Location`, SSE `stream`, cooperative `cancel`, redacted `TaskStep` summaries), optional persistent `session/`, and read-only `model/` discovery. |

### Cross-Service Data & Control Flow

```text
  ┌───────────────┐  opal.listen.intent.match   ┌───────────────────────────┐
  │  opal-listen  │ ──────────────────────────► │        opal-event         │
  │ (mic / STT /  │                             │  ZeroMQ XSUB/XPUB Broker  │
  │  intent/slot) │                             │  + Rules & Action Runner  │
  ├───────────────┤                             │   (shell / http / python) │
  │   opal-look   │   per-stream SSE only;      │                           │
  │ (engines /    │   republish via CLI pipe    └──────┬─────────────▲──────┘
  │  RTSP streams)│                                    │             │
  └───────────────┘          HTTP Action: POST /task/  │             │ Least-privilege REST:
                             (untrusted event context) │             │  GET  /api/v1/action/
                                                       ▼             │  POST /api/v1/action/{id}/execute
                                                ┌───────────────┐    │  GET  /api/v1/execution/{id}
                                                │  opal-think   │────┘
                                                │ (durable Task │
                                                │  reasoning)   │
                                                └───────┬───────┘
                                                        │ Persona registry (owner)
                                                        │ & spoken responses via Event/CLI
                                                        ▼
                                                ┌───────────────┐
                                                │   opal-say    │
                                                │ (WAV / s16le  │
                                                │  PCM synthesis│
                                                └───────────────┘
```

Key architectural boundaries enforced by the contracts:

- **Event is the sole action authority**: `opal-think` has no internal tool registry, shell runner, or approval engine. It discovers enabled actions in `opal-event`, validates arguments against `ActionInputSchema`, invokes `POST /api/v1/action/{action_id}/execute`, and polls `GET /api/v1/execution/{execution_id}` until terminal (`succeeded`, `failed`, `timed_out`, `dropped`).
- **Least-privilege `think` principal**: `opal_event.yaml` (`x-opal-authorization`) grants the `think` principal only `actions:read`, `actions:execute`, and `executions:read`, explicitly denying `actions:write`, `rules:write`, and `settings:write`.
- **Admission vs. completion**: `POST` to `/api/v1/event/`, `/api/v1/action/{action_id}/execute`, `/api/v1/task/`, and `/api/v1/stream/` returns `202 Accepted` (admission only, never synchronous completion). Manual action execution validates `EventInput.data` against `input_schema` synchronously (`422` on failure); rule-triggered dispatches record failures asynchronously as `Execution` records with `status: dropped` and `error_code: input_validation_failed`.
- **Loopback-first security**: Services bind `127.0.0.1` by default where `BearerAuth` may be explicitly disabled; non-loopback bindings require `BearerAuth` (and ZeroMQ CURVE in `opal-event`). Credentials are referenced via `token_env` / `credential_ref` and never appear in responses, exports, backups, or logs.

### Repository Layout

```text
opal-api/
├── openapi/
│   ├── opal_event.yaml              # OPAL Event OpenAPI 3.1.0 contract
│   ├── opal_listen.yaml             # OPAL Listen OpenAPI 3.1.0 contract
│   ├── opal_look.yaml               # OPAL Look OpenAPI 3.1.0 contract
│   ├── opal_say.yaml                # OPAL Say OpenAPI 3.1.0 contract
│   ├── opal_think.yaml              # OPAL Think OpenAPI 3.1.0 contract
│   └── shared/
│       └── opal_kernel.yaml         # Shared Suite Kernel (mounted via external $ref)
├── tests/
│   ├── spec_util.py                 # Dereferences kernel + local $refs & hoists x-opal-cli maps
│   ├── test_lint.py                 # Mutates specs to prove Spectral rules fire on violations
│   ├── test_event_150.py            # Event action metadata, schemas, fixtures, scopes & settings
│   ├── test_think_event.py          # Think <-> Event principal, scope, and route boundary tests
│   ├── test_look_cli.py             # Look x-opal-cli coverage & operational route assertions
│   ├── test_listen_150.py           # Listen settings & backup If-Match concurrency assertions
│   ├── test_say_150.py              # Say atomic backup import/restore & If-Match assertions
│   ├── test_rest_security.py        # Suite-wide BearerAuth, 401/403, and authorization semantics
│   └── fixtures/
│       └── event_150/               # 10 valid/legacy/invalid action YAML fixtures
├── docs/
│   ├── COOKBOOK.md                  # Unified Typer CLI reference & 50 multi-service recipes
│   └── create_cli.txt               # Prompt specification for CLI documentation generation
├── resources/
│   └── prompts/
│       └── create_readme.md         # Reusable prompt for generating repository READMEs
├── dist/                            # Bundled standalone specs generated by `npm run bundle` (gitignored)
├── .github/workflows/
│   └── openapi-validate.yml         # 14-stage GitHub Actions validation pipeline
├── redocly.yaml                     # Redocly structural OpenAPI 3.1 configuration
├── .spectral.yaml                   # Base Spectral OAS ruleset
├── .spectral.opal.yaml              # OPAL Suite Standard Spectral ruleset
├── .spectral.opal.look.yaml         # OPAL Look contract-specific Spectral ruleset
├── .spectral.opal.think.yaml        # OPAL Think contract-specific Spectral ruleset
├── package.json                     # npm validation, linting, bundling, and test scripts
└── requirements.txt                 # Python test dependencies (PyYAML, jsonschema)
```

---

## Contract Conventions (OPAL Suite Standard v1.2)

Every service contract adheres to the normative rules defined in [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) and enforced by [`.spectral.opal.yaml`](.spectral.opal.yaml):

1. **Namespace & path shape**: All routes live under `/api/v1` with singular resource names (`/api/v1/voice/`, `/api/v1/task/`, `/api/v1/rule/`) and a mandatory trailing slash on collection roots.
2. **Correlation headers**:
   - Inbound request header parameters on every path item: `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, `X-Opal-Causation-Id` (1–128 printable ASCII characters `^[!-~]+$`; invalid values return `422`).
   - Outbound response headers on every response (including `204`, `4xx`/`5xx`, binary streams, and SSE): `X-Opal-Request-Id` and `X-Opal-Transaction-Id` (`required: true`), plus `X-Opal-Session-Id` and `X-Opal-Causation-Id` (`required: false`, conditionally present).
3. **Strong ETag concurrency**:
   - Portable logical configuration carries a strong ETag.
   - All configuration mutations (`POST`, `PUT`, `PATCH`, `DELETE` on config resources, settings, and `backup/import` & `backup/restore`) require `If-Match` matching `^"[^"]+"$`.
   - Missing `If-Match` returns `428 Precondition Required`; stale ETag returns `412 Precondition Failed`; malformed/weak/wildcard ETag returns `422 Unprocessable Entity`.
4. **Standard status codes & error envelope**:
   - `201 Created` always includes a `Location` response header.
   - `202 Accepted` indicates asynchronous admission (plus `Location` where a status resource is created).
   - `204 No Content` for empty deletions.
   - All `4xx`/`5xx` JSON responses use `OpalError` (`{ "error": { "code", "message", "details", "request_id", "transaction_id", "session_id", "causation_id", "retryable" } }`), except `503` on `/health/live` and `/health/ready`, which returns `OpalHealthProbe` (`status: unavailable`, `ready: false`).
5. **Bounded collections (no cursor pagination)**:
   - Configuration catalogs return full arrays (subject to deployment caps).
   - Growing histories (`event/`, `execution/`, `task/`, `session/`, etc.) return bounded arrays in deterministic newest-first order with a `limit` query parameter (`minimum: 1`).
6. **Profiles vs. Personas (`x-opal-persona`)**:
   - A **profile** (`/api/v1/profile/`) is a preset of service operating defaults; at most one profile is active (`is_active: true`) at a time.
   - A **persona** (`/api/v1/persona/`) is a portable identity (`^[A-Za-z0-9][A-Za-z0-9._-]*$`) with optional per-service bindings (e.g., `voice_id` in Say, model/instructions in Think).

---

## REST Route Tree

Routes mounted from [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) across **all five services**:

```text
/api/v1
├── info/                            GET             (ServiceInfo: name, version, api_version)
├── info/ping                        GET             (LivenessRead: status=ok)
├── health/                          GET             (OpalHealthReport)
├── health/live                      GET             (OpalHealthProbe: 200 / 503)
├── health/ready                     GET             (OpalHealthProbe: 200 / 503)
├── setting/                         GET · PATCH     (OpalSettingsMap, PATCH requires If-Match)
├── setting/{key}                    GET · PUT · DELETE (SettingRead/SettingUpdate, PUT/DELETE require If-Match)
├── profile/                         GET · POST      (OpalProfile, POST requires If-Match)
├── profile/{profile_id}             GET · PATCH · DELETE (PATCH/DELETE require If-Match)
├── profile/{profile_id}/activate    POST            (requires If-Match)
├── persona/                         GET · POST      (OpalPersonaRead/Create, POST requires If-Match; not mounted on look)
├── persona/{persona_id}             GET · PATCH · DELETE (PATCH/DELETE require If-Match; not on look)
├── persona/{persona_id}/validate    POST            (OpalValidationReport; not on look)
├── backup/list                      GET             (OpalBackupInfo[])
├── backup/create                    POST            (201 + Location)
├── backup/download/{filename}       GET             (application/octet-stream)
├── backup/restore/{filename}        POST            (OpalImportResult, requires If-Match)
├── backup/{filename}                DELETE          (204)
├── backup/export                    GET             (OpalConfigExport, excludes secrets/history)
├── backup/import                    POST            (OpalImportResult, requires If-Match)
├── backup/validate                  POST · GET      (OpalValidationReport; GET on event/listen/say)
├── service/start                    POST            (OpalServiceStatus; logs/opal_<service>.log)
├── service/stop                     POST            (OpalServiceStatus)
└── service/log                      GET             (OpalServiceLogTail; ?lines=10)
    (plus /api/v1/engine/ GET and /api/v1/engine/{engine_id} GET/PATCH on say and look)
```

Service-specific routes:

```text
opal-event (openapi/opal_event.yaml)
├── /api/v1/event/                   POST (202) · GET · DELETE
├── /api/v1/event/{event_id}         GET · DELETE
├── /api/v1/topic/                   GET
├── /api/v1/rule/                    GET · POST
├── /api/v1/rule/{rule_id}           GET · PATCH · DELETE
├── /api/v1/rule/{rule_id}/test      POST
├── /api/v1/action/                  GET · POST
├── /api/v1/action/{action_id}       GET · PATCH · DELETE
├── /api/v1/action/{action_id}/execute POST (202)
├── /api/v1/execution/               GET
├── /api/v1/execution/{execution_id} GET
└── /api/v1/stats/                   GET

opal-listen (openapi/opal_listen.yaml)
├── /api/v1/recognition/start        POST
├── /api/v1/recognition/stop         POST
├── /api/v1/recognition/status       GET
├── /api/v1/recognition/stream       GET (text/event-stream SSE)
├── /api/v1/recognition/test_text    POST
├── /api/v1/recognition/test_audio   POST (multipart/form-data)
├── /api/v1/wakeword/                GET · POST
├── /api/v1/wakeword/{wakeword_id}   GET · PATCH · DELETE
├── /api/v1/intent/                  GET · POST
├── /api/v1/intent/{intent_id}       GET · PATCH · DELETE
├── /api/v1/intent/{intent_id}/phrase GET · POST
├── /api/v1/intent/{intent_id}/phrase/{phrase_id} DELETE
├── /api/v1/slot/                    GET · POST
├── /api/v1/slot/{slot_id}           GET · PATCH · DELETE
├── /api/v1/slot/{slot_id}/value     GET · POST
├── /api/v1/slot/{slot_id}/value/{value_id} DELETE
├── /api/v1/slot/{slot_id}/value/{value_id}/alias GET · POST
├── /api/v1/slot/{slot_id}/value/{value_id}/alias/{alias_id} DELETE
├── /api/v1/failed_utterance/        GET · POST
├── /api/v1/failed_utterance/{fu_id} GET · PATCH · DELETE
├── /api/v1/failed_utterance/{fu_id}/promote POST
├── /api/v1/regression/              GET · POST
├── /api/v1/regression/run           POST
├── /api/v1/regression/{test_id}     GET · PATCH · DELETE
├── /api/v1/performance/last         GET
├── /api/v1/performance/summary      GET
├── /api/v1/performance/history      GET
└── /api/v1/health/audio_devices     GET

opal-look (openapi/opal_look.yaml)
├── /api/v1/engine/discover          POST
├── /api/v1/engine/{engine_id}/capabilities GET
├── /api/v1/model/                   GET
├── /api/v1/model/{model_id}         GET
├── /api/v1/model/{model_id}/load    POST
├── /api/v1/model/{model_id}/unload  POST
├── /api/v1/predict                  POST (single-image detection)
├── /api/v1/hardware/                GET
├── /api/v1/hardware/{device_id}     GET
├── /api/v1/stream/                  POST (202 + Location, Idempotency-Key) · GET
├── /api/v1/stream/{stream_id}       GET
├── /api/v1/stream/{stream_id}/stop  POST
├── /api/v1/stream/{stream_id}/events GET (text/event-stream SSE)
├── /api/v1/stream/{stream_id}/video GET (multipart/x-mixed-replace MJPEG)
├── /api/v1/stream/{stream_id}/snapshot GET (image/jpeg)
└── /api/v1/stream/{stream_id}/metrics GET

opal-say (openapi/opal_say.yaml)
├── /api/v1/engine/{engine_id}/validate POST
├── /api/v1/voice/                   GET · POST
├── /api/v1/voice/{voice_id}         GET · PATCH · DELETE
├── /api/v1/voice/{voice_id}/validate POST
├── /api/v1/voice/{voice_id}/test    POST (audio/wav | audio/pcm)
├── /api/v1/generate                 POST (audio/wav | audio/pcm + X-Opal-Sample-Rate)
└── /api/v1/generate/stream          POST (progressive audio/pcm s16le mono)

opal-think (openapi/opal_think.yaml)
├── /api/v1/task/                    POST (202 + Location) · GET
├── /api/v1/task/{task_id}           GET
├── /api/v1/task/{task_id}/stream    GET (text/event-stream SSE)
├── /api/v1/task/{task_id}/cancel    POST (202)
├── /api/v1/session/                 POST (201 + Location) · GET
├── /api/v1/session/{session_id}     GET · DELETE
├── /api/v1/model/                   GET
└── /api/v1/model/{model_id}         GET
```

---

## CLI Contract (`x-opal-cli`)

Every operation is annotated with `x-opal-cli` using the structured descriptor defined in `x-opal-cli-format` of [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml):

```yaml
# On a direct operation:
x-opal-cli:
  parent: config      # optional super-group (e.g. config, data)
  group: persona      # optional command group
  command: list       # required canonical kebab-case verb
  aliases: []         # optional alternate complete command spellings

# On a kernel $ref-mounted path item (hoisted onto each method by spec_util.py):
x-opal-cli:
  get:
    parent: config
    group: setting
    command: list
  patch:
    parent: config
    group: setting
    command: update
    aliases:
      - config setting patch
```

Resulting unified `opal` command tree:

```text
opal
├── listen
│   ├── recognition   start | stop | status | stream | test-text | test-audio
│   ├── config        intent | slot | wakeword | regression | persona | profile | setting
│   ├── data          failed-utterance | performance
│   ├── backup        create | list | download | remove | export | import | validate | restore
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready | audio-devices
├── say
│   ├── generate      (text -> WAV/PCM file)
│   ├── stream        (text -> progressive s16le PCM stream)
│   ├── engine        list | show | update | validate
│   ├── config        voice | persona | profile | setting
│   ├── backup        create | list | download | remove | export | import | validate | restore
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready
├── event
│   ├── config        rule | action | topic | persona | profile | setting
│   ├── data          event | execution | stats
│   ├── backup        create | list | download | remove | export | import | validate | restore
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready
├── look
│   ├── engine        list | show | discover | capabilities
│   ├── model         list | show | load | unload
│   ├── predict       image
│   ├── hardware      list | show
│   ├── stream        start | list | show | stop | watch | watch-video | snapshot | metrics
│   ├── config        engine | profile | setting
│   ├── backup        create | list | download | remove | export | import | validate | restore
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready
└── think
    ├── task          create (aliases: ask, chat) | list | show | watch | cancel
    ├── session       add | list | show | remove
    ├── model         list | show
    ├── config        persona | profile | setting
    ├── backup        create | list | download | remove | export | import | validate | restore
    ├── service       start | stop | log
    └── info          version | ping | health | live | ready
```

---

## Requirements

- **Node.js 20+** (CI runs on **Node.js 22**):
  - `@redocly/cli` `2.66.1` (pinned in [`package.json`](package.json))
  - `@stoplight/spectral-cli` `6.17.0` (pinned in [`package.json`](package.json))
- **Python 3.x** (for the contract regression test suite):
  - `PyYAML>=6.0`
  - `jsonschema>=4.21`

---

## Installation

```bash
git clone https://github.com/PatMartin/opal-api.git
cd opal-api

# Install pinned Redocly and Spectral CLIs
npm ci

# Install Python test harness dependencies
python -m pip install -r requirements.txt
```

---

## Quickstart & Usage

### Validate, Lint, Bundle, and Test

Run the entire 14-stage check suite (identical to CI):

```bash
npm run check
```

Or run individual stages while editing a contract:

```bash
# 1. Structural OpenAPI 3.1 validation & $ref resolution
npm run validate

# 2. Lint against OPAL suite conventions
npm run lint:opal
npm run lint:kernel

# 3. Produce self-contained dereferenced specs in dist/
npm run bundle
```

### Load a Resolved Contract in Python

Service specs use external `$ref`s into `openapi/shared/opal_kernel.yaml`. Use [`tests/spec_util.py`](tests/spec_util.py) to load a spec with all kernel and local `$ref`s dereferenced and path-level `x-opal-cli` maps hoisted onto their operations:

```python
from tests import spec_util

think = spec_util.load("openapi/opal_think.yaml")
print(think["info"]["title"], think["info"]["version"])
# -> OPAL Think API 1.7.1

task_post = think["paths"]["/api/v1/task/"]["post"]
print(task_post["x-opal-cli"])
# -> {'group': 'task', 'command': 'create', 'aliases': ['ask', 'chat']}
```

### Example CLI Workflows

From [`docs/COOKBOOK.md`](docs/COOKBOOK.md), which pairs the CLI command trees with 50 end-to-end recipes:

```bash
# Register a persona in Think (authoritative owner), synthesize speech in Say,
# and verify intent matching in Listen:
opal think config persona add \
  --persona-id duchess \
  --name "The Duchess" \
  --voice-id en-gb-alba-medium \
  --enabled

opal say generate \
  --text "Turn on the study lamps" \
  --persona duchess \
  --output /tmp/duchess.wav

opal listen recognition test-audio --file /tmp/duchess.wav
```

---

## Configuration & Rulesets

Validation behavior is controlled by five configuration files in the repository root:

| File | Tool | Purpose & Key Settings |
| --- | --- | --- |
| [`redocly.yaml`](redocly.yaml) | Redocly CLI | Extends `recommended`. Turns off `no-path-trailing-slash` (OPAL requires trailing slashes on collection roots) and `security-defined`; sets `operation-summary` and `no-empty-servers` to `warn`. |
| [`.spectral.yaml`](.spectral.yaml) | Spectral CLI | Base `spectral:oas` recommended ruleset. Disables `path-keys-no-trailing-slash` and `oas3-schema` (Spectral's resolver raises false positives on external path-item `$ref` mounts, which Redocly validates structurally). |
| [`.spectral.opal.yaml`](.spectral.opal.yaml) | Spectral CLI | Suite-wide normative rules: `opal-correlation-headers`, `opal-standard-error-body`, `opal-zeromq-frame-count`, `opal-context-events-compatibility`, `opal-ifmatch-precondition-responses`, `opal-item-op-404`, `opal-201-location-header`, `opal-recognition-stream-sse`, `opal-context-params`, `opal-header-required-ids`, `opal-header-conditional-ids`, `opal-cli-descriptor`, and `opal-cli-method-map`. |
| [`.spectral.opal.look.yaml`](.spectral.opal.look.yaml) | Spectral CLI | Look-specific guarantees: `opal-look-config-ifmatch`, `opal-look-health-probe`, `opal-look-event-contract`, `opal-look-ifmatch-strong-schema`, and header required/conditional checks. |
| [`.spectral.opal.think.yaml`](.spectral.opal.think.yaml) | Spectral CLI | Think-specific guarantees: `opal-think-config-ifmatch`, `opal-think-health-probe`, `opal-think-ifmatch-strong-schema`, and header required/conditional checks. |

---

## Development & Extending Contracts

When adding or modifying routes, schemas, or conventions:

1. **Shared vs. service-local**: If a header, parameter, error response, schema, or route family applies across services, put it in [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) and mount it via `$ref: './shared/opal_kernel.yaml#/components/...'`.
2. **Preserve suite invariants**:
   - Declare all four `Opal*Parameter` correlation headers on the path item and all four `Opal*Header` correlation headers on every response.
   - Include `401` (`Unauthorized`) and `403` (`Forbidden`) on every operation (`tests/test_rest_security.py` asserts 100% coverage across all operations).
   - Include `404` on all parameterized item paths (`{...}`) for `GET`, `POST`, `PATCH`, and `DELETE`.
   - Require `If-Match` (`$ref: './shared/opal_kernel.yaml#/components/parameters/IfMatch'`) and declare `412` + `428` on mutable configuration operations.
   - Include a `Location` header on every `201` response.
   - Add an `x-opal-cli` descriptor to every operation (or a per-method map on `$ref`-mounted path items).
3. **Drafting proposals**: `tests/test_rest_security.py` also checks `openapi/proposals/*.yaml`, and CI runs on `proposal/**` and `integration/**` branches.
4. **Regenerate bundles**: Run `npm run bundle` to verify that Redocly can dereference all external `$ref`s into `dist/opal_*.yaml`.

---

## Testing & Validation Pipeline

Every stage in `npm run check` (and [`.github/workflows/openapi-validate.yml`](.github/workflows/openapi-validate.yml)) runs independently in CI so a failure in one stage never hides findings in another:

| Stage | Script | Command | What It Verifies |
| --- | --- | --- | --- |
| 1 | `npm run validate` | `redocly lint "openapi/*.yaml"` | OpenAPI 3.1.0 structural validity and external `$ref` resolution across all five specs. |
| 2 | `npm run lint` | `spectral lint -r .spectral.yaml "openapi/*.yaml"` | Generic OpenAPI recommended rules. |
| 3 | `npm run lint:opal` | `spectral lint -r .spectral.opal.yaml "openapi/*.yaml"` | OPAL Suite Standard v1.2 rules on all five service contracts. |
| 4 | `npm run lint:kernel` | `spectral lint -r .spectral.opal.yaml openapi/shared/opal_kernel.yaml` | OPAL Suite Standard rules directly against the shared kernel. |
| 5 | `npm run lint:look` | `spectral lint -r .spectral.opal.look.yaml openapi/opal_look.yaml` | Look `If-Match`, health probe `200`/`503`, and `x-opal-event-contract` rules. |
| 6 | `npm run lint:think` | `spectral lint -r .spectral.opal.think.yaml openapi/opal_think.yaml` | Think `If-Match` and health probe `200`/`503` rules. |
| 7 | `npm run bundle` | `redocly bundle openapi/opal_*.yaml -o dist/opal_*.yaml` | All five contracts bundle cleanly into standalone artifacts in `dist/`. |
| 8 | `npm run test:lint` | `python tests/test_lint.py` | Negative tests: mutates specs in temp files and verifies each Spectral rule triggers as expected. |
| 9 | `npm run test:event150` | `python tests/test_event_150.py` | Event `1.7.1` action metadata fields, no duplicate YAML keys, Draft 2020-12 validation against 10 fixtures in `tests/fixtures/event_150/`, `input_validation_failed` semantics, scopes, and settings `If-Match`. |
| 10 | `npm run test:think-event` | `python tests/test_think_event.py` | Think `x-opal-event-integration` matches Event's `think` principal scopes/denials, routes, `202` admission, and execution states. |
| 11 | `npm run test:look-cli` | `python tests/test_look_cli.py` | Every Look operation has a unique `(group, command)` in `x-opal-cli`; kernel mounts, engine discover/capabilities, model load/unload, predict invariants, RTSP-only stream sources, SSE/MJPEG/snapshot/metrics routes, If-Match mutations, item-op 404s, and correlation headers are asserted. |
| 12 | `npm run test:listen150` | `python tests/test_listen_150.py` | Listen `1.7.1` `/api/v1/setting/{key}` GET/PUT/DELETE, collection PATCH, and `backup/import` `If-Match` + `412`/`428` preconditions. |
| 13 | `npm run test:say150` | `python tests/test_say_150.py` | Say `1.7.1` atomic `backup/import` and `backup/restore/{filename}` `If-Match` + `412`/`428` preconditions and `backup/validate`. |
| 14 | `npm run test:rest-security` | `python tests/test_rest_security.py` | Every spec declares `BearerAuth`, top-level security, `x-opal-authorization` semantics, and `401` + `403` on every operation. |

Spectral fails the build on `error` severity; `warn` findings are reported without failing the stage.

---

## Documentation

- [`docs/COOKBOOK.md`](docs/COOKBOOK.md) — **The OPAL CLI Cookbook (v1.7.1)**: complete Typer command trees, REST trees, command references, single-service usage examples, and 50 multi-service recipes across voice testing, perimeter security, education/quizzes, workshop/lab assistants, and accessibility.
- [`docs/create_cli.txt`](docs/create_cli.txt) — prompt specification for generating CLI reference and use-case documentation.
- [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) — normative definitions for `x-opal-authorization`, `x-opal-event-envelope`, `x-opal-cli-format`, and `x-opal-persona` (`profiles_vs_personas`).
- Per-service normative architecture and behavioral guarantees live in the `info.description` block at the top of each file in [`openapi/`](openapi/).

---

## Contributing

1. Create a branch following the workflow triggers in [`.github/workflows/openapi-validate.yml`](.github/workflows/openapi-validate.yml):
   - `proposal/<topic>` for new or experimental contract proposals
   - `integration/<topic>` for cross-service contract alignment
2. Make your changes in [`openapi/`](openapi/), update or add corresponding assertions in [`tests/`](tests/), and bump `info.version` across affected contracts when publishing a new revision.
3. Run the full verification suite locally before opening a pull request:
   ```bash
   npm run check
   ```
4. Report issues at <https://github.com/PatMartin/opal-api/issues>.

---

## License

The repository tooling in [`package.json`](package.json) is licensed under the **ISC** license; individual OpenAPI specifications declare `Internal use` in `info.license`.
