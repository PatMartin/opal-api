# OPAL CLI — a Typer surface for five OpenAPI contracts

> **Status.** This document describes a *hypothetical* Typer-based CLI
> composed from the five OpenAPI contracts in `openapi/`. It is a design
> proposal, not a claim that an `opal` binary ships today.
>
> **Naming authority.** Only `opal_look.yaml` and `opal_think.yaml`
> declare `x-opal-cli` metadata. Command names for those two services are
> normative. `opal_event.yaml`, `opal_listen.yaml`, and `opal_say.yaml`
> carry no CLI metadata, so the command names proposed here for those three
> services are a *consistent mapping* from their REST routes — not a
> contract requirement. Wherever a flag maps to a real schema field, query
> parameter, or enum value, that mapping is grounded in the contract.
>
> **Side-effecting operations** (shell/HTTP/python actions, camera streams,
> event clearing, configuration import, device control) should require
> explicit confirmation and never be retried blindly.

## At a glance

| Sub-app | Contract | One-line role | CLI metadata |
|---|---|---|---|
| `opal event` | `opal_event.yaml` | Event bus, rules, actions, executions | proposed |
| `opal listen` | `opal_listen.yaml` | Wakeword/STT, intents, slots, regression | proposed |
| `opal look` | `opal_look.yaml` | Cameras, models, pipelines, observations | **normative** |
| `opal say` | `opal_say.yaml` | TTS engines, voices, profiles, generation | proposed |
| `opal think` | `opal_think.yaml` | Durable LLM tasks, sessions, model catalog | **normative** |

Each sub-app is independently installable and usable. The suite does not
require all five services to be running.

## Install and shared surface

Hypothetical install:

```console
python -m pip install opal-cli
opal --help
```

Configure one URL and one token per service. The CLI should accept
`--url`/`--token` overrides and read `OPAL_<SERVICE>_URL` / `OPAL_TOKEN`
from the environment.

Shared kernel conventions every sub-app inherits (from
`openapi/shared/opal_kernel.yaml`):

| Option | Contract behavior |
|---|---|
| `--session-id`, `--transaction-id`, `--request-id`, `--causation-id` | The four `X-Opal-*` correlation headers. Preserve a transaction ID across a compound workflow for tracing. |
| `--if-match ETAG` | Strong-ETag precondition on protected mutations. Missing → 428; stale → 412. Safe pattern: fetch the resource, read its ETag, then mutate. |
| `--cursor`, `--limit` | Cursor pagination where the endpoint supports it. A cursor is bound to its filters; do not reuse it after changing filters. |
| `--json` | Proposed output affordance for scripting. Response/error envelopes are API-defined. |

Every sub-app exposes the kernel health and settings commands:

```text
opal <service> health
opal <service> health live
opal <service> health ready
opal <service> settings list
opal <service> settings show <key>
opal <service> settings set <key> <value> --if-match <etag>
opal <service> settings remove <key> --if-match <etag>
```

Settings responses mask secrets; configuration exports exclude secrets
and history. Backup routes (list/create/download/restore/delete plus
portable export/validate/import) vary slightly per service — use the
service's own route names.

---

# `opal event` — event bus and automation

## What it does alone

EVENT is a small event-driven automation service. Clients publish JSON
events on a topic; rules select topics and evaluate ANDed conditions;
registered actions run; execution records provide an audit trail. It does
not need LISTEN, LOOK, SAY, or THINK to receive events or run its own
actions.

## Command reference

Proposed command groups mapped to REST routes:

