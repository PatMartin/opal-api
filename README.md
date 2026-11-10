# opal-api

Published OpenAPI 3.1 contracts for the OPAL suite — one file per service in
[`openapi/`](openapi/), all built on a shared kernel contract
[`openapi/shared/opal_kernel.yaml`](openapi/shared/opal_kernel.yaml).

| File | Service | Version |
| --- | --- | --- |
| `openapi/opal_event.yaml` | OPAL Event API (publication, rules, actions, executions) | 1.7.0 |
| `openapi/opal_listen.yaml` | OPAL Listen API (speech recognition, intents, wakewords) | 1.7.0 |
| `openapi/opal_look.yaml` | OPAL Look API (vision sources, pipelines, sessions, media) | 1.7.0 |
| `openapi/opal_say.yaml` | OPAL Say API (TTS engines, voices, generation, streaming) | 1.7.0 |
| `openapi/opal_think.yaml` | OPAL Think API (durable reasoning tasks, sessions, models) | 1.7.0 |
| `openapi/shared/opal_kernel.yaml` | Shared kernel: headers, parameters, errors, mounted pathItems, common schemas | 1.7.0 |

## Contract conventions

- **Singular resource routes** — `/api/v1/voice/`, `/api/v1/task/`,
  `/api/v1/rule/`.
- **Correlation headers** — every operation accepts `X-Opal-Session-Id`,
  `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, `X-Opal-Causation-Id`.
- **Strong concurrency** — configuration mutations declare `If-Match`, return
  ETags, and document 428 (missing) / 412 (stale) / 422 where applicable.
- **Standard errors** — `OpalError` envelope on 4xx/5xx.
- **Service identity** — every service mounts `/api/v1/info/` +
  `/api/v1/info/ping` and `/api/v1/health/` + `/health/live|ready`.
- **Personas** — `/api/v1/persona/` CRUD + validate in all five services.
- **CLI metadata** — `x-opal-cli` group/command/parent annotations drive the
  CLI command surface (look: `{parent, group, command}` objects; think:
  `'group command'` strings).

## REST tree

Shared kernel mounts — identical in all five services:

```
/api/v1
├── backup/list  GET · backup/create  POST · backup/download/{fn}  GET
├── backup/restore/{fn}  POST · backup/{filename}  DELETE
├── backup/export  GET · backup/import  POST · backup/validate  POST
├── info/  GET · info/ping  GET
├── health/  GET · health/live  GET · health/ready  GET
├── profile/  GET/POST · profile/{id}  GET/PATCH/DELETE
│   └── profile/{id}/activate  POST
├── persona/  GET/POST · persona/{id}  GET/PATCH/DELETE
│   └── persona/{id}/validate  POST
├── service/start  POST · service/stop  POST · service/log  GET
└── setting/  GET/PATCH · setting/{key}  GET/PUT/DELETE
    (engine/ + engine/{id} GET — say and look only)
```

Service-specific routes:

```
listen
├── recognition/start|stop  POST · recognition/status  GET
│   ├── recognition/stream  GET · recognition/test_text|test_audio  POST
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
├── generate  POST · generate/stream  POST
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
├── source/  GET/POST · source/{id}  GET/PATCH/DELETE
│   └── /status GET · /probe POST · /frame GET · /capture/ POST · /stream GET
├── model/ · pipeline/ · zone/ · rule/ · monitor/   GET/POST + {id} GET/PATCH/DELETE
│   └── pipeline/validate  POST
├── session/  POST/GET · session/{id}  GET
│   └── /stop POST · /stream GET · /preview GET
├── job/  POST/GET · job/{id}  GET · job/{id}/cancel  POST
├── observation/  GET · observation/{id}  GET
├── media/  POST/GET · media/{id}  GET/DELETE
├── capture/|artifact/  GET · {id}  GET/DELETE · {id}/content  GET
├── recording/  POST/GET · recording/{id}  GET · /stop  POST
├── analyze/  POST · analyze/image  POST
└── capabilities/ · metrics/ · events/status   GET

think
├── task/  POST/GET · task/{id}  GET · /cancel  POST · /stream  GET
├── session/  POST/GET · session/{id}  GET/DELETE
└── model/  GET · model/{id}  GET
```

## Command tree

```
opal
├── listen
│   ├── recognition   start | stop | status | stream | test-text | test-audio
│   ├── config        intent | slot | wakeword | regression | persona | profile | setting
│   ├── data          failed-utterance | performance
│   ├── backup        create | list | download | remove | export | import | validate | restore
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready | audio-devices
│
├── say
│   ├── generate      (text → WAV file)
│   ├── stream        (text → PCM stream)
│   ├── config        voice | persona | profile | setting
│   ├── engine        list | show
│   ├── backup        ...
│   ├── service       start | stop | log
│   └── info          ...
│
├── event
│   ├── config        rule | action | topic | persona | profile | setting
│   ├── data          event | execution | stats
│   ├── backup        ...
│   ├── service       start | stop | log
│   └── info          ...
│
├── look                                   (fully annotated in spec)
│   ├── source        list | add | show | update | remove | status | probe | frame | capture | stream
│   ├── session       start | list | show | stop | stream | preview
│   ├── analyze       run | image
│   ├── config        model | pipeline | zone | rule | monitor | persona | profile | setting
│   ├── data          observation | media | capture | artifact | recording | job
│   ├── engine        list | show
│   ├── backup        ...
│   ├── service       start | stop | log
│   └── info          version | ping | health | live | ready | capabilities | metrics | events
│
└── think                                  (annotated in spec)
    ├── task          create (ask/chat) | list | show | watch | cancel
    ├── session       add | list | show | remove
    ├── model         list | show
    ├── config        persona | profile | setting
    ├── backup        ...
    ├── service       start | stop | log
    └── info          ...
```

`backup`, `persona`, `profile`, `setting`, `service`, and `info` are uniform
across all five services; `engine` exists on say + look only. `service start`
launches the server in the background (output to `logs/opal_<service>.log`,
overwritten by default, any running instance killed first), `service stop`
halts it, and `service log` tails the last 10 lines.

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

Spectral fails the build on `error` severity; `warn`-level findings are
reported but non-blocking.
