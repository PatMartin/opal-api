# opal-api

Published OpenAPI 3.1 contracts for the OPAL suite — one file per service in
[`openapi/`](openapi/), all built on a shared kernel contract
[`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml).

| File | Service | Version |
| --- | --- | --- |
| `openapi/opal_event.yaml` | OPAL Event API (publication, rules, actions, executions) | 1.6.0 |
| `openapi/opal_listen.yaml` | OPAL Listen API (speech recognition, intents, wakewords) | 1.6.0 |
| `openapi/opal_say.yaml` | OPAL Say API (TTS engines, voices, generation, streaming) | 1.6.0 |
| `openapi/opal_look.yaml` | OPAL Look API (vision sources, pipelines, sessions, media) | 1.6.0 |
| `openapi/opal_think.yaml` | OPAL Think API (durable reasoning tasks, sessions, models) | 1.6.0 |
| `openapi/shared/opal_kernel.yaml` | Shared kernel: headers, parameters, errors, mounted pathItems, common schemas | 1.6.0 |

## Contract conventions

- **Singular resource routes** — `/api/v1/voice/`, `/api/v1/task/`,
  `/api/v1/rule/` (v1.6.0 convention, matching `opal_say`).
- **Correlation headers** — every operation accepts `X-Opal-Session-Id`,
  `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, `X-Opal-Causation-Id`; these are
  transport context, not credentials.
- **Strong concurrency** — configuration mutations declare `If-Match`
  (`#/components/parameters/IfMatch`), return ETags, and document 428 (missing),
  412 (stale), and 422 where applicable.
- **Standard errors** — `OpalError` envelope on 4xx/5xx.
- **Service identity** — every service mounts `/api/v1/info/` and
  `/api/v1/info/ping` (kernel `ServiceInfo`/`LivenessRead`), plus
  `/api/v1/health/` and `/health/live|ready`.
- **Personas** — `/api/v1/persona/` CRUD + validate in all five services
  (named identities; `voice_id` optional outside Say).
- **CLI metadata** — `x-opal-cli` group/command annotations drive the CLI
  command surface (Look uses `group:`/`command:` objects; Think uses strings).

## Docs

[`docs/`](docs/) holds runnable CLI cookbooks: `COOKBOOK.md` (50 recipes),
`CLI_USECASES.md` (single-interface + 50 cross-interface recipes), and themed
multi-interface collections (`EDUCATION.md`, `HOME_AUTOMATION.md`,
`ACCESSIBILITY.md`, `PROPERTY_MONITORING.md`, `PET_CARE.md`,
`VOICE_ASSISTANT.md`, `SHOPPING.md`, `COMPUTER_TRIAGE.md`, `STARGAZING.md`).

## Validating the contracts

All checks run via `npm run check`.

### Prerequisites

- Node.js 20+ (CI uses Node 22)
- `npm ci` to install the pinned tool versions

### Commands

```bash
npm run validate       # Redocly structural validation + $ref resolution
npm run lint           # generic Spectral rules (.spectral.yaml)
npm run lint:opal      # OPAL suite conventions (.spectral.opal.yaml)
npm run lint:kernel    # suite conventions against the kernel
npm run lint:look      # Look-specific guarantees (.spectral.opal.look.yaml)
npm run lint:think     # Think-specific guarantees (.spectral.opal.think.yaml)
npm run bundle         # dereferenced bundles to dist/
npm run test:lint      # regression fixtures for the Spectral rules
npm run test:event150  # event contract assertions
npm run test:think-event  # think<->event integration routes
npm run test:look-cli  # x-opal-cli metadata coverage
npm run test:listen150 # listen contract assertions
npm run test:say150    # say contract assertions
npm run test:rest-security  # auth/scope/concurrency semantics
npm run check          # everything above, same as CI
```

### What is checked

- OpenAPI 3.1 parsing and structural validity (Redocly `recommended` ruleset)
- Local `$ref` resolution — both tools fail on unresolved references
- Duplicate `operationId`s, path/parameter consistency, valid examples
- OPAL suite conventions: correlation params, error envelope, ETag/precondition
  declarations, 201 Location, item-op 404s
- Look-specific guarantees: `x-opal-cli` on every operation, mandatory
  `If-Match` on configuration mutations, cursor-page structure, health-probe
  bodies
- Contract regression tests in `tests/` for each service

Spectral fails the build on `error` severity; `warn`-level findings are
reported but non-blocking.