| Command | Route | Key inputs |
|---|---|---|
| `event publish` | `POST /api/v1/events/` | Body: `topic` + `data`, optional `source`/`id`/`timestamp`. |
| `event list` | `GET /api/v1/events/` | `--topic`, `--source`, `--from`, `--to`, `--cursor`, `--limit`. |
| `event clear` | `DELETE /api/v1/events/` | Deletes stored events. |
| `event show <id>` / `event delete <id>` | `GET`/`DELETE /api/v1/events/{event_id}` | Event ID. |
| `event topics` | `GET /api/v1/topics/` | Observed topic names. |
| `event rules list` / `event rules add` | `GET`/`POST /api/v1/rules/` | Rule: `id`, `enabled`, `topic`, `conditions`, `actions`. |
| `event rules show` / `update` / `delete <id>` | `GET`/`PATCH`/`DELETE /api/v1/rules/{rule_id}` | PATCH uses `If-Match`. |
| `event rules test <id>` | `POST /api/v1/rules/{rule_id}/test` | Evaluate a candidate event without executing actions. |
| `event actions list` / `add` | `GET`/`POST /api/v1/actions/` | Action variants: shell, HTTP, python. |
| `event actions show` / `update` / `delete <id>` | `GET`/`PATCH`/`DELETE /api/v1/actions/{action_id}` | Delete only valid for unused actions. |
| `event actions execute <id>` | `POST /api/v1/actions/{action_id}/execute` | Manually run a registered action. |
| `event executions list` | `GET /api/v1/executions/` | `--status`, `--rule-id`, `--action-id`, `--event-id`, `--cursor`, `--limit`. |
| `event executions show <id>` | `GET /api/v1/executions/{execution_id}` | Execution ID. |
| `event stats` | `GET /api/v1/stats/` | Event and execution counters. |

Condition operators (contract enum): `eq`, `ne`, `gt`, `gte`, `lt`,
`lte`, `in`, `not_in`, `exists`, `contains`. Conditions are ANDed.

Action variants and their key fields:
- **shell**: `mode`, `executable` or `script-path`, timeout, options.
- **http**: `method`, `url`, headers, body mode.
- **python**: `module`, `function`, timeout.
- All variants may carry `description`, `input_schema`, `keywords`,
  `suggested_prompts` for discovery.

The wire event is a topic + JSON body. ZeroMQ transport uses exactly two
frames (topic frame + JSON body); the CLI does not expose an undocumented
third frame.

## Standalone recipe: threshold alert

```console
opal event actions show page-on-call
opal event rules add --id hot-room --topic 'sensor.*' \
  --condition 'data.temperature gt 30' --action page-on-call
opal event rules test hot-room \
  --event '{"topic":"sensor.lab","data":{"temperature":33.2}}'
opal event publish sensor.lab '{"temperature":33.2}' --source bench-pi
opal event executions list --rule-id hot-room --limit 20
```

---

# `opal listen` — voice recognition and vocabulary

## What it does alone

LISTEN is a standalone wakeword/STT/intent/slot service. It classifies
text without an audio device, recognizes live speech through its
configured audio pipeline, defines wakewords/intents/slots/profiles, and
improves recognition from failed-utterance logs and regression tests.
Event publication is a configurable integration, not a prerequisite.

## Command reference

| Command | Route family | Key inputs |
|---|---|---|
| `listen wakewords list/add/show/update/remove` | `/api/v1/wakewords/` + item | `name`, `enabled`, `confidence_threshold`. |
| `listen intents list/add/show/update/remove` | `/api/v1/intents/` + item | `name`, `description`, `enabled`, `confidence_threshold`, optional phrases. |
| `listen intents phrases <intent>` | `/api/v1/intents/{intent_id}/phrases` + item | Phrase text. |
| `listen slots list/add/show/update/remove` | `/api/v1/slots/` + item | `name`, `slot_type`, optional description. |
| `listen slots values <slot>` | `/api/v1/slots/{slot_id}/values` + item | Canonical string values. |
| `listen slots aliases <slot> <value>` | aliases collection + item | Alternative spoken forms. |
| `listen profiles list/add/show/update/remove/activate` | `/api/v1/profiles/` + item + activate | Name, active state, wakeword names, enabled intents/slots, confidence thresholds, VAD settings. |
| `listen recognition test-text TEXT` | `POST /api/v1/recognition/test_text` | `text`; optional `save_log`. **Diagnostic only — never publishes events.** |
| `listen recognition test-audio FILE` | `POST /api/v1/recognition/test_audio` | Multipart `file`; `save_log`, `require_wakeword`. **Diagnostic only.** |
| `listen recognition start/stop/status` | `/start`, `/stop`, `/status` | Start/stop the active pipeline; status reports state/metrics. |
| `listen recognition stream` | `GET /api/v1/recognition/stream` | Optional `debug`; streaming response. |
| `listen logs list/show/count` | `/api/v1/logs/` + count + item | `--intent-name`, `--matched`, `--cursor`, `--limit`. |
| `listen failed list/add/show/update/remove/promote` | `/api/v1/failed_utterances/` + item + promote | `--reviewed`, `--promoted`; promote accepts intent name and optional regression creation. |
| `listen regression list/add/show/update/remove/run` | `/api/v1/regression/` + run + item | Test name, phrase, expected intent/slots; run accepts `enabled_only`. |
| `listen performance last/summary/history` | `/api/v1/performance/{last,summary,history}` | Summary/history support limits; history also supports cursor. |
| `listen health audio-devices` | `GET /api/v1/health/audio_devices` | Enumerate available audio devices. |

