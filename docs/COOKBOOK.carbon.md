# The OPAL Ecosystem Cookbook

*170 copy-pasteable recipes for five cooperating services — ears that listen, eyes that watch, a brain that reasons, a mouth that speaks, and an event bus that keeps them all honest.*

This cookbook is a practical field guide to the unified `opal` [Typer](https://typer.tiangolo.com/) command-line interface implied by the OpenAPI 3.1 contracts in [`openapi/`](../openapi/), the standalone YOLO inference adapter in [`openapi/engines/opal_look_yolo.yaml`](../openapi/engines/opal_look_yolo.yaml), and the shared contract kernel in [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml).

> **Contract-first note:** This repository defines and validates the HTTP and event contracts (`v5.0.0`); it does not ship a running daemon or an `opal` binary. Every command in this book maps directly to a public REST operation in those specifications, with a thin layer of documented client-side ergonomics (`--play`, `--wait`, `--out`, `-`, and `@file`). Every fenced code block renders with a one-click copy button in GitHub, VS Code, and Markdown viewers.

---

## Contents

- [Introduction](#introduction)
  - [The Five Faculties (Plus an Engine Adapter)](#the-five-faculties-plus-an-engine-adapter)
  - [Shared Kernel Rules That Bind the Suite](#shared-kernel-rules-that-bind-the-suite)
  - [Profiles vs. Personas](#profiles-vs-personas)
  - [CLI Conventions and Ergonomics](#cli-conventions-and-ergonomics)
- [CLI Command Tree](#cli-command-tree)
- [EVENT FLOW](#event-flow)
  - [Topic, Stream, and Action Topology](#topic-stream-and-action-topology)
  - [Transport and Guarantee Matrix](#transport-and-guarantee-matrix)
- [Recipes](#recipes)
  - [Single-Service One-Liners](#single-service-one-liners)
    - [opal say (24 progressive one-liners)](#opal-say)
    - [opal listen (24 progressive one-liners)](#opal-listen)
    - [opal look (24 progressive one-liners)](#opal-look)
    - [opal think (24 progressive one-liners)](#opal-think)
    - [opal event (24 progressive one-liners)](#opal-event)
  - [combined (50 Multi-Service Recipes)](#combined)
    - [Once-Per-Host Plumbing](#once-per-host-plumbing)
    - [1–8: Core Classics & Desktop Control](#core-classics-and-desktop-control)
      - [1. Setting up a camera to use YOLO for detection](#recipe-1)
      - [2. Ask an AI a question — and hear the answer](#recipe-2)
      - [3. Launch bashtop by voice command](#recipe-3)
      - [4. Shutdown your computer by voice](#recipe-4)
      - [5. Setting up a persona across the suite](#recipe-5)
      - [6. Full-duplex voice assistant](#recipe-6)
      - [7. One portable profile across Say and Listen](#recipe-7)
      - [8. Streaming LLM tokens into incremental TTS](#recipe-8)
    - [9–16: Voice Lab & Audio Tricks](#voice-lab-and-audio-tricks)
      - [9. Soundoff — opal say says hello in every voice it has](#recipe-9)
      - [10. Voice roulette — user says something, computer says it back in a random voice](#recipe-10)
      - [11. Voice lab: one trigger phrase across every persona](#recipe-11)
      - [12. Voice lab: espresso speed sweep](#recipe-12)
      - [13. Paraphrase and speak](#recipe-13)
      - [14. Paraphrase factory for intent training](#recipe-14)
      - [15. The miss whisperer: LLM triage for failed utterances](#recipe-15)
      - [16. Spoken NLU regression report](#recipe-16)
    - [17–26: Eyes on the Property](#eyes-on-the-property)
      - [17. Notify me when you see a target](#recipe-17)
      - [18. Tell me when there is a package on the porch](#recipe-18)
      - [19. "Who is at the front door?"](#recipe-19)
      - [20. Polite porch greeter with evidence snapshot](#recipe-20)
      - [21. "Off the couch, Biscuit!" — dynamic pet scolder](#recipe-21)
      - [22. Driveway capacity counter](#recipe-22)
      - [23. Camera-down watchdog](#recipe-23)
      - [24. Voice-triggered photo booth ("Say cheese")](#recipe-24)
      - [25. Nightly front-yard visitor digest](#recipe-25)
      - [26. Workshop safety-glasses officer](#recipe-26)
    - [27–36: Classroom, Games & Storytelling](#classroom-games-and-storytelling)
      - [27. Make up a story about...](#recipe-27)
      - [28. Hands-free story time on any spoken topic](#recipe-28)
      - [29. Spelling Bee](#recipe-29)
      - [30. Verbal pub-quiz with session scorekeeping](#recipe-30)
      - [31. Timed multiplication drill with event timestamps](#recipe-31)
      - [32. Socratic word-problem math tutor](#recipe-32)
      - [33. Foreign-language pronunciation coach](#recipe-33)
      - [34. Spoken Twenty Questions](#recipe-34)
      - [35. Tabletop RPG Dungeon Master](#recipe-35)
      - [36. Homework helper that hints without spoiling](#recipe-36)
    - [37–43: Smart Home & Ambient Automation](#smart-home-and-ambient-automation)
      - [37. Room-aware lights with spoken confirmation](#recipe-37)
      - [38. Smart doorbell with snapshot and chime](#recipe-38)
      - [39. Thirsty-garden soil sensor narrator](#recipe-39)
      - [40. Water-leak alarm and insurance snapshot](#recipe-40)
      - [41. Household dinner bell](#recipe-41)
      - [42. Morning porch and day-ahead briefing](#recipe-42)
      - [43. Synchronized goodnight mode](#recipe-43)
    - [44–50: Developer Workflow & Fleet Operations](#developer-workflow-and-fleet-operations)
      - [44. Speaking CI/CD build announcer](#recipe-44)
      - [45. Automated log triage across services](#recipe-45)
      - [46. Post-mortem diagnosis on a failed execution](#recipe-46)
      - [47. Desk guardian: alert if your laptop leaves without you](#recipe-47)
      - [48. Start all services](#recipe-48)
      - [49. Backup everything](#recipe-49)
      - [50. Graceful fleet shutdown with audit marker](#recipe-50)

---

## Introduction

OPAL decomposes an intelligent local assistant into **five independent HTTP microservices** plus pluggable inference adapters. Rather than bundling speech-to-text, computer vision, LLM reasoning, text-to-speech, and shell execution into one privileged monolith, OPAL gives each faculty its own process, configuration snapshot, health report, and security boundary.

### The Five Faculties (Plus an Engine Adapter)

| CLI Root | Contract | Default Example Port | Faculty & Boundary |
| --- | --- | --- | --- |
| `opal listen` | [`openapi/opal_listen.yaml`](../openapi/opal_listen.yaml) | `localhost:8000` | **Hearing.** Wakewords, speech-to-text (with optional async second-pass refinement), intent classification, slot/alias extraction, failed-utterance triage, and NLU regression tests. Optionally publishes live microphone matches. |
| `opal look` | [`openapi/opal_look.yaml`](../openapi/opal_look.yaml) | `127.0.0.1:8082` | **Sight.** Ephemeral RTSP streams (plain video works with zero AI engines installed), optional discoverable detection engines (YOLO, RF-DETR, RT-DETR, D-FINE), engine-owned models, single-image prediction, SSE metadata/detections, MJPEG viewing, and JPEG snapshots. |
| `opal look-yolo` | [`openapi/engines/opal_look_yolo.yaml`](../openapi/engines/opal_look_yolo.yaml) | `127.0.0.1:8086` | **Detection Adapter.** Standalone Ultralytics YOLO adapter owning local model weights, GPU/CPU discovery, and frame/image inference behind Look. |
| `opal think` | [`openapi/opal_think.yaml`](../openapi/opal_think.yaml) | `127.0.0.1:8083` * | **Reasoning.** Model-neutral asynchronous tasks and optional multi-turn sessions. Never runs arbitrary shell/Python/HTTP directly; instead discovers and invokes permitted actions registered in Event. Hosts the authoritative persona registry. |
| `opal say` | [`openapi/opal_say.yaml`](../openapi/opal_say.yaml) | `127.0.0.1:8081` * | **Voice.** Text-to-speech over host-installed engines (such as Piper or Kokoro). Returns completed WAV/PCM bytes or progressive/incremental raw `s16le` mono PCM streams. Never downloads models and never plays audio on hardware itself. |
| `opal event` | [`openapi/opal_event.yaml`](../openapi/opal_event.yaml) | `127.0.0.1:8080` | **Nervous System.** HTTP and ZeroMQ event ingress, bounded history, stateless topic/condition rules, registered `shell` / `http` / `python` actions with optional JSON Schema input validation, and execution audit records. |

*\* Event, Say, and Think all use `127.0.0.1:8080` as an illustrative placeholder in their individual specs. When running the full suite on one host, this cookbook assigns Event `8080`, Say `8081`, Look `8082`, Think `8083`, Look-YOLO `8086`, and Listen `8000`.*

### Shared Kernel Rules That Bind the Suite

Every module mounts shared Path Items and schemas from [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml):

1. **Singular `/api/v1` routes:** Collection endpoints end with a trailing slash (`/api/v1/voice/`, `/api/v1/task/`, `/api/v1/stream/`); item endpoints do not (`/api/v1/voice/{voice_id}`).
2. **End-to-end correlation:** Every request and response (including errors, binary audio headers, and SSE preambles) propagates `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, and `X-Opal-Causation-Id`. Correlation IDs are trace context only — never credentials.
3. **Optimistic concurrency on configuration:** Portable configuration reads return a strong quoted `ETag`. Mutations (`POST /profile/`, `PUT /setting/{key}`, `POST /config/load`, intent/voice/rule/action edits) require `If-Match` — missing yields `428 Precondition Required`, stale yields `412 Precondition Failed`. Runtime data deletions (events, sessions, failed utterances) are exempt by design.
4. **Admission vs. completion:** Synchronous creation returns `201 Created` + `Location`. Asynchronous work (`POST /event/`, `POST /action/{id}/execute`, `POST /task/`, `POST /stream/`) returns `202 Accepted` (honoring `Idempotency-Key`) and transitions through the shared lifecycle vocabulary: `queued -> running -> completed | failed | cancelled | timed_out` (plus `dropped` on Event when input validation or queue bounds reject a rule dispatch).
5. **Portable configuration snapshots:** Every module exposes `config save`, `config load`, and `config validate`, capturing persistent desired configuration while excluding secrets, runtime inventory, binaries, and history.
6. **Least-privilege tool boundary:** Think authenticates to Event as the `think` principal with `actions:read`, `actions:execute`, and `executions:read` scopes, while `actions:write`, `rules:write`, and `settings:write` are explicitly denied.

### Profiles vs. Personas

Profiles and personas solve orthogonal problems and compose predictably:

- **Profiles (`opal <svc> profile ...`)** change *how services behave by default* (e.g., `"night-mode"` or `"studio"`). A v3 portable profile envelope contains a `shared` object plus module-namespaced compartments under `modules.<module-id>` (`modules.opal-say`, `modules.opal-listen`, etc.). Each service applies `shared` and its own compartment while preserving foreign compartments verbatim so a single YAML file can travel across the fleet.
- **Personas (`opal <svc> persona ...`)** change *who is speaking or reasoning* (e.g., `amy` or `vox`). OPAL Think is the authoritative persona registry; other services either keep standalone local persona records or resolve and cache them from Think's `owner_url`.

When a request omits a setting, every service resolves each field independently in strict precedence order:

```text
explicit request field  >  persona binding  >  active profile's modules.<svc>  >  active profile's shared  >  service default
```

### CLI Conventions and Ergonomics

The kernel's `x-opal-cli-format` maps every annotated REST operation to:

```text
opal <service> [parent] [group] <command> [ARGS] [OPTIONS]
```

- **Canonical verbs:** Resource lifecycles use `list`, `add`, `show`, `update`, and `remove`. Operational endpoints keep explicit verbs (`start`, `stop`, `watch`, `watch-video`, `snapshot`, `predict`, `generate`, `stream`, `publish`, `execute`, `test`, `promote`, `run`, `activate`, `save`, `load`, `validate`).
- **Auto `If-Match`:** When you omit `--if-match` on a configuration mutation, the CLI fetches the current strong `ETag` first and sends the header automatically. Pass `--if-match '"rev"'` explicitly when scripting CAS loops.
- **Client-side flags:**
  - `--out FILE` writes binary audio/JPEG/MJPEG or exported snapshots (`yaml`/`json` by extension) to disk.
  - `--in FILE`, `--shared FILE`, and `--module FILE` parse local `.yaml`/`.json` files on the client and submit structured JSON in the request body.
  - `--play` routes audio bytes returned by `opal say` to the local host's default audio output device (playback is intentionally outside the Say HTTP contract).
  - `--wait` polls a `202 Accepted` task or execution until it reaches a terminal status.
  - `-` reads a positional argument or option payload from `stdin`; `@path` reads text or JSON from a local file.
  - `opal think ask` and `opal think chat` are built-in aliases for `opal think task add` that wait for completion and print the plain `answer` text so you can pipe reasoning straight into `opal say` or `opal listen`.

---

## CLI Command Tree

```text
opal
├── say                       voice: host-installed TTS engines, voices, audio streams
│   ├── generate              <text> → completed WAV or headerless s16le PCM
│   ├── stream                <text> → progressive raw s16le mono PCM stream
│   ├── stream-incremental    <ndjson> → sentence-buffered PCM from streaming text chunks
│   ├── engine                list | show | update | validate
│   ├── voice                 list | add | show | update | remove | validate | test
│   ├── profile               list | add | show | update | remove | activate
│   ├── persona               list | add | show | update | remove | validate
│   ├── config
│   │   ├── save              [--out FILE]
│   │   ├── load              [--in FILE]
│   │   ├── validate          [--in FILE]
│   │   └── setting           list | show | set | remove
│   ├── info                  health
│   └── service               start | stop | log
│
├── listen                    hearing: wakewords, STT, intents, slots, NLU QA
│   ├── wakeword              list | add | show | update | remove
│   ├── intent                list | add | show | update | remove
│   ├── phrase                list | add | remove
│   ├── slot                  list | add | show | update | remove
│   ├── slot-value            list | add | remove
│   ├── slot-alias            list | add | remove
│   ├── recognition           test-text | test-audio | start | stop | status | stream
│   ├── data
│   │   └── failed-utterance  list | add | show | update | remove | promote
│   ├── regression            list | add | show | update | remove | run
│   ├── performance           last | summary | history
│   ├── profile               list | add | show | update | remove | activate
│   ├── persona               list | add | show | update | remove | validate
│   ├── config
│   │   ├── save              [--out FILE]
│   │   ├── load              [--in FILE]
│   │   ├── validate          [--in FILE]
│   │   └── setting           list | show | set | remove
│   ├── info                  health
│   └── service               start | stop | log
│
├── look                      sight: optional engines, models, predict, RTSP streams
│   ├── engine                list | show | discover | capabilities | update
│   ├── model                 list | show | load | unload
│   ├── hardware              list | show
│   ├── predict               image
│   ├── stream                start | list | show | stop | watch | watch-video | snapshot | metrics
│   ├── profile               list | add | show | update | remove | activate
│   ├── persona               list | add | show | update | remove | validate
│   ├── config
│   │   ├── save              [--out FILE]
│   │   ├── load              [--in FILE]
│   │   ├── validate          [--in FILE]
│   │   └── setting           list | show | set | remove
│   ├── info                  health
│   └── service               start | stop | log
│
├── look-yolo                 standalone Ultralytics YOLO engine adapter (optional direct CLI)
│   ├── predict               [frame]
│   ├── engines               list | discover | show | capabilities
│   ├── models                list | show | load | unload
│   ├── hardware              list | show
│   ├── profile               list | add | show | update | remove | activate
│   ├── persona               list | add | show | update | remove | validate
│   ├── config                save | load | validate | setting (list | show | set | remove)
│   ├── info                  health
│   └── service               start | stop | log
│
├── think                     reasoning: bounded LLM tasks, sessions, models
│   ├── ask                   alias of `task add` (waits, prints answer text)
│   ├── chat                  alias of `task add` bound to `--session-id`
│   ├── task                  list | add | show | watch | cancel
│   ├── session               list | add | show | remove
│   ├── model                 list | show
│   ├── profile               list | add | show | update | remove | activate
│   ├── persona               list | add | show | update | remove | validate
│   ├── config
│   │   ├── save              [--out FILE]
│   │   ├── load              [--in FILE]
│   │   ├── validate          [--in FILE]
│   │   └── setting           list | show | set | remove
│   ├── info                  health
│   └── service               start | stop | log
│
└── event                     nervous system: pub/sub ingress, rules, actions, audit
    ├── data
    │   ├── event             list | publish | clear | show | remove
    │   ├── topic             list
    │   └── execution         list | show
    ├── rule                  list | add | show | update | remove | test
    ├── action                list | add | show | update | remove | execute
    ├── profile               list | add | show | update | remove | activate
    ├── persona               list | add | show | update | remove | validate
    ├── config
    │   ├── save              [--out FILE]
    │   ├── load              [--in FILE]
    │   ├── validate          [--in FILE]
    │   └── setting           list | show | set | remove
    ├── info                  health
    └── service               start | stop | log
```

*(Machine-only Kubernetes/systemd probes `GET /api/v1/health/live` and `GET /api/v1/health/ready` intentionally omit CLI bindings; human and script callers use `opal <svc> info health`.)*

---

## EVENT FLOW

OPAL separates **event publication** (asynchronous, best-effort notifications on hierarchical dotted topics) from **command/action invocation** (explicit REST calls with durable `Task` or `Execution` records). Not every service talks directly to the event bus — and knowing *which* interface speaks *what* protocol prevents mysterious silent pipelines.

### Topic, Stream, and Action Topology

```text
  ┌────────────────────┐
  │    MICROPHONE      │
  └─────────┬──────────┘
            │ live PCM ("mic" source only; test-text / test-audio never publish)
            ▼
  ┌────────────────────┐   topic: opal.listen.intent.match
  │    opal-listen     │ ──────────────────────────────────────────────┐
  │    (port 8000)     │   (opt-in: event_publication_enabled=true,    │
  └────────────────────┘    event_transport="http" | "zmq")            │
                                                                       ▼
  ┌────────────────────┐   SSE: GET /api/v1/stream/{id}/events   ┌────────────────────┐
  │     opal-look      │ ──(frame|detection|status|terminal)───▶ │   CLI / Bridge     │
  │    (port 8082)     │        │                                │  republisher (*)   │
  └─────────┬──────────┘        │  (*) Look has NO native bus    └─────────┬──────────┘
            │ delegates         │      publisher in MVP Plus;              │ POST /api/v1/event/
            ▼ inference         │      pipe `look stream watch`            │ topic: vision.<cam>
  ┌────────────────────┐        │      into `event data event publish`     │        porch.detection
  │  opal-look-yolo    │        │                                          │        yard.detection
  │    (port 8086)     │        ▼                                          ▼
  └────────────────────┘   ┌──────────────────────────────────────────────────────────┐
                           │                       opal-event                         │
  ┌────────────────────┐   │                       (port 8080)                        │
  │ External Producers │──▶│  Topics: exact (`home.doorbell.pressed`) or `prefix.*`   │
  │ (CLI, IoT, CI/CD)  │   │  Rules:  stateless ANDed conditions ──▶ Action Worker    │
  └────────────────────┘   └──────┬──────────────────────┬────────────────────┬───────┘
       topics: home.*,            │                      │                    │
       garden.*, ci.*, ops.*      │ HTTP Action          │ Shell Action       │ Python Action
                                  │ POST /api/v1/task/   │ (`speak`, `look`,  │ (`module:func`
                                  ▼                      │  `bashtop`, etc.)  │  JSON stdin)
                           ┌────────────────────┐        ▼                    ▼
                           │     opal-think     │   ┌────────────────────┐ ┌──────────────┐
                           │    (port 8083)     │   │     opal-say       │ │ Host Plugins │
                           └──────┬──────▲──────┘   │    (port 8081)     │ └──────────────┘
                                  │      │          └─────────┬──────────┘
         `think` principal (REST) │      │Persona             │ WAV / s16le PCM bytes
         • GET  /api/v1/action/   │      │owner sync          ▼ (`--play` on client/host)
         • POST /action/{id}/exec │      │GET /persona/{id} ┌────────────────────┐
         • GET  /execution/{id}   └──────┴─────────────────▶│     SPEAKERS       │
         (bounded causation depth prevents feedback loops)  └────────────────────┘
```

### Transport and Guarantee Matrix

| Producer -> Consumer | Channel / Topic | Contract Status | Delivery & Replay Semantics |
| --- | --- | --- | --- |
| **Listen -> Event** | `opal.listen.intent.match` (HTTP `POST /api/v1/event/` or 2-frame ZeroMQ) | **Fixed topic name** in `opal_listen.yaml` (envelope metadata schema `2.0`). | Disabled by default (`event_publication_enabled=false`). Deduplicated within `dedup_window_ms`. `event_transport='both'` is rejected to avoid duplicates. |
| **External / CLI -> Event** | Any lowercase dotted topic matching `^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)*$` (e.g., `home.doorbell.pressed`, `ci.build.finished`) | **Caller-chosen** (`opal_event.yaml`). Max wire size `1 MiB`. | `202 Accepted` means enqueued, not delivered or executed. Rules match exact topics or `prefix.*` hierarchies (`vision.*` matches `vision.front`, not `vision`). |
| **Look -> Watcher / Event** | `GET /api/v1/stream/{id}/events` (`text/event-stream`) -> optional pipe to `vision.*` / `porch.detection` | **SSE shape fixed** (`frame`, `detection`, `status`, `heartbeat`, `terminal`); **bus topic caller-chosen**. | Per-stream SSE supports bounded replay via `Last-Event-ID` (`409` if stale). Disconnecting a watcher leaves the stream running. |
| **Event -> Think** | Registered `http` action `POST http://127.0.0.1:8083/api/v1/task/` | **Standard HTTP action** (`body_mode: template`). | `202 Accepted` records task admission; Event tracks HTTP status in `Execution`, while Think owns the `Task` lifecycle. |
| **Think -> Event** | `GET /action/`, `POST /action/{id}/execute`, `GET /execution/{id}` | **Normative integration** (`x-opal-authorization.principals.think`). | Think validates arguments against `Action.input_schema`, polls `Execution` until terminal, and propagates `X-Opal-Causation-Id` to block runaway loops. |
| **Think / Event -> Say** | CLI `speak` shell action (`opal say generate ... --play`) or direct `POST /api/v1/generate[/stream[/incremental]]` | **Standard REST / Shell action.** | Say returns raw PCM or WAV audio bytes (`200 OK`) with `X-Opal-Sample-Rate`; a host client (`--play`, `aplay`, `ffplay`) performs physical playback. |
| **Any Service -> Think** | `GET {owner_url}/api/v1/persona/{persona_id}` | **Normative persona ownership** (`x-opal-persona`). | Consumers cache owner personas with their strong `ETag` (`origin: owner`) and revalidate on use. |

---

## Recipes

### Single-Service One-Liners

Each section below stays strictly inside **one** OPAL service and walks through **24 progressive one-liners** that build upon one another — from booting the daemon and discovering host capabilities to configuring resources, running workloads, tuning profiles/personas, and snapshotting state.

---

<a id="opal-say"></a>

### opal say

*24 progressive one-liners for text-to-speech synthesis, voice registration, personas, namespaced profiles, and streaming audio.*

**1. Start the OPAL Say service process.**

```bash
opal say service start
```

**2. Check the unified health report to confirm Say is live and ready.**

```bash
opal say info health
```

**3. List the host-installed TTS engines Say discovered at startup.**

```bash
opal say engine list
```

**4. Inspect the `piper` engine adapter's status and current configuration.**

```bash
opal say engine show piper
```

**5. Validate that the `piper` runtime and adapter can actually synthesize speech.**

```bash
opal say engine validate piper
```

**6. Park a secondary engine (`kokoro`) in a disabled state without uninstalling it from the host.**

```bash
opal say engine update kokoro --no-enabled
```

**7. Register an American English ONNX voice model already resident on disk.**

```bash
opal say voice add --voice-id en-us-lessac-medium --name "Lessac (US)" --engine-id piper --engine-voice-ref /opt/opal/voices/en_US-lessac-medium.onnx --language en-US
```

**8. Register a calm British baritone voice for narration and evening alerts.**

```bash
opal say voice add --voice-id en-gb-alan-low --name "Alan (UK)" --engine-id piper --engine-voice-ref /opt/opal/voices/en_GB-alan-low.onnx --language en-GB
```

**9. Register a Spanish voice so multilingual recipes have a native speaker.**

```bash
opal say voice add --voice-id es-es-davefx-medium --name "DaveFX (ES)" --engine-id piper --engine-voice-ref /opt/opal/voices/es_ES-davefx-medium.onnx --language es-ES
```

**10. List all enabled English voices (`--language en` matches both `en-US` and `en-GB` by prefix).**

```bash
opal say voice list --language en --enabled
```

**11. Validate that `en-us-lessac-medium` resolves cleanly against its engine.**

```bash
opal say voice validate en-us-lessac-medium
```

**12. Audition `en-gb-alan-low` with a classic phonetic pangram on your speakers.**

```bash
opal say voice test en-gb-alan-low --text "Sphinx of black quartz, judge my vow." --play
```

**13. Synthesize and play an immediate announcement using the default voice.**

```bash
opal say generate "The coffee machine has reached operating temperature." --play
```

**14. Render a completed WAV container to disk for reuse in alerts or tests.**

```bash
opal say generate "Welcome to the lab. Please do not feed the rack servers." --voice-id en-us-lessac-medium --output-format wav --out welcome.wav
```

**15. Dial down speaking rate and linear gain for a late-night verification code.**

```bash
opal say generate "Your one-time code is eight, four, two, nine." --voice-id en-gb-alan-low --speed 0.8 --volume 0.35 --play
```

**16. Pass engine-specific synthesis parameters through `--engine-options`.**

```bash
opal say generate "Testing custom phoneme timing." --voice-id en-us-lessac-medium --engine-options '{"noise_scale":0.5,"length_scale":1.1}' --play
```

**17. Export headerless 16 kHz `s16le` mono PCM bytes for a VoIP or wakeword pipeline.**

```bash
opal say generate "Please hold while we locate a human." --output-format pcm --sample-rate 16000 --out hold-16k.pcm
```

**18. Progressively stream a long text file so playback starts before synthesis finishes.**

```bash
opal say stream @chapter-one.txt --voice-id en-gb-alan-low --play
```

**19. Stream speech from incremental NDJSON text chunks (`/api/v1/generate/stream/incremental`).**

```bash
opal say stream-incremental @live-utterance.ndjson --play
```

**20. Bind a named `vox` persona to the British narrator voice.**

```bash
opal say persona add --persona-id vox --name "Vox" --description "Dry British house narrator" --voice-id en-gb-alan-low
```

**21. Validate the persona's voice binding and speak in character.**

```bash
opal say persona validate vox && opal say generate "Good evening. All systems are nominal." --persona-id vox --play
```

**22. Load and activate a `bedtime` profile whose `modules.opal-say` compartment lowers volume and speed.**

```bash
opal say profile add --name "Bedtime" --description "Quiet after-hours defaults" --is-active --module say-bedtime.yaml
```

**23. Raise the maximum accepted input length via a runtime setting override.**

```bash
opal say config setting set --name max_text_length --value 8192
```

**24. Save a portable YAML configuration snapshot and inspect the last 20 log lines.**

```bash
opal say config save --out say-snapshot.yaml && opal say service log --lines 20
```

---

<a id="opal-listen"></a>

### opal listen

*24 progressive one-liners for wakewords, intents, slots, spoken aliases, audio diagnostics, miss promotion, and regression testing.*

**1. Start the OPAL Listen service process.**

```bash
opal listen service start
```

**2. Inspect service health and discover host microphones under `.details.audio_devices`.**

```bash
opal listen info health
```

**3. Register the `"hey opal"` wakeword with an `0.85` confidence floor.**

```bash
opal listen wakeword add --name "hey opal" --confidence-threshold 0.85
```

**4. Relax the wakeword threshold slightly if whispers across the room are missed.**

```bash
opal listen wakeword update ww-hey-opal --confidence-threshold 0.80
```

**5. Create a `lights.turn_on` intent seeded with initial training phrases.**

```bash
opal listen intent add --name lights.turn_on --description "Turn room lights on" --confidence-threshold 0.75 --phrases '["turn on the lights","lights on in the {room}","illuminate the {room}"]'
```

**6. Create a second intent for launching desktop utilities by voice.**

```bash
opal listen intent add --name app.launch --description "Open a named desktop program" --phrases '["launch {app}","open {app}","start {app}"]'
```

**7. Add an idiomatic training phrase to `lights.turn_on` as people invent new phrasing.**

```bash
opal listen phrase add int-lights-on --phrase "flip the switch in the {room}"
```

**8. List every training phrase currently attached to `lights.turn_on`.**

```bash
opal listen phrase list int-lights-on
```

**9. Create a `room` slot to extract target locations from utterances.**

```bash
opal listen slot add --name room --slot-type list --description "Named rooms in the building"
```

**10. Populate canonical values on the `room` slot.**

```bash
opal listen slot-value add slt-room --value kitchen
```

**11. Teach the `kitchen` slot value a colloquial spoken alias (`"the galley"`).**

```bash
opal listen slot-alias add slt-room val-kitchen --alias "the galley"
```

**12. Dry-run text through intent and slot extraction without polluting history (`--no-save-log`).**

```bash
opal listen recognition test-text --text "turn on the lights in the galley" --no-save-log
```

**13. Dry-run a recorded WAV file through wakeword detection, STT, and NLU.**

```bash
opal listen recognition test-audio samples/galley-lights.wav --require-wakeword
```

**14. Enable external intent-match event publication over HTTP (`opal.listen.intent.match`).**

```bash
opal listen config setting set --name event_publication_enabled --value true
```

**15. Configure a 2.5-second deduplication window so repeated matches do not double-fire.**

```bash
opal listen config setting set --name dedup_window_ms --value 2500
```

**16. Start the live microphone capture and recognition pipeline.**

```bash
opal listen recognition start
```

**17. Check live queue utilization, mic overflows, and per-stage latency metrics.**

```bash
opal listen recognition status
```

**18. Stream live recognition events over SSE with diagnostic debug fields enabled.**

```bash
opal listen recognition stream --debug
```

**19. List the ten most recent unrecognized utterances awaiting human review.**

```bash
opal listen data failed-utterance list --no-reviewed --limit 10
```

**20. Tag a failed utterance with its intended target and mark it reviewed.**

```bash
opal listen data failed-utterance update fu-07 --expected-intent lights.turn_on --notes "Kettle boiling in background" --reviewed
```

**21. Promote that failed utterance into both a live training phrase and a regression test in one call.**

```bash
opal listen data failed-utterance promote fu-07 --intent-id int-lights-on --create-regression
```

**22. Add an explicit regression test that asserts both the matched intent and extracted slot map.**

```bash
opal listen regression add --name "galley alias resolves to kitchen" --phrase "lights on in the galley" --expected-intent lights.turn_on --expected-slots '{"room":"kitchen"}'
```

**23. Run all enabled regression tests to verify recent vocabulary edits broke nothing.**

```bash
opal listen regression run --enabled-only
```

**24. Inspect aggregate STT/refiner/NLU latency percentiles and export a portable snapshot.**

```bash
opal listen performance summary --limit 50 && opal listen config save --out listen-snapshot.yaml
```

---

<a id="opal-look"></a>

### opal look

*24 progressive one-liners for engine discovery, GPU hardware inspection, model loading, single-image prediction, and live RTSP streams.*

**1. Start the OPAL Look visual observation service.**

```bash
opal look service start
```

**2. Check service readiness (note: Look reports healthy even with zero AI engines installed).**

```bash
opal look info health
```

**3. Scan the host for installed detection engine adapters (YOLO, RF-DETR, RT-DETR, D-FINE).**

```bash
opal look engine discover
```

**4. List all discovered engine adapters and whether each is enabled.**

```bash
opal look engine list
```

**5. Inspect the `yolo` adapter's supported tasks, device types, and accepted `engine_options` schema.**

```bash
opal look engine capabilities yolo
```

**6. Enumerate local CPU, GPU, and accelerator devices visible to Look's engines.**

```bash
opal look hardware list
```

**7. Show memory and capability details for GPU `cuda:0`.**

```bash
opal look hardware show cuda:0 --engine-id yolo
```

**8. List locally installed models owned by the `yolo` engine.**

```bash
opal look model list --engine-id yolo
```

**9. Inspect metadata and load state for `yolo11n`.**

```bash
opal look model show yolo11n --engine-id yolo
```

**10. Pre-load `yolo11n` weights into memory so the first inference frame has no cold-start spike.**

```bash
opal look model load yolo11n --engine-id yolo
```

**11. Run synchronous object detection on a local still image at `0.50` minimum confidence.**

```bash
opal look predict image --engine-id yolo --model-id yolo11n --source driveway.jpg --confidence 0.50
```

**12. Run GPU-pinned single-image prediction and include raw adapter-native output for debugging.**

```bash
opal look predict image --engine-id yolo --model-id yolo11n --source loading-dock.jpg --device-id cuda:0 --engine-options '{"iou":0.45}' --include-native
```

**13. Admit a plain video-only RTSP camera stream — no engine or model required.**

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1
```

**14. Admit a retry-safe YOLO detection stream with bounding-box overlays and `drop_oldest` backpressure.**

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1 --engine-id yolo --model-id yolo11n --confidence 0.45 --device-id cuda:0 --annotate --buffer-policy drop_oldest --buffer-size 4 --idempotency-key porch-cam-main
```

**15. List all active and recently stopped streams.**

```bash
opal look stream list
```

**16. Inspect a stream's state and verify RTSP userinfo credentials are scrubbed in `source_redacted`.**

```bash
opal look stream show str-porch
```

**17. Grab an unannotated JPEG snapshot of the latest decoded frame.**

```bash
opal look stream snapshot str-porch --no-annotated --out porch-clean.jpg
```

**18. Grab an annotated JPEG snapshot with rendered detection boxes and labels.**

```bash
opal look stream snapshot str-porch --annotated --out porch-annotated.jpg
```

**19. Capture the live annotated MJPEG video feed to a local file or viewer.**

```bash
opal look stream watch-video str-porch --annotated --out porch-feed.mjpeg
```

**20. Stream live typed JSON events (`frame`, `detection`, `status`, `terminal`) over SSE.**

```bash
opal look stream watch str-porch
```

**21. Reconnect to a stream's SSE feed using `--last-event-id` for bounded missed-event replay.**

```bash
opal look stream watch str-porch --last-event-id evt-1042
```

**22. Read per-stream FPS, dropped-frame counters, and mean inference milliseconds.**

```bash
opal look stream metrics str-porch
```

**23. Stop the detection stream cleanly and unload `yolo11n` weights to free VRAM.**

```bash
opal look stream stop str-porch && opal look model unload yolo11n --engine-id yolo
```

**24. Validate and save Look's portable configuration snapshot.**

```bash
opal look config validate && opal look config save --out look-snapshot.yaml
```

---

<a id="opal-think"></a>

### opal think

*24 progressive one-liners for model discovery, guarded tasks, SSE progress watching, multi-turn sessions, and authoritative personas.*

**1. Start the OPAL Think reasoning service.**

```bash
opal think service start
```

**2. Check health, model availability, and active task counts.**

```bash
opal think info health
```

**3. List all models discovered from configured provider adapters.**

```bash
opal think model list
```

**4. Inspect `ollama:llama3.2` to verify `streaming`, `tool_calling`, `vision`, and `context_window`.**

```bash
opal think model show ollama:llama3.2
```

**5. Configure `ollama:llama3.2` as Think's default model.**

```bash
opal think config setting set --name models.default_id --value '"ollama:llama3.2"'
```

**6. Point Think at OPAL Event so tasks can discover and execute registered actions.**

```bash
opal think config setting set --name event.base_url --value '"http://127.0.0.1:8080"'
```

**7. Ask a stateless one-shot question and print the completed answer text.**

```bash
opal think ask "Explain HTTP 428 Precondition Required in one crisp sentence."
```

**8. Override the model for a single code-heavy question.**

```bash
opal think ask "Give one Python regex that matches dotted lowercase topic names." --model-id ollama:qwen2.5-coder:7b
```

**9. Pass untrusted structured telemetry via `--context` so data stays separated from instructions.**

```bash
opal think ask "Which sensor reading is physically implausible, and why?" --context '{"greenhouse_c":[21.2,21.5,142.8,21.4]}'
```

**10. Enqueue a bounded asynchronous task (`202 Accepted`) with step, timeout, and idempotency guards.**

```bash
opal think task add "Audit active Event actions and summarize what physical devices this host can touch." --max-steps 6 --timeout-seconds 90 --idempotency-key audit-2026-11-18
```

**11. Watch live step summaries and incremental token output over SSE.**

```bash
opal think task watch tsk-audit-01
```

**12. Fetch the final authoritative `Task` record, including sanitized `action_input` steps.**

```bash
opal think task show tsk-audit-01
```

**13. Attach caller-only benchmark tracking metadata (persisted on the task, never sent to the model).**

```bash
opal think task add "Compute 37 * 43." --metadata '{"evalset":"arith-smoke","case_id":"mul-037"}' --wait
```

**14. Request cancellation of an in-flight task that is taking too long.**

```bash
opal think task cancel tsk-runaway-99
```

**15. List the ten most recent failed tasks for troubleshooting.**

```bash
opal think task list --status failed --limit 10
```

**16. Register `amy` in Think — the OPAL suite's authoritative persona registry.**

```bash
opal think persona add --persona-id amy --name "Amy" --description "Calm, concise systems engineer" --voice-id en-gb-alan-low
```

**17. Validate Think's local model/instruction bindings for persona `amy`.**

```bash
opal think persona validate amy
```

**18. Open an explicit multi-turn conversation session bound to persona `amy`.**

```bash
opal think session add --title "Home lab power budget" --persona-id amy
```

**19. Send the opening turn in that session (`chat` serializes turns per session).**

```bash
opal think chat "I have a 65W mini-PC running five Python services and one RTSP stream. Where will CPU spike first?" --session-id ses-power
```

**20. Ask a follow-up question that relies on the session's prior turn.**

```bash
opal think chat "What if I move YOLO inference onto an external Coral or CUDA box?" --session-id ses-power
```

**21. List every retained task belonging to `ses-power`.**

```bash
opal think task list --session-id ses-power
```

**22. Delete the conversation session and its session-linked tasks when finished.**

```bash
opal think session remove ses-power
```

**23. Cap concurrent active tasks and default step budgets across the service.**

```bash
opal think config setting set --name task.max_concurrent --value 3 && opal think config setting set --name task.default_max_steps --value 8
```

**24. Save Think's portable configuration snapshot to disk.**

```bash
opal think config save --out think-snapshot.yaml
```

---

<a id="opal-event"></a>

### opal event

*24 progressive one-liners for publishing events, inspecting topics, registering shell/HTTP/Python actions, testing rules, and auditing executions.*

**1. Start the OPAL Event broker and rule engine.**

```bash
opal event service start
```

**2. Inspect service health and read event/execution counters under `.details.stats`.**

```bash
opal event info health
```

**3. Publish a doorbell event (`202 Accepted` returns a `PublishReceipt`).**

```bash
opal event data event publish --topic home.doorbell.pressed --source front-button --data '{"door":"front"}'
```

**4. Publish a retry-safe sensor reading using `--idempotency-key`.**

```bash
opal event data event publish --topic garden.soil.moisture --source greenhouse-pi --data '{"bed":"tomatoes","moisture_pct":14.2}' --idempotency-key soil-20261118T0800Z
```

**5. List every topic observed by Event's internal store.**

```bash
opal event data topic list
```

**6. Query the five most recent moisture events within a time window.**

```bash
opal event data event list --topic garden.soil.moisture --from 2026-11-18T00:00:00Z --limit 5
```

**7. Show the full normalized envelope of one stored event by ID.**

```bash
opal event data event show 7fe5d3fa-d326-41fd-9cce-5d76b69a6174
```

**8. Register an `exec`-mode shell action (argv-only, no shell interpolation) with an `input_schema` contract.**

```bash
opal event action add --id ring-chime --type shell --mode exec --executable /usr/bin/aplay --args '["/opt/opal/sounds/chime.wav"]' --stdin none --timeout-seconds 10 --description "Play the front-door chime WAV on local speakers." --keywords '["chime","doorbell","audio"]' --input-schema '{"type":"object","properties":{"door":{"type":"string"}},"required":["door"]}'
```

**9. Register a static-script `bash` action that receives the full normalized event JSON on `stdin`.**

```bash
opal event action add --id archive-event --type shell --mode bash --script-path /opt/opal/scripts/archive_event.sh --args '["{{data.bed}}"]' --stdin event_json --timeout-seconds 15 --description "Append sensor event JSON to cold storage."
```

**10. Register an HTTP webhook action forwarding `event_json` to an allowlisted endpoint.**

```bash
opal event action add --id notify-ops --type http --method POST --url http://127.0.0.1:9000/hooks/opal --body-mode event_json --timeout-seconds 10 --description "Forward matched events to the local ops bridge."
```

**11. Register a templated HTTP action that submits an asynchronous reasoning task to Think.**

```bash
opal event action add --id ask-garden-advisor --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Give a one-sentence watering recommendation for bed {{data.bed}} at {{data.moisture_pct}}% moisture.","context":"{{event}}","max_steps":3}' --timeout-seconds 15 --description "Trigger a Think task for low-moisture events."
```

**12. Register an out-of-process Python plugin action (`module` + `function`).**

```bash
opal event action add --id score-anomaly --type python --module opal_plugins.telemetry --function score_moisture --timeout-seconds 20 --description "Run anomaly scoring in an isolated Python subprocess."
```

**13. List all registered actions and their discovery metadata.**

```bash
opal event action list
```

**14. Create an exact-topic rule wiring `home.doorbell.pressed` to `ring-chime`.**

```bash
opal event rule add --id doorbell-rule --topic home.doorbell.pressed --conditions '[]' --actions '["ring-chime"]'
```

**15. Create a hierarchical wildcard rule (`garden.*`) with strictly typed ANDed conditions.**

```bash
opal event rule add --id dry-beds-rule --topic 'garden.*' --conditions '[{"path":"data.moisture_pct","operator":"lt","value":20},{"path":"data.bed","operator":"in","value":["tomatoes","peppers"]}]' --actions '["notify-ops","ask-garden-advisor"]'
```

**16. Dry-run `dry-beds-rule` against a synthetic payload without executing any actions.**

```bash
opal event rule test dry-beds-rule --event '{"topic":"garden.soil.moisture","data":{"bed":"tomatoes","moisture_pct":14.2}}'
```

**17. Manually execute `ring-chime` for a fire drill and wait for the terminal `Execution` record.**

```bash
opal event action execute ring-chime --event '{"topic":"manual.drill","data":{"door":"front"}}' --wait
```

**18. List the ten most recent completed action executions.**

```bash
opal event data execution list --status completed --limit 10
```

**19. Audit executions dropped before launch due to `input_schema` violations or worker queue saturation.**

```bash
opal event data execution list --status dropped --limit 10
```

**20. Inspect `exit_code`, `duration_ms`, `stdout`, and `stderr` for a single execution.**

```bash
opal event data execution show exe-901
```

**21. Temporarily mute a rule during irrigation maintenance without deleting it.**

```bash
opal event rule update dry-beds-rule --no-enabled
```

**22. Tighten an HTTP action's timeout to 5 seconds.**

```bash
opal event action update notify-ops --timeout-seconds 5
```

**23. Lower the maximum accepted wire event size to 256 KiB.**

```bash
opal event config setting set --name max_event_bytes --value 262144
```

**24. Save Event's configuration snapshot to a file and clear test events from the history log.**

```bash
opal event config save --out event-snapshot.yaml && opal event data event clear
```

---

<a id="combined"></a>

## combined

*50 multi-service recipes where two, three, four, or all five OPAL faculties team up.*

<a id="once-per-host-plumbing"></a>

### Once-Per-Host Plumbing

Set up three small pieces of shared wiring once so every combined recipe below stays compact and readable:

1. **Connect Think to Event** so reasoning tasks can discover and execute registered actions.
2. **Turn on Listen's live event publisher** so microphone matches land on `opal.listen.intent.match` (diagnostic `test-text` and `test-audio` calls remain strictly local).
3. **Register a reusable `speak` action in Event.** Because OPAL Say returns audio bytes and never touches hardware speakers itself, an Event `shell` action running `opal say generate ... --play` on the speaker host lets both Event rules and Think tasks speak aloud safely with schema-validated input.

```bash
# 1. Point Think at Event's REST endpoint
opal think config setting set --name event.base_url --value '"http://127.0.0.1:8080"'

# 2. Enable live microphone intent publication from Listen to Event
opal listen config setting set --name event_publication_enabled --value true
opal listen config setting set --name event_transport --value '"http"'

# 3. Register a schema-guarded `speak` action that both Event rules and Think tasks can call
opal event action add \
  --id speak \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","{{data.text}}","--play"]' \
  --stdin none \
  --timeout-seconds 30 \
  --description "Synthesize data.text via OPAL Say and play it on the host's default speaker." \
  --keywords '["speak","say","tts","announce","voice"]' \
  --suggested-prompts '["Say hello out loud","Announce this message on the speakers"]' \
  --input-schema '{"type":"object","properties":{"text":{"type":"string","minLength":1}},"required":["text"]}'
```

> **Tip on event payload shapes:** Listen's topic `opal.listen.intent.match` is fixed by contract; the examples below inspect `data.intent_name`, `data.transcript`, and `data.slot_values.<slot>`. Look's SSE `detection` frames carry `event_type`, `detections[0].class_name`, and `detections[0].confidence`. Always verify a live sample with `opal event data event list --limit 1` when wiring production rules.

---

<a id="core-classics-and-desktop-control"></a>

### 1–8: Core Classics & Desktop Control

<a id="recipe-1"></a>

#### 1. Setting up a camera to use YOLO for detection

*Interfaces: `look` + `event` (+ `look-yolo` adapter).* Discover the YOLO adapter, pre-load `yolo11n` onto the GPU, start an annotated RTSP detection stream, and pipe its live SSE detection events onto the OPAL Event bus so any rule or service can subscribe to `vision.front_door`.

```bash
# Discover engines, warm up the YOLO weights, and start an idempotent RTSP detection stream
opal look engine discover
opal look model load yolo11n --engine-id yolo
opal look stream start \
  --source rtsp://192.168.1.40:554/stream1 \
  --engine-id yolo \
  --model-id yolo11n \
  --confidence 0.50 \
  --device-id cuda:0 \
  --annotate \
  --buffer-policy drop_oldest \
  --idempotency-key front-door-yolo

# Bridge the stream's live SSE events onto the Event bus under `vision.front_door`
opal look stream watch str-front-door | while IFS= read -r frame_json; do
  [ -n "$frame_json" ] && opal event data event publish --topic vision.front_door --source opal-look --data "$frame_json"
done
```

<a id="recipe-2"></a>

#### 2. Ask an AI a question — and hear the answer

*Interfaces: `think` + `say`.* `opal think ask` submits a task, waits for completion, and prints only the final `answer` text, which pipes cleanly into `opal say generate - --play`.

```bash
# Ask Think a question and pipe the plain-text answer straight into Say for immediate playback
opal think ask "Why do touch-tone phones use two simultaneous frequencies per button? Answer in two clear sentences." \
  | opal say generate - --voice-id en-gb-alan-low --play
```

<a id="recipe-3"></a>

#### 3. Launch bashtop by voice command

*Interfaces: `listen` + `event`.* Teach Listen an intent for opening a system monitor, register an argv-safe `exec` shell action that spawns `bashtop` inside a terminal emulator on your desktop display, and connect the two with an Event rule.

```bash
# 1. Teach Listen how you ask for the system monitor
opal listen intent add \
  --name desktop.bashtop \
  --description "Open bashtop in a new terminal window" \
  --confidence-threshold 0.85 \
  --phrases '["launch bashtop","open bashtop","show system monitor","bring up bashtop"]'

# 2. Register an exec-mode shell action (no shell interpolation) that launches kitty + bashtop
opal event action add \
  --id launch-bashtop \
  --type shell \
  --mode exec \
  --executable /usr/bin/kitty \
  --args '["--title","OPAL System Monitor","/usr/bin/bashtop"]' \
  --stdin none \
  --timeout-seconds 10 \
  --description "Spawn bashtop in a dedicated terminal window."

# 3. Route live microphone matches for `desktop.bashtop` to the launcher action
opal event rule add \
  --id voice-launch-bashtop \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"desktop.bashtop"}]' \
  --actions '["launch-bashtop"]'

# 4. Ensure live recognition is running
opal listen recognition start
```

<a id="recipe-4"></a>

#### 4. Shutdown your computer by voice

*Interfaces: `listen` + `event` + `say`.* Voice-triggered poweroff deserves belt-and-suspenders safety: require a deliberate multi-word phrase with a high `0.92` confidence threshold, announce the impending shutdown out loud, and schedule `shutdown +1` so you have sixty seconds to type `shutdown -c` if your parrot learned a new trick.

```bash
# 1. Require a very explicit phrase and a strict 0.92 confidence threshold
opal listen intent add \
  --name host.shutdown \
  --description "Schedule a graceful 60-second workstation shutdown" \
  --confidence-threshold 0.92 \
  --phrases '["authorize workstation shutdown now","initiate system poweroff sequence"]'

# 2. Announce the countdown aloud so it never happens silently
opal event action add \
  --id warn-shutdown \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Workstation shutdown scheduled in sixty seconds. Run shutdown dash c to abort.","--volume","1.4","--play"]' \
  --stdin none \
  --description "Announce a 60-second shutdown warning."

# 3. Schedule a 1-minute graceful shutdown (requires polkit/sudoers rule for the service user)
opal event action add \
  --id schedule-shutdown \
  --type shell \
  --mode exec \
  --executable /usr/sbin/shutdown \
  --args '["-h","+1","Scheduled by OPAL voice command"]' \
  --stdin none \
  --description "Schedule system halt in one minute."

# 4. Require BOTH intent match and >= 0.92 confidence in the Event rule
opal event rule add \
  --id voice-shutdown-rule \
  --topic opal.listen.intent.match \
  --conditions '[
    {"path":"data.intent_name","operator":"eq","value":"host.shutdown"},
    {"path":"data.confidence","operator":"gte","value":0.92}
  ]' \
  --actions '["warn-shutdown","schedule-shutdown"]'
```

<a id="recipe-5"></a>

#### 5. Setting up a persona across the suite

*Interfaces: `think` + `say` + `listen` + `look` + `event`.* OPAL Think is the authoritative persona owner (`x-opal-persona`), while Say validates that `voice_id` resolves to an installed TTS voice. Register `jarvis` across the suite, validate service-local bindings, and run a spoken character check.

```bash
# 1. Create the authoritative persona record in Think and mirror it across standalone services
opal think persona add  --persona-id jarvis --name "Jarvis" --description "Polite, understated lab steward" --voice-id en-gb-alan-low
opal say persona add    --persona-id jarvis --name "Jarvis" --description "Polite, understated lab steward" --voice-id en-gb-alan-low
opal listen persona add --persona-id jarvis --name "Jarvis" --description "Polite, understated lab steward" --voice-id en-gb-alan-low
opal look persona add   --persona-id jarvis --name "Jarvis" --description "Polite, understated lab steward" --voice-id en-gb-alan-low
opal event persona add  --persona-id jarvis --name "Jarvis" --description "Polite, understated lab steward" --voice-id en-gb-alan-low

# 2. Verify service-specific bindings (Think checks model/instructions; Say checks voice_id)
opal think persona validate jarvis
opal say persona validate jarvis

# 3. Have Jarvis introduce himself using both his Think persona and his Say voice
opal think ask "Introduce yourself in one understated sentence." --persona-id jarvis \
  | opal say generate - --persona-id jarvis --play
```

<a id="recipe-6"></a>

#### 6. Full-duplex voice assistant

*Interfaces: `listen` + `event` + `think` + `say`.* Wire a conversational assistant end to end: you speak after the wakeword, Listen publishes `opal.listen.intent.match`, Event triggers a Think task carrying your transcript in a persistent session, and Think speaks its reply through the registered `speak` action.

```bash
# 1. Create a persistent assistant session in Think
opal think session add --title "Desk Assistant" --persona-id jarvis

# 2. Add a general-purpose assistant intent in Listen
opal listen intent add \
  --name assistant.query \
  --description "General spoken request for the assistant" \
  --phrases '["can you tell me","i have a question","help me with something","what do you think about"]'

# 3. Register an Event HTTP action that forwards the transcript into the Think session
opal event action add \
  --id dispatch-to-assistant \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"session_id":"ses-desk","persona_id":"jarvis","prompt":"The user said: {{data.transcript}}. Reply helpfully in at most two spoken sentences by invoking the speak action.","context":"{{event}}","max_steps":5}' \
  --timeout-seconds 30 \
  --description "Forward spoken user queries to the persistent Think session."

# 4. Connect Listen's match topic to Think and start listening
opal event rule add \
  --id assistant-loop \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"assistant.query"}]' \
  --actions '["dispatch-to-assistant"]'
opal listen recognition start
```

<a id="recipe-7"></a>

#### 7. One portable profile across Say and Listen

*Interfaces: `say` + `listen`.* Because v3 profiles store per-module settings under `modules.<module-id>` and preserve foreign compartments untouched, you can author **one** `focus-mode.yaml` file and load it into both Say and Listen.

```bash
# Write one portable profile document containing compartments for both opal-say and opal-listen
cat > focus-mode.yaml <<'EOF'
name: Focus Mode
description: Quiet voice output and minimal interruption intents during deep work
is_active: true
shared: {}
modules:
  opal-say:
    voice_id: en-gb-alan-low
    speed: 1.05
    volume: 0.35
    output_format: wav
  opal-listen:
    wakeword_names:
      - hey opal
    enabled_intents:
      - assistant.query
      - lights.turn_on
EOF

# Ingest and activate the exact same file on both services
opal say profile add --in focus-mode.yaml
opal listen profile add --in focus-mode.yaml
```

<a id="recipe-8"></a>

#### 8. Streaming LLM tokens into incremental TTS

*Interfaces: `think` + `say` (via Python).* Combine Think's SSE `task.output` token stream (`GET /api/v1/task/{id}/stream`) with Say's NDJSON incremental synthesis endpoint (`POST /api/v1/generate/stream/incremental`) so the first sentence starts playing before the LLM finishes writing paragraph two.

```python
#!/usr/bin/env python3
"""Pipe live OPAL Think SSE output chunks into OPAL Say's incremental NDJSON stream."""
import json
import httpx

THINK_URL = "http://127.0.0.1:8083/api/v1"
SAY_URL = "http://127.0.0.1:8081/api/v1"


def think_chunks(task_id: str):
    # Line 1 of /generate/stream/incremental is the generation parameter header
    yield json.dumps({"voice_id": "en-gb-alan-low", "speed": 1.0, "sample_rate": 22050}) + "\n"
    with httpx.stream("GET", f"{THINK_URL}/task/{task_id}/stream", timeout=120.0) as sse:
        event_name = None
        for line in sse.iter_lines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and event_name == "task.output":
                payload = json.loads(line.split(":", 1)[1].strip())
                if text := payload.get("text"):
                    yield json.dumps({"text": text}) + "\n"
    yield json.dumps({"done": True}) + "\n"


task = httpx.post(
    f"{THINK_URL}/task/",
    json={"prompt": "Explain how a mechanical lighthouse clockwork rotates, in four vivid sentences."},
    timeout=15.0,
).json()

with httpx.stream(
    "POST",
    f"{SAY_URL}/generate/stream/incremental",
    headers={"Content-Type": "application/x-ndjson"},
    content=think_chunks(task["id"]),
    timeout=120.0,
) as audio, open("lighthouse-stream.pcm", "wb") as out:
    print("Streaming s16le PCM at", audio.headers.get("X-Opal-Sample-Rate"), "Hz")
    for pcm_bytes in audio.iter_bytes():
        out.write(pcm_bytes)
```

---

<a id="voice-lab-and-audio-tricks"></a>

### 9–16: Voice Lab & Audio Tricks

<a id="recipe-9"></a>

#### 9. Soundoff — opal say says hello in every voice it has

*Interfaces: `say` + `listen`.* Enumerate every enabled voice registered in OPAL Say, have each voice introduce itself by name on the speakers while saving a WAV clip, and pass each clip through `opal listen recognition test-audio` to score STT legibility across your entire voice catalog.

```bash
# Roll call: every enabled voice says hello out loud and gets graded by Listen's STT pipeline
opal say voice list --enabled | python3 -c "
import json, subprocess, sys
for v in json.load(sys.stdin):
    vid, name = v['voice_id'], v['name']
    wav = f'/tmp/soundoff-{vid}.wav'
    phrase = f'Hello from OPAL Say. My voice identifier is {name}.'
    subprocess.run(['opal', 'say', 'generate', phrase, '--voice-id', vid, '--out', wav, '--play'], check=True)
    subprocess.run(['opal', 'listen', 'recognition', 'test-audio', wav, '--no-save-log'], check=True)
"
```

<a id="recipe-10"></a>

#### 10. Voice roulette — user says something, computer says it back in a random voice

*Interfaces: `listen` + `say`.* Capture or supply a spoken recording (or watch a live utterance from `opal listen recognition stream`), extract what the user said, pick a random enabled voice from `opal say voice list`, and parrot the transcript right back in a surprise voice.

```bash
# Transcribe a recorded utterance (or swap in one line from `opal listen recognition stream`)
# and repeat the exact words back in a randomly chosen OPAL Say voice
TRANSCRIPT=$(opal listen recognition test-audio user-utterance.wav --no-save-log \
  | python3 -c "import json, sys; print(json.load(sys.stdin)['transcript'])")

RANDOM_VOICE=$(opal say voice list --enabled \
  | python3 -c "import json, random, sys; print(random.choice(json.load(sys.stdin))['voice_id'])")

opal say generate "$TRANSCRIPT" --voice-id "$RANDOM_VOICE" --play
```

<a id="recipe-11"></a>

#### 11. Voice lab: one trigger phrase across every persona

*Interfaces: `say` + `listen`.* Synthesize the exact same wakeword-prefixed command using every registered persona's bound voice, then run each WAV through `opal listen recognition test-audio --require-wakeword` to verify intent recognition stays rock-solid regardless of speaker timbre or accent.

```bash
# Synthesize the same wakeword + command across personas and verify every one hits `lights.turn_on`
for PERSONA in vox amy jarvis; do
  opal say generate "hey opal, turn on the lights in the kitchen" \
    --persona-id "$PERSONA" \
    --out "/tmp/test-${PERSONA}.wav"
  opal listen recognition test-audio "/tmp/test-${PERSONA}.wav" --require-wakeword --no-save-log
done
```

<a id="recipe-12"></a>

#### 12. Voice lab: espresso speed sweep

*Interfaces: `say` + `listen`.* Sweep `--speed` from a sleepy `0.6x` up to acaffeinated `2.2x` to find the exact speaking rate where your wakeword detector or STT model begins dropping words.

```bash
# Find the breaking point of your STT engine across five speaking rates
for SPEED in 0.6 1.0 1.4 1.8 2.2; do
  opal say generate "hey opal, turn on the lights in the galley" \
    --voice-id en-us-lessac-medium \
    --speed "$SPEED" \
    --out "/tmp/sweep-${SPEED}.wav"
  echo "=== Testing speed ${SPEED}x ==="
  opal listen recognition test-audio "/tmp/sweep-${SPEED}.wav" --require-wakeword --no-save-log
done
```

<a id="recipe-13"></a>

#### 13. Paraphrase and speak

*Interfaces: `listen` + `think` + `say`.* Say something blunt into a recording, let Listen transcribe it, ask Think to paraphrase it into diplomatic Victorian prose (or crisp executive bullet-speak), and have Say deliver the upgraded version aloud.

```bash
# Transcribe -> paraphrase in Think -> speak aloud as Vox
opal listen recognition test-audio raw-rant.wav --no-save-log \
  | opal think ask "Paraphrase the `transcript` field in this JSON into one impeccably polite, diplomatic sentence suitable for a formal email. Output the sentence only." --context - \
  | opal say generate - --persona-id vox --play
```

<a id="recipe-14"></a>

#### 14. Paraphrase factory for intent training

*Interfaces: `think` + `listen`.* Bootstrapping NLU intents by hand gets repetitive fast. Ask Think for ten diverse, colloquial ways a human might ask to turn off the lights, and feed each line straight into `opal listen phrase add`.

```bash
# Generate 8 natural paraphrases in Think and register every one on intent `int-lights-off`
opal think ask "Write 8 natural, distinct ways someone at home might ask to turn off the lights in a {room}. Lowercase, no numbering, no quotes, one phrase per line." \
  | while IFS= read -r PHRASE; do
      [ -n "$PHRASE" ] && opal listen phrase add int-lights-off --phrase "$PHRASE"
    done
```

<a id="recipe-15"></a>

#### 15. The miss whisperer: LLM triage for failed utterances

*Interfaces: `listen` + `think`.* Pull an unrecognized utterance from Listen's miss queue alongside your live intent catalog, ask Think which intent the speaker actually meant, and promote the miss into a permanent training phrase and regression test.

```bash
# Ask Think which existing intent best matches failed utterance `fu-07`, then promote it
INTENTS=$(opal listen intent list)
MISS=$(opal listen data failed-utterance show fu-07)

SUGGESTED_ID=$(opal think ask "Given `miss.transcript` and the `intents` list in context, reply with ONLY the matching intent `id` (or `none`)." \
  --context "{\"miss\":$MISS,\"intents\":$INTENTS}")

[ "$SUGGESTED_ID" != "none" ] && opal listen data failed-utterance promote fu-07 --intent-id "$SUGGESTED_ID" --create-regression
```

<a id="recipe-16"></a>

#### 16. Spoken NLU regression report

*Interfaces: `listen` + `think` + `say`.* Run your entire NLU regression suite after editing slots or phrases, let Think summarize pass/fail counts and call out any broken test case by name, and hear the verdict while your tea steeps.

```bash
# Run regressions -> summarize in one spoken sentence -> play on speakers
opal listen regression run --enabled-only \
  | opal think ask "Summarize this regression test run in at most two spoken sentences: state total passed/failed and name any failed test." --context - \
  | opal say generate - --persona-id amy --play
```

---

<a id="eyes-on-the-property"></a>

### 17–26: Eyes on the Property

<a id="recipe-17"></a>

#### 17. Notify me when you see a target

*Interfaces: `look` + `event` + `say`.* Watch any RTSP camera for a target class (`person`, `dog`, `bear`, `bicycle` — change `TARGET` once) with confidence `>= 0.65`, and announce sightings aloud the moment they enter the frame.

```bash
TARGET="bear"

# 1. Register a spoken alert action for the target class
opal event action add \
  --id "alert-${TARGET}" \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args "[\"say\",\"generate\",\"Heads up. A ${TARGET} was just spotted on the yard camera.\",\"--volume\",\"1.3\",\"--play\"]" \
  --stdin none \
  --description "Announce when ${TARGET} is detected."

# 2. Match high-confidence sightings of TARGET on `vision.yard`
opal event rule add \
  --id "spot-${TARGET}" \
  --topic vision.yard \
  --conditions "[
    {\"path\":\"data.event_type\",\"operator\":\"eq\",\"value\":\"detection\"},
    {\"path\":\"data.detections[0].class_name\",\"operator\":\"eq\",\"value\":\"${TARGET}\"},
    {\"path\":\"data.detections[0].confidence\",\"operator\":\"gte\",\"value\":0.65}
  ]" \
  --actions "[\"alert-${TARGET}\"]"

# 3. Start the yard stream and pipe SSE events to Event
opal look stream start --source rtsp://192.168.1.42:554/stream1 --engine-id yolo --model-id yolo11n --idempotency-key yard-watch
opal look stream watch str-yard | while IFS= read -r ev; do
  [ -n "$ev" ] && opal event data event publish --topic vision.yard --source opal-look --data "$ev"
done
```

<a id="recipe-18"></a>

#### 18. Tell me when there is a package on the porch

*Interfaces: `look` + `event` + `say`.* Point a porch stream at a model trained with a `package` (or `suitcase`/`backpack`/`box`) class, snap an annotated JPEG for proof of delivery, and announce arrival over the house speakers.

```bash
# 1. Start the porch detection stream with bounding-box rendering enabled
opal look stream start --source rtsp://192.168.1.41:554/stream1 --engine-id yolo --model-id porch-packages-v2 --annotate --idempotency-key porch-pkg

# 2. Register actions to save an annotated delivery photo and announce the package
opal event action add \
  --id snap-package \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["look","stream","snapshot","str-porch-pkg","--annotated","--out","/var/tmp/latest-package.jpg"]' \
  --stdin none \
  --description "Save an annotated snapshot of the delivered package."

opal event action add \
  --id say-package \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","There is a package on the front porch.","--persona-id","vox","--play"]' \
  --stdin none \
  --description "Announce a package on the porch."

# 3. Trigger both actions whenever `package` is detected, then start the SSE bridge
opal event rule add \
  --id porch-package-rule \
  --topic porch.detection \
  --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"package"}]' \
  --actions '["snap-package","say-package"]'

opal look stream watch str-porch-pkg | while IFS= read -r ev; do
  [ -n "$ev" ] && opal event data event publish --topic porch.detection --source opal-look --data "$ev"
done
```

<a id="recipe-19"></a>

#### 19. "Who is at the front door?"

*Interfaces: `listen` + `event` + `think` + `look` + `say`.* All five services in one loop: ask out loud who is outside; Listen matches `door.check`; Event wakes Think; Think invokes an Event HTTP action that runs `POST /api/v1/predict` against the live stream's `/snapshot` URL, reads the detection list, and answers through `speak`.

```bash
# 1. Ensure the front-door stream is running (even video-only works for `/snapshot`!)
opal look stream start --source rtsp://192.168.1.40:554/stream1 --idempotency-key door-cam

# 2. Teach Listen the question
opal listen intent add \
  --name door.check \
  --description "Check what is currently in front of the door camera" \
  --phrases '["who is at the front door","check the front door","is anyone outside"]'

# 3. Register an Event HTTP action Think can call to run YOLO on the live snapshot URL
opal event action add \
  --id inspect-front-door \
  --type http \
  --method POST \
  --url http://127.0.0.1:8082/api/v1/predict \
  --body-mode template \
  --body '{"engine_id":"yolo","model_id":"yolo11n","source":"http://127.0.0.1:8082/api/v1/stream/str-door-cam/snapshot","confidence":0.45}' \
  --timeout-seconds 15 \
  --description "Run YOLO object detection on the current front-door camera frame." \
  --keywords '["camera","door","vision","detect"]'

# 4. Register the Think task launcher and bind it to `door.check`
opal event action add \
  --id think-door-check \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"prompt":"Execute the inspect-front-door action, inspect its result detections, and invoke the speak action to tell me in one natural sentence who or what is at the front door.","max_steps":5}' \
  --description "Ask Think to inspect the front door and report aloud."

opal event rule add \
  --id door-check-rule \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"door.check"}]' \
  --actions '["think-door-check"]'
```

<a id="recipe-20"></a>

#### 20. Polite porch greeter with evidence snapshot

*Interfaces: `look` + `event` + `say`.* When a person steps onto the porch after midnight, archive a clean high-res frame and greet them in a calm, unmistakable British baritone so honest visitors feel welcomed and porch pirates rethink their life choices.

```bash
opal event action add \
  --id snap-visitor \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["look","stream","snapshot","str-door-cam","--out","/var/tmp/porch-visitor.jpg"]' \
  --stdin none \
  --description "Save a clean JPEG snapshot of the porch visitor."

opal event action add \
  --id greet-visitor \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Good evening. The front porch camera is active. How may we help you?","--persona-id","vox","--play"]' \
  --stdin none \
  --description "Politely greet a porch visitor."

opal event rule add \
  --id late-visitor-rule \
  --topic porch.detection \
  --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' \
  --actions '["snap-visitor","greet-visitor"]'
```

<a id="recipe-21"></a>

#### 21. "Off the couch, Biscuit!" — dynamic pet scolder

*Interfaces: `look` + `event` + `think` + `say`.* Static recordings lose their power over a clever dog by Tuesday. Whenever `dog` appears on the living-room stream, trigger Think to improvise a brand-new, affectionate-but-firm reprimand and speak it out loud.

```bash
opal event action add \
  --id scold-biscuit \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"prompt":"Our golden retriever Biscuit was just detected on the living-room couch again. Invent one fresh, funny, affectionate-but-firm sentence telling Biscuit to get off the cushions, and say it aloud using the speak action.","max_steps":4}' \
  --description "Have Think improvise a fresh couch-patrol warning for Biscuit."

opal event rule add \
  --id biscuit-couch-rule \
  --topic livingroom.detection \
  --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"dog"}]' \
  --actions '["scold-biscuit"]'
```

<a id="recipe-22"></a>

#### 22. Driveway capacity counter

*Interfaces: `look` + `think` + `say`.* Grab a live frame of the driveway, run `predict image`, and let Think count vehicles (`car`, `truck`, `motorcycle`) and announce how many guest parking spots remain.

```bash
opal look stream snapshot str-driveway --out /tmp/driveway.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source /tmp/driveway.jpg --confidence 0.45 \
  | opal think ask "Our driveway holds 4 vehicles. Count every car, truck, or motorcycle in `detections` and state in one sentence how many vehicles are parked and how many spots remain." --context - \
  | opal say generate - --play
```

<a id="recipe-23"></a>

#### 23. Camera-down watchdog

*Interfaces: `look` + `event` + `say`.* Security cameras that silently drop offline are worse than no cameras at all. Match `status == "failed"` on republished stream events so the house tells you the moment an RTSP feed dies.

```bash
opal event action add \
  --id say-cam-failed \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Warning: camera stream {{data.stream_id}} has failed and needs attention.","--play"]' \
  --stdin none \
  --description "Announce a failed Look camera stream."

opal event rule add \
  --id stream-failure-watchdog \
  --topic 'vision.*' \
  --conditions '[{"path":"data.status","operator":"eq","value":"failed"}]' \
  --actions '["say-cam-failed"]'
```

<a id="recipe-24"></a>

#### 24. Voice-triggered photo booth ("Say cheese")

*Interfaces: `listen` + `event` + `look` + `say`.* Say *"Hey OPAL, take a group photo"* — Event announces a quick verbal cue, grabs a clean frame from the living-room stream, and confirms the shot is saved.

```bash
opal listen intent add \
  --name camera.photobooth \
  --description "Snap a family or whiteboard photo from the room camera" \
  --phrases '["say cheese","take a group photo","snap a picture"]'

opal event action add \
  --id snap-photobooth \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["look","stream","snapshot","str-livingroom","--no-annotated","--out","/var/tmp/photobooth-latest.jpg"]' \
  --stdin none \
  --description "Capture a clean JPEG from the living-room stream."

opal event action add \
  --id confirm-photo \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Got it. Photo saved.","--play"]' \
  --stdin none \
  --description "Confirm the photo capture aloud."

opal event rule add \
  --id photobooth-rule \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"camera.photobooth"}]' \
  --actions '["snap-photobooth","confirm-photo"]'
```

<a id="recipe-25"></a>

#### 25. Nightly front-yard visitor digest

*Interfaces: `look` + `event` + `think` + `say`.* Query the day's stored `vision.front_door` events from Event, pass the bounded array to Think as untrusted context, and listen to a two-sentence evening security recap.

```bash
opal event data event list --topic vision.front_door --limit 200 \
  | opal think ask "Summarize today's front-door detections in two calm sentences: mention what classes appeared, approximate peak activity times, and whether anything looked unusual." --context - \
  | opal say generate - --persona-id vox --play
```

<a id="recipe-26"></a>

#### 26. Workshop safety-glasses officer

*Interfaces: `look` + `event` + `say`.* Watch the garage workbench stream and issue a friendly reminder about eye protection whenever a human steps up to the table saw.

```bash
opal event action add \
  --id remind-goggles \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Friendly workshop reminder: put your safety glasses on before flipping that switch.","--play"]' \
  --stdin none \
  --description "Remind woodworker to wear eye protection."

opal event rule add \
  --id workshop-ppe-rule \
  --topic vision.workshop \
  --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' \
  --actions '["remind-goggles"]'
```

---

<a id="classroom-games-and-storytelling"></a>

### 27–36: Classroom, Games & Storytelling

<a id="recipe-27"></a>

#### 27. Make up a story about...

*Interfaces: `think` + `say`.* Pass any imaginative topic to Think and pipe the finished story straight into `opal say stream - --play` so progressive PCM narration begins immediately without waiting for the final sentence to synthesize.

```bash
TOPIC="a retired submarine captain who opens a tiny bakery on Mars"

opal think ask "Make up a cozy, two-minute story about ${TOPIC}. Write for spoken narration with no markdown formatting." \
  --timeout-seconds 240 \
  | opal say stream - --persona-id vox --speed 0.92 --play
```

<a id="recipe-28"></a>

#### 28. Hands-free story time on any spoken topic

*Interfaces: `listen` + `event` + `think` + `say`.* Let anyone in the room say *"Hey OPAL, make up a story about a clockwork owl"* — Listen captures the full transcript, Event triggers Think, and Think narrates the story through `speak`.

```bash
opal listen intent add \
  --name story.request \
  --description "Generate and narrate an original story on a spoken subject" \
  --phrases '["make up a story about","tell me a story about","bedtime story about"]'

opal event action add \
  --id narrate-story \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"prompt":"A listener asked: {{data.transcript}}. Write an original 90-second story on that exact subject in plain spoken prose, then read it aloud with the speak action.","timeout_seconds":300,"max_steps":4}' \
  --description "Ask Think to invent and speak a story from a voice prompt."

opal event rule add \
  --id voice-storytime \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"story.request"}]' \
  --actions '["narrate-story"]'
```

<a id="recipe-29"></a>

#### 29. Spelling Bee

*Interfaces: `think` + `say` + `listen`.* Run a real multi-turn Spelling Bee: a Think session picks an age-appropriate word and remembers it across turns, Say pronounces the word slowly and uses it in a sentence, Listen transcribes your spoken letter-by-letter attempt, and Think judges your spelling and awards points.

```bash
# 1. Start a dedicated Spelling Bee session
opal think session add --title "Saturday Spelling Bee"

# 2. Judge announces the word and uses it in a sentence (without revealing the spelling in audio!)
opal think chat "You are a friendly Spelling Bee pronouncer. Pick a challenging 8-to-11-letter English word, state the word, give its definition, and use it in a sentence. Do NOT spell it out." \
  --session-id ses-bee \
  | opal say generate - --voice-id en-us-lessac-medium --speed 0.85 --play

# 3. Record your spoken spelling into `attempt.wav`, transcribe with Listen, and let Think grade it
opal listen recognition test-audio attempt.wav --no-save-log \
  | opal think chat "The JSON context holds the contestant's spoken transcript attempting to spell your word. Judge whether the letter sequence is right, state the running score, spell the word clearly for confirmation, and announce the next word." \
      --session-id ses-bee --context - \
  | opal say generate - --voice-id en-us-lessac-medium --speed 0.90 --play
```

<a id="recipe-30"></a>

#### 30. Verbal pub-quiz with session scorekeeping

*Interfaces: `think` + `say` + `listen`.* Turn your living room into trivia night: Think tracks five rounds of questions and scores inside a session while Listen grades spoken team answers.

```bash
opal think session add --title "Pub Quiz: Science & History"

# Ask Round 1
opal think chat "You are a witty pub-quiz host. Ask Question 1 of 5 on science or history. Keep it to two sentences and hold back the answer." \
  --session-id ses-quiz \
  | opal say generate - --persona-id vox --play

# Grade Team A's spoken answer and immediately tee up Question 2
opal listen recognition test-audio team-answer.wav --no-save-log \
  | opal think chat "Grade `transcript` in context against your last question, announce the updated score in one sentence, and ask Question 2." \
      --session-id ses-quiz --context - \
  | opal say generate - --persona-id vox --play
```

<a id="recipe-31"></a>

#### 31. Timed multiplication drill with event timestamps

*Interfaces: `think` + `say` + `listen` + `event`.* Because every normalized Event carries an authoritative ISO `timestamp`, a Think session can enforce a real five-second shot clock on spoken mental-math answers.

```bash
opal think session add --title "8x Speed Drill"

opal listen intent add \
  --name drill.answer \
  --description "Spoken numeric answer during a math drill" \
  --phrases '["it is","the answer is","equals"]'

opal event action add \
  --id grade-timed-math \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"session_id":"ses-math8","prompt":"Student said: {{data.transcript}}. Compare the event timestamp in context with when you asked the problem: if wrong OR slower than 6 seconds, mark it missed. Speak a brief verdict and the next 8-times-table question via the speak action.","context":"{{event}}","max_steps":4}' \
  --description "Grade spoken math answers against accuracy and elapsed time."

opal event rule add \
  --id math-drill-loop \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"drill.answer"}]' \
  --actions '["grade-timed-math"]'

# Kick off Question 1
opal listen recognition start
opal think chat "Start a 5-question speed drill on the 8 times table. Speak Question 1 aloud using the speak action." --session-id ses-math8
```

<a id="recipe-32"></a>

#### 32. Socratic word-problem math tutor

*Interfaces: `think` + `say` + `listen`.* Instead of blurting out the final number when a student stumbles, Think diagnoses *which reasoning step* went sideways and speaks a Socratic hint.

```bash
opal think session add --title "Fractions Tutor"

opal think chat "Pose one practical cooking word problem involving multiplying fractions. Do not give the answer." \
  --session-id ses-tutor \
  | opal say generate - --speed 0.9 --play

opal listen recognition test-audio student-work.wav --no-save-log \
  | opal think chat "Inspect `transcript` in context. If correct, congratulate the student. If wrong, do NOT reveal the answer — ask one guiding question that points at the first arithmetic slip." \
      --session-id ses-tutor --context - \
  | opal say generate - --speed 0.9 --play
```

<a id="recipe-33"></a>

#### 33. Foreign-language pronunciation coach

*Interfaces: `think` + `say` + `listen`.* Think writes a useful travel sentence in Spanish, Say models it with the native `es-es-davefx-medium` voice, and Listen transcribes your repetition so Think can coach any mispronounced words.

```bash
# 1. Generate and hear a Spanish travel phrase in a native Spanish TTS voice
PHRASE_ES=$(opal think ask "Give one polite Spanish sentence for ordering two coffees and asking for the check. Output Spanish text only.")
opal say generate "$PHRASE_ES" --voice-id es-es-davefx-medium --speed 0.85 --play

# 2. Compare your recorded repetition against the target sentence
opal listen recognition test-audio my-spanish-attempt.wav --no-save-log \
  | opal think ask "Target Spanish phrase: '$PHRASE_ES'. Compare it with `transcript` in context and give one encouraging pronunciation tip in English." --context - \
  | opal say generate - --voice-id en-us-lessac-medium --play
```

<a id="recipe-34"></a>

#### 34. Spoken Twenty Questions

*Interfaces: `think` + `say` + `listen`.* Think secretly chooses an everyday household object at the start of a session and answers only `"Yes"`, `"No"`, or `"Sometimes"` while counting down your twenty guesses.

```bash
opal think session add --title "Twenty Questions"

opal think chat "Secretly pick a physical object found in a kitchen. Tell me only 'I have picked an object — ask Question 1 of 20.'" \
  --session-id ses-20q \
  | opal say generate - --persona-id amy --play

opal listen recognition test-audio question-01.wav --no-save-log \
  | opal think chat "Answer the yes/no question in `transcript` honestly, state how many questions remain, and celebrate if I guessed the exact object." \
      --session-id ses-20q --context - \
  | opal say generate - --persona-id amy --play
```

<a id="recipe-35"></a>

#### 35. Tabletop RPG Dungeon Master

*Interfaces: `think` + `say` + `listen` + `event`.* Run a voice-driven micro-dungeon: players declare actions out loud, Event logs every move on `game.dnd.turn` and wakes the Think campaign session, and the DM narrates consequences through `speak`.

```bash
opal think session add --title "Crypt of the Rustaveli Clockmaker"

opal listen intent add \
  --name rpg.action \
  --description "A player's spoken move in the tabletop adventure" \
  --phrases '["i search the","i open the","i cast","i attack","i ask the"]'

opal event action add \
  --id dm-turn \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"session_id":"ses-dnd","prompt":"Player declares: {{data.transcript}}. Adjudicate the move fairly in three atmospheric sentences, end with 'What do you do next?', and narrate it aloud via the speak action.","max_steps":4}' \
  --description "Advance the tabletop campaign by one spoken player action."

opal event rule add \
  --id dnd-voice-turn \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"rpg.action"}]' \
  --actions '["dm-turn"]'
```

<a id="recipe-36"></a>

#### 36. Homework helper that hints without spoiling

*Interfaces: `look` + `think` + `say`.* Snap a frame of the desk camera over a science diagram or lab setup, detect the objects present, and ask Think for a conceptual study hint.

```bash
opal look stream snapshot str-desk --out /tmp/desk-diagram.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source /tmp/desk-diagram.jpg \
  | opal think ask "Based on the objects detected on the student's desk in context, give a two-sentence study prompt without giving away textbook answers." --context - \
  | opal say generate - --play
```

---

<a id="smart-home-and-ambient-automation"></a>

### 37–43: Smart Home & Ambient Automation

<a id="recipe-37"></a>

#### 37. Room-aware lights with spoken confirmation

*Interfaces: `listen` + `event` + `say`.* One matched intent dispatches two independent concurrent actions in Event: an HTTP call to your local lighting bridge templated with `{{data.slot_values.room}}` and a spoken confirmation so you know which room switched.

```bash
opal event action add \
  --id bridge-lights-on \
  --type http \
  --method POST \
  --url 'http://127.0.0.1:8123/api/rooms/{{data.slot_values.room}}/lights/on' \
  --body-mode none \
  --timeout-seconds 5 \
  --description "Switch on room lights via local home bridge."

opal event action add \
  --id confirm-room-lights \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Turning on the {{data.slot_values.room}} lights.","--play"]' \
  --stdin none \
  --description "Confirm room light activation aloud."

opal event rule add \
  --id room-lights-rule \
  --topic opal.listen.intent.match \
  --conditions '[
    {"path":"data.intent_name","operator":"eq","value":"lights.turn_on"},
    {"path":"data.slot_values.room","operator":"exists","value":true}
  ]' \
  --actions '["bridge-lights-on","confirm-room-lights"]'
```

<a id="recipe-38"></a>

#### 38. Smart doorbell with snapshot and chime

*Interfaces: `event` + `look` + `say`.* Any Zigbee button, ESP32, or script that `POST`s `home.doorbell.pressed` instantly becomes a smart intercom that saves a porch photo and announces which door rang.

```bash
opal event action add \
  --id snap-doorbell \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["look","stream","snapshot","str-door-cam","--out","/var/tmp/doorbell-press.jpg"]' \
  --stdin none \
  --description "Capture porch frame on doorbell press."

opal event action add \
  --id say-doorbell \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Someone just pressed the {{data.door}} doorbell.","--persona-id","vox","--play"]' \
  --stdin none \
  --description "Announce which doorbell was pressed."

opal event rule add \
  --id smart-doorbell-rule \
  --topic home.doorbell.pressed \
  --conditions '[]' \
  --actions '["snap-doorbell","say-doorbell"]'

# Test it without walking outside
opal event data event publish --topic home.doorbell.pressed --source porch-zigbee --data '{"door":"front"}'
```

<a id="recipe-39"></a>

#### 39. Thirsty-garden soil sensor narrator

*Interfaces: `event` + `think` + `say`.* Raw numbers (`13.8%`) are easy to ignore; a dry houseplant pleading its case out loud gets watered. Route low-moisture readings through Think to `speak`.

```bash
opal event action add \
  --id narrate-thirsty-bed \
  --type http \
  --method POST \
  --url http://127.0.0.1:8083/api/v1/task/ \
  --body-mode template \
  --body '{"prompt":"Sensor event in context shows low soil moisture. Invoke the speak action with one witty sentence naming the plant bed and its exact moisture percentage.","context":"{{event}}","max_steps":3}' \
  --description "Turn low-moisture sensor events into spoken reminders."

opal event rule add \
  --id thirsty-garden-rule \
  --topic 'garden.soil.*' \
  --conditions '[{"path":"data.moisture_pct","operator":"lt","value":18}]' \
  --actions '["narrate-thirsty-bed"]'

opal event data event publish --topic garden.soil.moisture --source patio-esp32 --data '{"bed":"basil","moisture_pct":13.8}'
```

<a id="recipe-40"></a>

#### 40. Water-leak alarm and insurance snapshot

*Interfaces: `event` + `look` + `say`.* When a utility-room moisture puck trips `home.leak.detected`, blast a max-volume spoken alert and immediately snapshot the utility-room camera stream for your plumber and insurer.

```bash
opal event action add \
  --id alarm-leak \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Urgent alert! Water leak detected near the {{data.sensor}}. Shut off the main valve.","--volume","2.0","--play"]' \
  --stdin none \
  --description "High-volume spoken water-leak alarm."

opal event action add \
  --id snap-utility-room \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["look","stream","snapshot","str-utility","--out","/var/tmp/leak-evidence.jpg"]' \
  --stdin none \
  --description "Capture utility-room camera frame on leak alert."

opal event rule add \
  --id leak-emergency-rule \
  --topic home.leak.detected \
  --conditions '[]' \
  --actions '["alarm-leak","snap-utility-room"]'
```

<a id="recipe-41"></a>

#### 41. Household dinner bell

*Interfaces: `listen` + `event` + `say`.* Say *"Hey OPAL, ring the dinner bell"* in the kitchen at normal volume, and let Event broadcast an authoritative announcement at `1.6x` gain.

```bash
opal listen intent add \
  --name home.dinner_bell \
  --description "Call the household to the table" \
  --phrases '["ring the dinner bell","call everyone for dinner","dinner is on the table"]'

opal event action add \
  --id broadcast-dinner \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/opal \
  --args '["say","generate","Attention household: dinner is served while it is still hot.","--persona-id","vox","--volume","1.6","--play"]' \
  --stdin none \
  --description "Broadcast the dinner announcement."

opal event rule add \
  --id dinner-bell-rule \
  --topic opal.listen.intent.match \
  --conditions '[{"path":"data.intent_name","operator":"eq","value":"home.dinner_bell"}]' \
  --actions '["broadcast-dinner"]'
```

<a id="recipe-42"></a>

#### 42. Morning porch and day-ahead briefing

*Interfaces: `think` + `event` + `look` + `say`.* One scheduled cron line at 7:30 AM: Think invokes `inspect-front-door` (from Recipe 19) through Event, checks overnight `home.*` events, and delivers a concise spoken morning report via `speak`.

```bash
OVERNIGHT=$(opal event data event list --topic 'home.doorbell.pressed' --limit 20)

opal think task add \
  "Good-morning briefing: call the inspect-front-door action to see what is on the porch right now, combine that with the overnight doorbell events in context, and invoke the speak action with a cheerful two-sentence summary." \
  --context "{\"overnight_doorbells\":$OVERNIGHT}" \
  --max-steps 6 \
  --idempotency-key "briefing-$(date +%F)" \
  --wait
```

<a id="recipe-43"></a>

#### 43. Synchronized goodnight mode

*Interfaces: `say` + `listen` + `event`.* Activate quiet night profiles on Say and Listen, pause noisy daytime yard alerts in Event, and whisper confirmation that the house is tucked in.

```bash
opal say profile activate bedtime
opal listen profile activate night-mode
opal event rule update spot-bear --no-enabled
opal event data event publish --topic home.mode.changed --source cli --data '{"mode":"goodnight"}'
opal say generate "Goodnight mode active. Daytime yard alerts are muted." --play
```

---

<a id="developer-workflow-and-fleet-operations"></a>

### 44–50: Developer Workflow & Fleet Operations

<a id="recipe-44"></a>

#### 44. Speaking CI/CD build announcer

*Interfaces: `event` + `say`.* Route any `ci.*` event carrying `data.text` straight into the `speak` action so long test suites or Docker builds announce completion while you read a paper across the room.

```bash
opal event rule add \
  --id ci-voice-notifier \
  --topic 'ci.*' \
  --conditions '[{"path":"data.text","operator":"exists","value":true}]' \
  --actions '["speak"]'

# Drop this at the tail of any long build script:
npm run check \
  && opal event data event publish --topic ci.contracts.passed --source local-ci --data '{"text":"All OpenAPI contracts validated and bundled cleanly."}' \
  || opal event data event publish --topic ci.contracts.failed --source local-ci --data '{"text":"Contract check failed. Step away from git push."}'
```

<a id="recipe-45"></a>

#### 45. Automated log triage across services

*Interfaces: `look` + `listen` + `think` + `say`.* Collect the recent service logs from Look and Listen, hand both tails to Think as structured context, and hear a single-sentence diagnosis of warnings or errors.

```bash
LOOK_LOG=$(opal look service log --lines 40)
LISTEN_LOG=$(opal listen service log --lines 40)

opal think ask "Inspect these two OPAL service log tails. In one spoken sentence, name the most urgent error or warning — or confirm both logs look clean." \
  --context "{\"opal_look\":$LOOK_LOG,\"opal_listen\":$LISTEN_LOG}" \
  | opal say generate - --persona-id amy --play
```

<a id="recipe-46"></a>

#### 46. Post-mortem diagnosis on a failed execution

*Interfaces: `event` + `think` + `say`.* When an Event action fails (`exit_code != 0`, `template_error`, or `input_validation_failed`), pipe its full `Execution` record into Think for an instant root-cause explanation and fix.

```bash
# Grab the latest failed or dropped execution and have Think explain how to fix it
opal event data execution show exe-failed-42 \
  | opal think ask "Analyze this OPAL Event Execution record (`status`, `error_code`, `error_message`, `stderr`). Explain why it failed and give the exact fix in two concise sentences." --context - \
  | opal say generate - --play
```

<a id="recipe-47"></a>

#### 47. Desk guardian: alert if your laptop leaves without you

*Interfaces: `look` + `think` + `say`.* Snapshot an overhead desk stream, run YOLO object detection, and trigger a spoken warning if no `laptop` appears in the detections.

```bash
opal look stream snapshot str-office-desk --out /tmp/desk-check.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source /tmp/desk-check.jpg --confidence 0.50 \
  | opal think ask "Check `detections` in context: if at least one `laptop` is present, reply ONLY with `Laptop present.` Otherwise reply with an urgent sentence warning that the laptop is missing from the desk." --context - \
  | opal say generate - --play
```

<a id="recipe-48"></a>

#### 48. Start all services

*Interfaces: `event` + `say` + `look` + `look-yolo` + `think` + `listen`.* Bring up the entire OPAL fleet in dependency order (Event bus first, TTS and vision adapters next, Think reasoning, and Listen's microphone pipeline last), verify `.ready == true` across every health report, and announce boot completion out loud.

```bash
# 1. Start every module in dependency order (--append preserves prior log history)
opal event service start --append
opal say service start --append
opal look-yolo service start --append
opal look service start --append
opal think service start --append
opal listen service start --append

# 2. Verify health across all modules
opal event info health
opal say info health
opal look-yolo info health
opal look info health
opal think info health
opal listen info health

# 3. Record fleet boot on the event bus and announce readiness
opal event data event publish --topic ops.fleet.started --source boot-script --data '{"modules":6}'
opal say generate "All OPAL ecosystem services are online and ready." --persona-id jarvis --play
```

<a id="recipe-49"></a>

#### 49. Backup everything

*Interfaces: `say` + `listen` + `look` + `look-yolo` + `think` + `event`.* Save both server-managed recovery snapshots (`config save` with no `--out`) and portable version-controlled YAML files (`--out`), validate every exported snapshot against its module contract, and ask Think to audit cross-service references.

```bash
mkdir -p backups/$(date +%F)
DIR="backups/$(date +%F)"

# 1. Save a managed recovery snapshot AND export a portable YAML file per module
for SVC in event say listen look look-yolo think; do
  opal "$SVC" config save
  opal "$SVC" config save --out "${DIR}/${SVC}.yaml"
  opal "$SVC" config validate --in "${DIR}/${SVC}.yaml"
done

# 2. Ask Think to cross-check Event rules against defined Event actions
opal think ask "Audit this exported opal-event snapshot: confirm every action ID referenced in rules exists in actions, in one sentence." \
  --context "@${DIR}/event.yaml" \
  | opal say generate - --persona-id amy --play
```

<a id="recipe-50"></a>

#### 50. Graceful fleet shutdown with audit marker

*Interfaces: `say` + `event` + `listen` + `look` + `look-yolo` + `think`.* Announce maintenance before muting your own vocal cords, write a permanent `ops.fleet.stopping` breadcrumb into Event, stop active capture/inference producers first, and stop `opal event` last so every upstream departure is recorded cleanly.

```bash
# 1. Speak the sign-off while Say is still running
opal say generate "OPAL fleet entering scheduled maintenance. Standing down all faculties." --persona-id vox --play

# 2. Record the shutdown marker in Event before tearing down producers
opal event data event publish --topic ops.fleet.stopping --source ops-cli --data '{"reason":"scheduled maintenance"}'

# 3. Stop edge capture and reasoning first, adapters next, and the Event bus last
opal listen recognition stop
opal listen service stop
opal look service stop
opal look-yolo service stop
opal think service stop
opal say service stop
opal event service stop
```


