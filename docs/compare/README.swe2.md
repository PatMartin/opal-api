# opal-api

[![Validate OpenAPI contracts](https://github.com/PatMartin/opal-api/actions/workflows/openapi-validate.yml/badge.svg)](https://github.com/PatMartin/opal-api/actions/workflows/openapi-validate.yml)

Published OpenAPI 3.1 contracts for the OPAL suite — a family of five
cooperating local services for vision, speech, reasoning, events, and
voice output. This repository contains **contracts and validation
tooling only**; service implementations live elsewhere and consume these
documents as their normative REST interface.

## Contents

- [What is OPAL?](#what-is-opal)
- [The contracts](#the-contracts)
- [Repository layout](#repository-layout)
- [Shared conventions (the kernel)](#shared-conventions-the-kernel)
- [How the services fit together](#how-the-services-fit-together)
- [REST tree](#rest-tree)
- [CLI contract](#cli-contract)
- [Requirements](#requirements)
- [Getting started](#getting-started)
- [Validation pipeline](#validation-pipeline)
- [Changing a contract](#changing-a-contract)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## What is OPAL?

OPAL is a suite of five loopback-first microservices that see, hear,
reason, react, and speak on a local machine:

- **OPAL Look** — visual observation: optional detection engines,
  engine-owned models, single-image prediction, and ephemeral RTSP
  streams with SSE metadata, MJPEG video, snapshots, and metrics.
- **OPAL Listen** — speech pipeline: wakewords, STT, intent recognition,
  slot extraction, regression tests, failed-utterance review.
- **OPAL Think** — durable reasoning tasks with bounded steps; invokes
  tools only through OPAL Event's registered actions.
- **OPAL Event** — a ZeroMQ-based event bus with REST ingress, topic
  rules, and guarded shell/HTTP/python action execution.
- **OPAL Say** — text-to-speech over host-installed engines (Piper,
  Kokoro, …), voices, personas, profiles, generation and PCM streaming.

The contracts here are written API-first: the OpenAPI documents are the
source of truth for service behavior, and the generated Typer CLI and
SPA clients call only the public REST surface described by them.

## The contracts

One file per service in [`openapi/`](openapi/), all built on the shared
kernel contract [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml).
Published single-file artifacts are produced by `npm run bundle` into
`dist/` (gitignored build output).

| File | Service | Contract version |
| --- | --- | --- |
| [`openapi/opal_event.yaml`](openapi/opal_event.yaml) | OPAL Event — event publication, topics, rules, actions, executions, stats | 1.7.1 |
| [`openapi/opal_listen.yaml`](openapi/opal_listen.yaml) | OPAL Listen — speech recognition, intents, slots, wakewords, regression, performance | 1.7.1 |
| [`openapi/opal_look.yaml`](openapi/opal_look.yaml) | OPAL Look — engines, models, predict, hardware, RTSP streams | 1.7.1 |
| [`openapi/opal_say.yaml`](openapi/opal_say.yaml) | OPAL Say — TTS engines, voices, personas, generation, streaming | 1.7.1 |
| [`openapi/opal_think.yaml`](openapi/opal_think.yaml) | OPAL Think — durable reasoning tasks, sessions, model discovery | 1.7.1 |
| [`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml) | Shared kernel: headers, parameters, error responses, mounted pathItems, common schemas | 1.7.1 |

## Repository layout

```
opal-api/
├── openapi/                     # the published contracts
│   ├── opal_event.yaml
│   ├── opal_listen.yaml
│   ├── opal_look.yaml
│   ├── opal_say.yaml
│   ├── opal_think.yaml
│   └── shared/
│       └── opal_kernel.yaml     # shared components + reusable Path Items (never served standalone)
├── tests/                       # Python contract tests
│   ├── spec_util.py             # loads a spec with kernel $refs fully resolved
│   ├── test_*.py                # contract assertions per service/feature
│   └── fixtures/                # deliberately invalid/legacy payloads for regression tests
├── docs/
│   ├── COOKBOOK.md              # the OPAL CLI cookbook: command trees + 50 cross-service recipes
│   └── create_cli.txt           # prompt spec used to generate the CLI docs
├── resources/prompts/           # reusable prompts for doc generation
├── dist/                        # bundled self-contained specs (gitignored output)
├── package.json                 # all validation entry points (npm run check)
├── requirements.txt             # PyYAML + jsonschema for the Python test harness
├── redocly.yaml                 # generic OpenAPI structural lint config
├── .spectral.yaml               # generic Spectral ruleset (base OAS rules)
├── .spectral.opal.yaml          # OPAL suite conventions, applied to every spec + the kernel
├── .spectral.opal.look.yaml     # Look-specific contract guarantees
├── .spectral.opal.think.yaml    # Think-specific contract guarantees
└── .github/workflows/
    └── openapi-validate.yml     # CI: runs every check stage, aggregates results
```

## Shared conventions (the kernel)

Every service spec mounts the kernel's Path Items via external `$ref`
and references its components. The kernel encodes **OPAL SUITE STANDARD
v1.2**:

- **Routing** — `/api/v1` namespace, singular resource names, trailing
  slash on collection roots (`/api/v1/voice/`).
- **Correlation headers** — every operation accepts and returns
  `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`,
  `X-Opal-Causation-Id`. Opaque 1–128 printable-ASCII tokens; transport
  context only, never authorization credentials. Transaction and request
  IDs are always returned; session and causation are conditional.
- **Strong concurrency** — mutable configuration carries one strong
  ETag; mutations require `If-Match`: 428 missing, 412 stale, 422
  malformed (weak tags, lists, `*` rejected).
- **Status vocabulary** — 201 + `Location` for creation, 202 +
  `Location` for asynchronous admission, 204 for empty deletion,
  `OpalError` envelope on all 4xx/5xx, 401 missing/invalid credentials,
  403 authenticated-but-not-permitted, 404 on item operations.
- **Uniform route families** — identical in all five services:
  `info/` + `info/ping`, `health/` + `health/live` + `health/ready`,
  `setting/` map + per-key, `backup/` (list, create, download, delete,
  export, import, restore, validate), `profile/` CRUD + activate,
  `service/start|stop|log`. `persona/` CRUD + validate is mounted
  everywhere except Look, which excludes personas in its MVP Plus scope.
  `engine/` exists on Say and Look only.
- **Personas** — a portable identity with optional per-service bindings
  (`x-opal-persona`). OPAL Think is the authoritative writer; every
  service keeps full local CRUD and may cache owner records
  (`origin: local|owner`). Resolution order: explicit request field >
  persona binding > active profile > service default.
- **Events** — `x-opal-event-envelope`: exactly two ZeroMQ frames
  (topic + JSON envelope), correlation IDs propagated under
  `data.metadata`; consumers must ignore unknown metadata fields.
- **Authorization** — `x-opal-authorization`: BearerAuth optional on
  loopback, required on non-loopback; secrets never appear in
  responses, exports, or error details.

## How the services fit together

The designed dataflow is a loop through the bus:

```
listen (intent match) ──┐
                        ├──> event (ZeroMQ topics, rules)
                        │        │
                        │        v
                        │   actions: shell / http / python
                        │        │
                        v        v
say (spoken output) <── think (reasoning tasks, execute-only principal)
```

- **Event** is the execution and authorization authority. It owns action
  definitions, dispatch, limits, and execution records. 202 means
  admission, not execution; terminal states are
  `succeeded | failed | timed_out | dropped`.
- **Think** discovers enabled Event actions and invokes them under a
  least-privilege principal (`actions:read`, `actions:execute`,
  `executions:read`; denied `actions:write`, `rules:write`,
  `settings:write`). Think never executes model-generated shell, URLs,
  or code directly — tools exist only through Event.
- **Listen** publishes `opal.listen.intent.match` when
  `event_publication_enabled` is true; mic matches only — diagnostic
  text/audio sources never publish externally.
- **Look** publishes no bus events; stream metadata and detections are
  per-stream SSE (`GET /api/v1/stream/{id}/events`) that a client may
  republish to Event.
- **Say** supplies voices bound to shared personas; `persona` on a
  generation request resolves voice through the persona.

These guarantees are enforced in the repo, not just documented:
[`tests/test_think_event.py`](tests/test_think_event.py) pins the
Think↔Event boundary and [`tests/test_rest_security.py`](tests/test_rest_security.py)
asserts 401/403 on every operation plus the declared semantics.

## REST tree

Shared kernel mounts — identical in all five services:

```
/api/v1
├── backup/list  GET · backup/create  POST · backup/download/{fn}  GET
├── backup/restore/{fn}  POST · backup/{filename}  DELETE
├── backup/export  GET · backup/import  POST · backup/validate  POST|GET
├── info/  GET · info/ping  GET
├── health/  GET · health/live  GET · health/ready  GET
├── profile/  GET/POST · profile/{id}  GET/PATCH/DELETE
│   └── profile/{id}/activate  POST
├── persona/  GET/POST · persona/{id}  GET/PATCH/DELETE
│   └── persona/{id}/validate  POST      (not on look)
├── service/start  POST · service/stop  POST · service/log  GET
└── setting/  GET/PATCH · setting/{key}  GET/PUT/DELETE
    (engine/ + engine/{id} GET/PATCH — say and look only)
```

Service-specific routes:

```
listen
├── recognition/start|stop  POST · recognition/status  GET
│   ├── recognition/stream  GET (SSE) · test_text|test_audio  POST
├── intent/  GET/POST · intent/{id}  GET/PATCH/DELETE
│   └── intent/{id}/phrase  GET/POST · phrase/{pid}  DELETE
├── slot/  GET/POST · slot/{id}  GET/PATCH/DELETE
│   └── slot/{id}/value  GET/POST · value/{vid}  DELETE
│       └── value/{vid}/alias  GET/POST · alias/{aid}  DELETE
├── wakeword/  GET/POST · wakeword/{id}  GET/PATCH/DELETE
├── regression/  GET/POST · regression/run  POST
│   └── regression/{id}  GET/PATCH/DELETE
├── failed_utterance/  GET/POST · failed_utterance/{id}  GET/PATCH/DELETE
│   └── failed_utterance/{id}/promote  POST
├── performance/summary|last|history  GET
└── health/audio_devices  GET

say
├── generate  POST · generate/stream  POST (raw s16le PCM)
├── voice/  GET/POST · voice/{id}  GET/PATCH/DELETE
│   └── voice/{id}/test|validate  POST
└── engine/{id}/validate  POST

event
├── event/  POST/GET/DELETE · event/{id}  GET/DELETE   (publish + history)
├── topic/  GET
├── rule/  GET/POST · rule/{id}  GET/PATCH/DELETE · rule/{id}/test  POST
├── action/  GET/POST · action/{id}  GET/PATCH/DELETE
│   └── action/{id}/execute  POST
├── execution/  GET · execution/{id}  GET
└── stats/  GET

look
├── engine/discover  POST · engine/{id}/capabilities  GET
├── model/  GET · model/{id}  GET · model/{id}/load|unload  POST
├── predict  POST (single-image detection)
├── hardware/  GET · hardware/{device_id}  GET
└── stream/  POST/GET · stream/{id}  GET · /stop  POST
    └── /events GET (SSE) · /video GET (MJPEG) · /snapshot GET · /metrics GET

think
├── task/  POST/GET · task/{id}  GET · /cancel  POST · /stream  GET (SSE)
├── session/  POST/GET · session/{id}  GET/DELETE
└── model/  GET · model/{id}  GET
```

## CLI contract

Every operation carries an `x-opal-cli` descriptor
(`{command, group?, parent?, aliases?}`) that binds it to a canonical
`opal <service> [parent] [group] <command>` spelling. The format is
defined by kernel extension `x-opal-cli-format` and enforced by the
`opal-cli-descriptor` / `opal-cli-method-map` Spectral rules.
Kernel-mounted paths carry a per-method map `{<method>: <descriptor>}`
because extensions cannot inject into `$ref`ed operations.

Canonical verbs: `list | add | show | update | remove` for resource CRUD;
explicit operational verbs (`generate`, `stream`, `start`, `stop`,
`validate`, `activate`, `watch`, `cancel`, `probe`, `capture`,
`execute`, …) elsewhere. Standardized groups: `config` (mutable
configuration), `data` (runtime artifacts/history), `info` (probes and
telemetry), `service` (daemon lifecycle), `backup` (snapshots and
portable configuration).

```
opal
├── listen   recognition · config (intent|slot|wakeword|regression|persona|profile|setting)
│            data (failed-utterance|performance) · backup · service · info
├── say      generate · stream · engine · config (voice|persona|profile|setting)
│            backup · service · info
├── event    config (rule|action|topic|persona|profile|setting)
│            data (event|execution|stats) · backup · service · info
├── look     engine · model · predict · hardware · stream
│            config (engine|profile|setting)
│            backup · service · info
└── think    task (create with ask/chat aliases) · session · model
             config (persona|profile|setting) · backup · service · info
```

## Requirements

- **Node.js 20+** (CI uses Node 22) — Redocly CLI 2.66.1 and Spectral
  CLI 6.17.0, pinned in `package.json` / `package-lock.json`.
- **Python 3** — for the contract test harness (`PyYAML>=6.0`,
  `jsonschema>=4.21` in [`requirements.txt`](requirements.txt)).

## Getting started

```bash
git clone https://github.com/PatMartin/opal-api.git
cd opal-api
npm ci                                    # pinned lint/validation tools
python -m pip install -r requirements.txt # test harness deps
npm run check                             # the full pipeline, same as CI
```

Useful one-off commands:

```bash
npm run bundle      # dereference each spec into a self-contained dist/*.yaml
npm run validate    # redocly lint: parse + $ref resolution + OAS 3.1
npm run lint:opal   # OPAL suite conventions on all five specs
```

## Validation pipeline

`npm run check` runs every stage in order — identical to the
`openapi-validate` CI workflow:

| Command | What it proves |
| --- | --- |
| `npm run validate` | Redocly structural validation and `$ref` resolution for `openapi/*.yaml` |
| `npm run lint` | Generic OAS rules (`.spectral.yaml`) |
| `npm run lint:opal` | Suite conventions on the five specs (`.spectral.opal.yaml`) |
| `npm run lint:kernel` | Suite conventions on the kernel document |
| `npm run lint:look` | Look-specific guarantees (`.spectral.opal.look.yaml`) |
| `npm run lint:think` | Think-specific guarantees (`.spectral.opal.think.yaml`) |
| `npm run bundle` | Every spec dereferences into a self-contained document for consumers |
| `npm run test:lint` | Spectral rules actually fire on deliberately mutated specs |
| `npm run test:event150` | Event contract assertions (rules, actions, fixtures) |
| `npm run test:think-event` | Think↔Event integration boundary and scoped principal |
| `npm run test:look-cli` | `x-opal-cli` metadata coverage on the Look contract |
| `npm run test:listen150` | Listen contract assertions |
| `npm run test:say150` | Say contract assertions |
| `npm run test:rest-security` | BearerAuth on every spec, 401/403 on every operation, declared semantics |

Spectral fails the build on `error` severity; `warn` findings are
reported but non-blocking. The Python tests load specs through
[`tests/spec_util.py`](tests/spec_util.py), which resolves kernel
`$ref`s so assertions run against the effective bundled contract.

## Changing a contract

1. Edit the service spec — or the kernel for anything shared. Service
   specs mount kernel Path Items via
   `$ref: './shared/opal_kernel.yaml#/components/pathItems/<name>'` and
   reference kernel components the same way.
2. Keep the suite conventions or lint will fail: four correlation
   headers on every operation and response, `OpalError` bodies on
   4xx/5xx, `If-Match` + 412/428 on configuration mutations, `Location`
   on every 201, 404 on item operations, `x-opal-cli` descriptor on
   every operation.
3. If the change is contract-significant, extend the matching Python
   test under `tests/` and add fixtures under `tests/fixtures/` for new
   acceptance shapes.
4. Run `npm run check` locally — it is exactly what CI runs. The
   workflow triggers on `main`, `integration/**`, and `proposal/**`
   branches, so push contract proposals on a `proposal/<name>` branch.

Two lint quirks, documented in the rulesets: the trailing-slash
convention disables `no-path-trailing-slash` /
`path-keys-no-trailing-slash`, and `oas3-schema` is off because the
Spectral resolver mishandles external path-item `$ref` mounts (Redocly
validates them structurally instead).

## Documentation

- [`docs/COOKBOOK.md`](docs/COOKBOOK.md) — the OPAL CLI cookbook
  (v1.7.1): per-service command trees, REST trees, command references,
  and 50 cross-service recipes.
- [`docs/create_cli.txt`](docs/create_cli.txt) — prompt spec used to
  generate the CLI documentation set.
- Spec `info.description` blocks — normative per-service prose: event
  templating/execution rules, listen's recognition pipeline guarantees,
  look's stream/detection invariants, think's ratified architecture
  decisions, say's engine/voice contract.
- Kernel extensions — `x-opal-authorization`, `x-opal-event-envelope`,
  `x-opal-cli-format`, `x-opal-persona` define suite-wide semantics.

## Contributing

- Branch naming follows the CI triggers: `proposal/<slug>` for contract
  proposals, `integration/<slug>` for staged contract work.
- `tests/test_rest_security.py` also globs `openapi/proposals/*.yaml`,
  so in-progress contract drafts can live under `openapi/proposals/`
  and are held to the same security assertions.
- Before pushing, run `npm run check` — CI runs the identical stage
  list and fails on any stage.
- Contract versions move together: bump `info.version` in the service
  spec (and the kernel when shared semantics change) rather than
  silently editing behavior.

## License

Spec `info.license` fields declare "Internal use". The npm manifest
declares ISC for this repository's tooling.