All settings/config mutations use `If-Match`. Event publication is off
by default; diagnostic test requests never publish external events.

## Standalone recipe: build and test a command

```console
opal listen intents add --name lights.set --phrase 'turn on the {room} lights'
opal listen slots add --name room --slot-type room_name --json
# Use the returned slot ID:
opal listen slots values <slot-id> add --value kitchen
opal listen slots values <slot-id> add --value office
opal listen recognition test-text 'turn on the kitchen lights' --save-log
opal listen regression add --name kitchen-lights \
  --phrase 'turn on the kitchen lights' --expected-intent lights.set \
  --expected-slots '{"room":"kitchen"}'
opal listen regression run --enabled-only
```

---

# `opal look` — visual perception and camera operations

LOOK's normative `x-opal-cli` metadata requires the root `opal look`,
kebab-case options, canonical resource verbs (`add`, `remove`, `update`,
`list`, `show`), and explicit lifecycle verbs (`start`, `stop`, `stream`,
`validate`, `status`, `capture`, `cancel`). No implicit `create`/`delete`/
`get`/`set` aliases.

## What it does alone

LOOK turns a camera, video file, or uploaded image into live previews,
typed observations, finite analysis jobs, zone/rule detections, and
retained media. It does not need EVENT to store or query observations;
event publication is an optional, opt-in integration.

## Command reference

| Group / commands | Capability | Key inputs |
|---|---|---|
| `capabilities show` | Discover supported tasks, formats, filters, runtime capabilities. | **Query before relying on any optional task.** |
| `engines list/show/update` | Inspect known engines; change enabled/options. | Engine ID; update uses `--if-match`. |
| `models list/add/show/update/remove` | Register/discover model resources. | `id`, `engine_id`, `resource_ref`, `tasks`, `options`. **No model download/install command.** |
| `sources list/add/show/update/remove/status` | Register `usb`/`rtsp`/`http_mjpeg`/`file`/`media`/`adapter` sources. | `id`, `kind`, `name`, `locator`, optional `secret_ref`, `options`, `enabled`. Use `secret_ref` for credentials. |
| `sources frame` | One current JPEG, optionally processed. | `pipeline_id`, `target_fps`, `width`, `height`, `quality`, `presentation_filter`. Frame is fresh, not identical to a running stream. |
| `sources stream` | Raw or transiently processed MJPEG view. | `annotations`, `pipeline_id`, `classes`, `min_confidence`, `show_labels`, `show_boxes`, `show_confidence`, `target_fps`, `width`, `height`, `quality`. Options fixed at stream start. **Ephemeral viewer, not a session/recording.** |
| `sources capture` | Capture a current frame; optionally retain. | Source ID and capture request fields. |
| `pipelines list/add/show/update/remove/validate` | Ordered stage DAGs; validate is non-mutating. | `id`, `name`, `stages`, optional `description`. |
| `profiles list/add/show/update/remove/activate` | Reusable processing profiles. | Profile create/patch schema fields. |
| `zones list/add/show/update/remove` | Line/polygon regions. | `id`, `source_id`, `name`, `kind`, points. |
| `rules list/add/show/update/remove` | Visual condition evaluation. | Kinds: `object_appears`, `object_disappears`, `enters_zone`, `exits_zone`, `line_crosses`, `count_threshold`, `dwell_time`. Optional zone/class filters, threshold, duration, cooldown, capture/clip-on-match. |
| `monitors list/add/show/update/remove` | Persistent source/pipeline work. | `id`, `name`, `source_id`, optional pipeline/profile, `enabled`, `restart_policy` (`on_failure`/`always`/`never`). |
| `analyze run` / `analyze image` | Synchronous single-frame/media analysis. | Existing source or media; pipeline/profile/options/retention. |
| `sessions start/list/show/stop/observations/stream/preview` | Long-running live analysis. | Start: source, pipeline/profile/options/retention/auto-start. SSE supports `Last-Event-ID` resume from bounded cache; expired cursors may return 409. Preview is MJPEG. |
| `jobs submit/list/show/cancel` | Finite video analysis, annotated export, clip extraction. | Kinds: `analyze_video`, `export_annotated_video`, `extract_clip`. |
| `observations list/show` | Search immutable results. | `source_id`, `session_id`, `job_id`, `task`, `label`, `after`, `before`, `cursor`, `limit`. |
| `media list/upload/show/remove` | Uploaded image/video inputs. | Upload file; item ID. |
| `captures list/show/download/remove` | Retained captures and exact bytes. | Cursor/limit; output file for download. |
| `recordings list/start/show/stop` | Explicit independent recording lifecycle. | Start source/options; stop recording ID. |
| `artifacts list/show/download/remove` | Clips/derived outputs. | Cursor/limit; byte range for supported downloads. |
| `metrics show` / `events status` | Operational counters; event-publication queue/drop status. | Event publication remains opt-in/allowlisted. |
| `configuration export/validate/import` | Portable configuration (LOOK's route naming). | Export excludes secrets/history; import is validated and preconditioned. |

All settings/config mutations require the strong ETag precondition.
Optional vision tasks (OCR, pose, caption, VQA, anomaly, embeddings,
classification, segmentation, depth) are **capability-advertised** — check
`capabilities show` before depending on one. The contract does not
expose model downloads, training, identity recognition, or arbitrary
host shell execution.

## Standalone recipe: camera to observations

```console
opal look capabilities show
opal look sources add --id camera-1 --kind rtsp --name 'Front door' \
  --locator rtsp://camera.local/stream --secret-ref front-door-camera
opal look sources status camera-1
opal look pipelines validate pipeline.json
opal look pipelines add --id front-detect --name 'Front door detection' \
  --stages pipeline.json
opal look sessions start --source-id camera-1 --pipeline-id front-detect
opal look sessions stream <session-id>
opal look observations list --source-id camera-1 --task detect --label person \
  --limit 50
```

---

# `opal say` — text-to-speech

SAY abstracts installed TTS engines, registered voices, profiles, and
generation. **Engine installation is not an API operation.** The contract
states engines are installed and discovered by the implementation; they
cannot be created or deleted through the API.

## What it does alone

SAY produces completed audio files or streams headerless PCM for any
application that can send text. Profiles centralize voice/speed/output
defaults so callers do not need to know the engine's native API.

## Command reference

| Command | Route | Key inputs |
|---|---|---|
| `say engines list/show` | `GET /api/v1/engines/` + item | Catalog includes enabled/available/state; details include options and capability metadata. |
| `say engines update` | `PATCH /api/v1/engines/{engine_id}` | `enabled`, `options`; `--if-match` required. |
| `say engines validate` | `POST /api/v1/engines/{engine_id}/validate` | Verify availability/configuration. |
| `say voices list/add/show/update/remove` | `/api/v1/voices/` + item | List filters `engine_id`, `enabled`. Create: `voice_id`, `name`, `engine_id`, `engine_voice_ref`, language/options. |
| `say voices validate/test` | `/validate`, `/test` under voice item | Validate engine voice reference; synthesize a test sample. |
| `say profiles list/add/show/update/remove/activate` | `/api/v1/profiles/` + item + activate | Name, voice, speed, volume, output format, sample rate, engine options. |
| `say speak` | `POST /api/v1/generate` | Required `text`; optional profile/voice/engine IDs, speed, volume, output format, sample rate, engine options. |
| `say stream` | `POST /api/v1/generate/stream` | Same controls; response is **headerless signed 16-bit little-endian mono PCM, not WAV.** |
| `say backup ...` | SAY backup routes | Archive list/create/download/restore/delete; portable export/validate/import. Mutations use `If-Match`. |

Engine states (contract enum): `ready`, `unavailable`, `error`, `disabled`.

## Host setup, then API registration

The host steps are illustrative only — install the engine runtime and
voice/model files using that engine's own instructions. The API does not
name a single install command or a universal package manager.

```console
# On the SAY host: install a supported engine runtime and voice/model files.
opal say engines list
opal say engines validate <engine-id>
opal say voices add --voice-id <voice-id> --name <display-name> \
  --engine-id <engine-id> --engine-voice-ref <engine-specific-reference> \
  --language en-US --engine-options '{}'
opal say voices validate <voice-id>
opal say voices test <voice-id> --text 'Installation check' --output check.wav
opal say profiles add --name calm --voice-id <voice-id> --speed 0.9
opal say speak 'Hello from OPAL' --profile-id calm --output hello.wav
```

Do not assume an installable engine exists until `engines list` and
`engines validate` confirm it.

---

# `opal think` — durable LLM tasks

THINK accepts a prompt, returns a durable task ID (HTTP 202), then
exposes task state/output and a stream. Sessions serialize turns. Model
discovery is read-only; provider endpoints and secrets are service
configuration, not API operations.

## What it does alone

THINK provides a durable, scriptable LLM task queue, a streamed answer,
and serialized multi-turn sessions. Other OPAL services are optional
clients.

## Command reference (normative `x-opal-cli`)

```text
opal think ask|chat
opal think task create|list|show|watch|cancel
opal think session add|list|show|remove
opal think model list|show
opal think settings list|show|set|remove
opal think health
```

Task-create fields: required `prompt`; optional `session_id`, `model_id`,
`context`, `max_steps`, `timeout_seconds`, metadata. Task-list filters
include status/session and cursor pagination. Session add accepts a
title. Model list is a bounded provider/model catalog and may include
unavailable models (`available: false`). **No model-install/delete
route exists.**

`ask` is a proposed convenience implemented as task-create + task-watch.
`chat` is a proposed client loop using one session and one task per
turn. There is no separate chat REST endpoint. Treat context as
untrusted input. An idempotency key can make task admission retries safer
but does not promise exactly-once side effects.

## Standalone recipe: submit and follow a task

```console
opal think model list
opal think task create 'Summarize this incident report' \
  --context '{"report":"..."}' --json
opal think task watch <task-id>
opal think task show <task-id>
opal think session add --title 'Incident review'
opal think ask 'What should we investigate next?' --session-id <session-id>
```

---

# Ecosystem workflows

The suite enables **client-side chains**, not a single cross-service
endpoint. Preserve one transaction ID through the chain for traceability.
The sequences below assume each service URL, credentials, optional
capabilities, and resource IDs are configured. They are not turnkey
deployments.

## Twenty cross-domain use cases

### Home automation

### 1. Announce a package on the porch

```console
opal look rules add --id porch-package --name package --source-id porch \
  --kind object_appears --class-filters '["package"]' --capture-on-match
opal event actions add http --id package-notice --method POST \
  --url <deployment-say-adapter-url> --body-mode json
opal event rules add --id announce-package --topic 'opal.look.*' \
  --condition 'data.class eq "package"' --action package-notice
opal event rules test announce-package --event @package-event.json
```

Routing generated audio to a particular speaker is deployment-specific,
not an API operation.

### 2. Person crossing a driveway zone

```console
opal look zones add --id driveway --source-id camera-1 --name driveway \
  --kind polygon --points @driveway-points.json
opal look rules add --id arrival --name arrival --source-id camera-1 \
  --kind enters_zone --zone-id driveway --class-filters '["person"]'
opal look events status
opal look observations list --source-id camera-1 --label person --limit 20
```

### 3. Voice-controlled light action

```console
opal listen intents add --name lights.set --phrase 'turn on the {room} lights'
opal listen slots add --name room --slot-type room_name
opal listen slots values <room-slot-id> add --value kitchen
opal event actions add http --id lights-api --method POST \
  --url <home-automation-endpoint> --body-mode json
opal event rules add --id kitchen-lights --topic intent.recognized \
  --condition 'data.intent eq "lights.set"' --action lights-api
opal event rules test kitchen-lights --event @recognized-intent.json
```

### 4. "Is the garage open?" visual check

```console
opal look sources frame garage-camera --output garage.jpg
opal look capabilities show
opal look analyze image garage.jpg --pipeline-id garage-state
opal look observations list --source-id garage-camera --limit 5
opal think ask 'From these observations, is the garage open?' \
  --context @garage-observations.json
opal say speak '<answer from THINK>' --profile-id household
```

Requires a pipeline/task that can distinguish the garage state; do not
assume a caption/VQA capability unless LOOK advertises it.

### 5. Leak/anomaly notification

```console
opal look capabilities show                  # confirm anomaly task exists first
opal look pipelines validate @anomaly-pipeline.json
opal look monitors add --id basement --name basement --source-id basement-camera \
  --pipeline-id anomaly-pipeline --restart-policy on_failure
opal look observations list --source-id basement-camera --task anomaly --limit 20
opal event actions show <notification-action-id>
```

### Education

### 6. Reading practice feedback

```console
opal listen recognition test-audio reading.wav --save-log
opal listen logs list --limit 1 --json
opal think ask 'Give supportive feedback comparing the recognized words to this passage.' \
  --context @reading-context.json
opal say speak '<THINK feedback>' --profile-id tutor --output feedback.wav
```

### 7. Language lesson with a recognition regression

```console
opal listen intents add --name location.query --phrase 'où est la bibliothèque'
opal listen regression add --name french-library \
  --phrase 'où est la bibliothèque' --expected-intent location.query
opal listen regression run --enabled-only
opal listen performance history --limit 20
```

### 8. Explain a lab object from a camera frame

```console
opal look capabilities show                    # confirm caption/OCR/VQA support
opal look sources frame lab-camera --output lab.jpg
opal look analyze image lab.jpg --pipeline-id lab-caption
opal look observations list --source-id lab-camera --task caption --limit 1
opal think ask 'Explain this object to a beginner.' --context @caption-result.json
opal say speak '<THINK answer>'
```

### 9. Classroom occupancy count

```console
opal look rules add --id occupancy --name occupancy --source-id classroom \
  --kind count_threshold --class-filters '["person"]' --threshold 25
opal look observations list --source-id classroom --task detect --label person \
  --after <ISO-time> --before <ISO-time>
opal look metrics show
```

Aggregate visual detection, not identity recognition.

### 10. Spoken flashcards

```console
opal think ask 'Create five short Q/A flashcards about photosynthesis.' \
  --context @lesson-notes.txt --json
opal say speak '<question>' --output question.wav
opal listen recognition test-audio answer.wav --save-log
opal think ask 'Compare the answer with the expected answer.' \
  --context @flashcard-and-transcript.json
```

### Voice assistant

### 11. "Ask OPAL a question"

```console
opal listen recognition stream
# Capture the recognized utterance with the LISTEN client.
opal think task create '<recognized utterance>' --session-id <conversation-id>
opal think task watch <task-id>
opal say stream '<completed THINK response>' > answer.pcm
```

Client orchestration, not a single REST endpoint. Microphone
capture/playback are local device concerns.

### 12. Timer by voice

```console
opal listen intents add --name timer.set --phrase 'set a timer for {minutes} minutes'
opal listen slots add --name minutes --slot-type duration
opal listen slots values <minutes-slot-id> add --value 5
opal listen recognition test-text 'set a timer for 5 minutes'
opal event actions show <timer-action-id>
opal event rules add --id timer-start --topic intent.recognized \
  --condition 'data.intent eq "timer.set"' --action <timer-action-id>
opal event executions list --action-id <timer-action-id> --limit 10
```

An actual scheduler action must be installed/configured; EVENT does not
provide a dedicated timer resource.

### 13. Multi-turn cooking assistant

```console
opal think session add --title cooking --json
opal think ask 'What can I cook with lentils and spinach?' --session-id <session-id>
opal think ask 'Make that vegan and give me a shopping list.' --session-id <session-id>
opal say speak '<final response>' --profile-id kitchen
```

### 14. "Drop in on camera-1"

```console
opal look sources status camera-1
opal look sources stream camera-1 --annotations --show-labels --show-boxes
opal look sessions list --source-id camera-1 --limit 10
```

`sources stream` is an ephemeral MJPEG view; it does not create a
session/recording. Use sessions when persisted live analysis is intended.

### 15. Spoken visual accessibility

```console
opal look capabilities show                    # verify OCR/caption task
opal look sources frame entry-camera --output sign.jpg
opal look analyze image sign.jpg --pipeline-id read-sign
opal look observations list --source-id entry-camera --task ocr --limit 1
opal say speak '<recognized sign text>' --profile-id accessible
```

### Custom and developer workflows

### 16. CI build summary spoken on an office speaker

```console
opal event publish build.finished \
  '{"repo":"opal-api","status":"failed","log":"..."}' --source ci
opal event rules test ci-failure --event @build-event.json
opal event executions list --rule-id ci-failure --limit 20
opal think ask 'Summarize this build failure.' --context @build-event.json
opal say speak '<summary>' --output build-summary.wav
```

### 17. Wildlife camera evidence

```console
opal look monitors add --id trail --name trail --source-id trail-rtsp \
  --pipeline-id wildlife --restart-policy always
opal look rules add --id animal --name animal --source-id trail-rtsp \
  --kind object_appears --class-filters '["deer","fox"]' --clip-on-match
opal look observations list --source-id trail-rtsp --task detect --limit 100
opal look artifacts list --limit 50
```

### 18. Store-front crossing analytics

```console
opal look zones add --id entrance-line --source-id store-cam --name entrance \
  --kind line --points @entrance-line.json
opal look rules add --id footfall --name footfall --source-id store-cam \
  --kind line_crosses --zone-id entrance-line --class-filters '["person"]'
opal look observations list --source-id store-cam --task detect --after <ISO-time>
opal event stats
```

### 19. Elder-care check-in workflow

```console
opal look rules add --id inactivity --name inactivity --source-id living-room \
  --kind dwell_time --minimum-duration-ms 14400000
opal event rules test check-in --event @sample-look-event.json
opal listen intents add --name checkin.reply --phrase '{answer}'
opal event actions show <check-in-action-id>
opal say speak 'Are you okay?' --profile-id calm
opal listen recognition stream
```

This illustrates a reviewable automation chain. It is not a medical
monitoring guarantee; the threshold, connectivity, consent, escalation
policy, and reliable human response must be designed and validated
separately.

### 20. Discoverable custom skills

```console
opal event actions list
opal event actions show <action-id>              # inspect description/schema
opal think ask 'Which registered actions can help organize my morning?' \
  --context @action-catalog.json
opal event actions execute <safe-action-id>      # only after reviewing it
opal event executions list --action-id <safe-action-id>
```

EVENT action metadata (`description`, `input_schema`, `keywords`,
`suggested_prompts`) can help a client or THINK discover registered
tools. Discovery does not itself authorize execution.

---

# Appendix: contract grounding

- **Normative CLI names** come from `x-opal-cli` in `opal_look.yaml` and
  `opal_think.yaml`. Proposed names for EVENT, LISTEN, and SAY are
  derived from REST paths and request schemas.
- **Flags** map to real schema fields, query parameters, and enum
  values: LOOK rule kinds, EVENT condition operators, SAY engine
  states, LISTEN `require_wakeword`, etc.
- **Engine/model installation** is host-level for SAY, LOOK, and THINK.
  No contract exposes install/download/delete endpoints. The docs
  describe host install followed by API verification (`engines list` →
  `engines validate` → `voices add --engine-voice-ref` → `voices
  validate` → `voices test`), not an invented `install` command.
- **Concurrency**: protected mutations use strong ETag `If-Match`
  preconditions; missing → 428, stale → 412. The CLI should fetch-then-
  write to obtain a valid ETag.
- **Pagination**: cursor-based where supported; cursors are bound to
  their filters.
- **Streams**: LOOK `sources stream` is an ephemeral MJPEG viewer, not
  a session/recording. LOOK session SSE supports `Last-Event-ID`
  resume from a bounded cache; expired cursors may return 409. SAY
  `stream` returns headerless signed 16-bit little-endian mono PCM,
  not WAV.
- **Optional capabilities** (LOOK OCR, pose, caption, VQA, anomaly,
  embeddings, classification, segmentation, depth) are capability-
  advertised, not universally guaranteed. Check `capabilities show`
  before depending on one.
- **Ecosystem workflows** are client-side orchestration across
  independent services. There is no single cross-service API.
- **Event metadata versions**: most services emit `metadata_schema_version:
  '1.0'`; LISTEN declares `'2.0'` in its own normative prose. The
  shared compatibility clause permits producers to emit any version
  without breaking the wire contract; the field-level differences
  between 1.0 and 2.0 are not documented in the contracts.
- **Correlation IDs** (`X-Opal-Session-Id`, `X-Opal-Transaction-Id`,
  `X-Opal-Request-Id`, `X-Opal-Causation-Id`) are tracing context, not
  authorization credentials or a distributed-transaction guarantee.
