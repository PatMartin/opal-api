# OPAL CLI — a Typer command surface for five APIs

> **Hypothetical CLI.** This is a design proposal, not a claim that an
> `opal` executable exists. It composes the five independent OpenAPI
> contracts in `openapi/`. LOOK and THINK define `x-opal-cli` metadata; the
> commands for those services follow it. EVENT, LISTEN, and SAY do not
> define that metadata, so their command names below are a proposed
> consistent mapping from their REST operations.
>
> The shell examples show the intended workflow. Names such as
> `--json`, `--output`, or a convenient positional argument are CLI
> affordances, not API fields unless explicitly identified as such.

## The five applications

| CLI application | Contract | Responsibility |
|---|---|---|
| `opal event` | `openapi/opal_event.yaml` | Event publication/storage, topic discovery, rules, actions, execution history |
| `opal listen` | `openapi/opal_listen.yaml` | Wakewords, speech recognition, intents, slots, profiles, logs and regression |
| `opal look` | `openapi/opal_look.yaml` | Visual sources, models, pipelines, analysis, sessions, jobs and observations |
| `opal say` | `openapi/opal_say.yaml` | TTS engines, voices, profiles and generated audio |
| `opal think` | `openapi/opal_think.yaml` | Durable LLM tasks, sessions and model discovery |

Each sub-application can be installed and used independently. The suite
does not require all five services to be running.

## Install, endpoints, and shared options

The CLI package and install command are hypothetical:

```console
python -m pip install opal-cli
opal --help
```

Configure a URL per service, for example:

```console
export OPAL_EVENT_URL=http://127.0.0.1:8080
export OPAL_LOOK_URL=http://127.0.0.1:8081
export OPAL_LISTEN_URL=http://127.0.0.1:8000
export OPAL_SAY_URL=http://127.0.0.1:8001
export OPAL_THINK_URL=http://127.0.0.1:8082
export OPAL_TOKEN=...
```

The actual API `servers` entries are defaults, not a promise that a
particular deployment uses those ports. The CLI should allow a service URL
override (`--url`) and a bearer token (`--token` / `OPAL_TOKEN`). Avoid
putting credentials in shell history or camera URLs; LOOK supports a
`secret_ref` for source credentials.

All services share kernel conventions:

| Proposed CLI option | Contract behavior |
|---|---|
| `--session-id`, `--transaction-id`, `--request-id`, `--causation-id` | Supply the four `X-Opal-*` correlation headers. The CLI may generate IDs where absent; preserve a transaction ID across a compound workflow. |
| `--if-match ETAG` | Strong ETag precondition on protected mutations. Missing precondition is 428; stale value is 412. A safe CLI can fetch the resource and ETag before writing. |
| `--cursor`, `--limit` | Cursor pagination where the endpoint supports it. A cursor is tied to its filters; do not reuse it after changing filters. |
| `--json` | Proposed output-format option. Useful for scripts; response/error envelopes are API-defined. |

Loopback authorization behavior and bearer authentication are described in
each service contract. Do not treat an opaque session/correlation ID as an
authorization credential.

## Kernel commands

The kernel supplies common health and settings operations. The exact
service-specific backup routes vary; where one service names the same
capability `configuration`, the CLI should retain that service's name or
provide a clearly documented alias.

```text
opal <service> health
opal <service> health live
opal <service> health ready
opal <service> settings list
opal <service> settings show <key>
opal <service> settings set <key> <JSON-value> --if-match <etag>
opal <service> settings remove <key> --if-match <etag>
opal <service> settings patch <JSON-object> --if-match <etag>
```

Protected mutations must carry `If-Match`; fetch the current representation
first to get the ETag. Settings responses mask secrets; configuration
exports exclude secrets and history.

---

# `opal event` — event bus and automation

EVENT is useful on its own as a small event-driven automation service:
clients publish JSON events; rules select topics and evaluate conditions;
registered actions run; execution records provide an audit trail.

## Command map

The following proposed command groups map to the EVENT REST routes:

| Commands | REST operation | API query/body inputs |
|---|---|---|
| `event publish`, `event list`, `event clear` | `POST/GET/DELETE /api/v1/events/` | Publish body: topic and data, optional source/id/timestamp. List filters: `cursor`, `limit`, `topic`, `source`, `from`, `to`. Clear deletes stored events. |
| `event show/delete ID` | `GET/DELETE /api/v1/events/{event_id}` | Event ID path parameter. |
| `event topics` | `GET /api/v1/topics/` | Observed topic names. |
| `event rules list/add` | `GET/POST /api/v1/rules/` | Rule has `id`, `enabled`, `topic`, `conditions`, `actions`. |
| `event rules show/update/delete ID` | `GET/PATCH/DELETE /api/v1/rules/{rule_id}` | Partial update; protected config changes use `If-Match`. |
| `event rules test ID` | `POST /api/v1/rules/{rule_id}/test` | Evaluate a candidate event without executing actions. |
| `event actions list/add` | `GET/POST /api/v1/actions/` | Registered action definition; action variants are shell, HTTP, Python. |
| `event actions show/update/delete ID` | `GET/PATCH/DELETE /api/v1/actions/{action_id}` | Delete is only valid for an unused action. |
| `event actions execute ID` | `POST /api/v1/actions/{action_id}/execute` | Manually execute a registered action. |
| `event executions list/show` | `GET /api/v1/executions/`, `GET /api/v1/executions/{execution_id}` | List filters: `status`, `rule_id`, `action_id`, `event_id`, `limit`, `cursor`. |
| `event stats` | `GET /api/v1/stats/` | Event and execution counters. |

CLI options should map directly to API inputs:

- Event listing: `--topic`, `--source`, `--from`, `--to`, `--cursor`,
  `--limit`.
- Rule: `--id`, `--topic`, `--enabled/--disabled`, repeatable
  `--condition`, repeatable `--action`.
- Condition operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`,
  `not_in`, `exists`, `contains`; conditions are ANDed.
- Shell action: `--mode`, `--executable` or `--script-path`, and its
  declared timeout/options.
- HTTP action: `--method`, `--url`, headers and body mode as specified by
  the action schema.
- Python action: `--module`, `--function`, and timeout.
- All action variants can carry action self-description fields such as
  `description`, `input_schema`, `keywords`, and `suggested_prompts`.

The wire event is a topic and JSON body; ZeroMQ transport is separately
specified and uses exactly two frames. The CLI does not expose an
undocumented third frame or infer that HTTP publication and ZeroMQ
publication are interchangeable deployment settings.

## What EVENT can do alone

It can route webhook/device/script events to other HTTP endpoints or
registered local actions, keep a searchable event history, and show which
rules/actions ran. It does not need LISTEN, LOOK, SAY, or THINK to receive
events or run its own actions.

### Standalone example: threshold alert

Assume an external sensor can POST events and the deployment has a
pre-registered HTTP action called `page-on-call`.

```console
opal event actions show page-on-call
opal event rules add --id hot-room --topic 'sensor.*' \
  --condition 'data.temperature gt 30' --action page-on-call
opal event rules test hot-room \
  --event '{"topic":"sensor.lab","data":{"temperature":33.2}}'
opal event publish sensor.lab '{"temperature":33.2}' --source bench-pi
opal event executions list --rule-id hot-room --limit 20
```

`actions show/add` use the action schema for the actual fields; registering
or executing an action can have side effects, so inspect the target and
test the rule before enabling it.

---

# `opal listen` — voice recognition and vocabulary

LISTEN is a standalone wakeword/STT/intent/slot service. It also exposes a
training-and-quality workflow through logs, failed utterances, promotion,
and regression tests. Event publication is a configurable integration, not
a prerequisite for recognition.

## Command map and options

| Proposed commands | REST route family | Inputs / options |
|---|---|---|
| `listen wakewords list/add/show/update/remove` | `/api/v1/wakewords/`, `/api/v1/wakewords/{wakeword_id}` | `name`, `enabled`, `confidence_threshold`; path ID for item operations. |
| `listen intents list/add/show/update/remove` | `/api/v1/intents/`, `/api/v1/intents/{intent_id}` | `name`, `description`, `enabled`, `confidence_threshold`, optional phrases. |
| `listen intents phrases <intent>` | `/api/v1/intents/{intent_id}/phrases` and phrase item route | Add/list/remove phrases; phrase text is the input. |
| `listen slots list/add/show/update/remove` | `/api/v1/slots/`, `/api/v1/slots/{slot_id}` | Slot `name`, `slot_type`, optional description. |
| `listen slots values <slot>` | `/api/v1/slots/{slot_id}/values` and value item route | Add/list/remove canonical string values. |
| `listen slots aliases <slot> <value>` | aliases collection/item routes | Add/list/remove alternative spoken forms. |
| `listen profiles list/add/show/update/remove/activate` | `/api/v1/profiles/`, `/api/v1/profiles/{profile_id}`, activate route | Profile fields include name, active state, wakeword names, enabled intents/slots, confidence thresholds and VAD settings. |
| `listen recognition test-text TEXT` | `POST /api/v1/recognition/test_text` | `text`; optional `save_log` query option. Diagnostic only. |
| `listen recognition test-audio FILE` | `POST /api/v1/recognition/test_audio` | Multipart `file`; query options `save_log`, `require_wakeword`. Diagnostic only. |
| `listen recognition start/stop/status` | `/api/v1/recognition/start`, `/stop`, `/status` | Start/stop active pipeline; status reports recognition state/metrics. |
| `listen recognition stream` | `GET /api/v1/recognition/stream` | Optional `debug`; streaming response. |
| `listen logs list/show/count` | `/api/v1/logs/`, `/api/v1/logs/count`, `/api/v1/logs/{log_id}` | List filters include `limit`, `cursor`, `intent_name`, `matched`. |
| `listen failed list/add/show/update/remove/promote` | `/api/v1/failed_utterances/` and item/promote routes | `reviewed`, `promoted`, `limit`, `offset`; promote accepts intent name and optional regression creation. |
| `listen regression list/add/show/update/remove/run` | `/api/v1/regression/`, `/api/v1/regression/run`, item route | Test name, phrase, expected intent/slots; run accepts `enabled_only`. |
| `listen performance last/summary/history` | `/api/v1/performance/{last,summary,history}` | Summary/history support limits; history also supports cursor. |
| `listen health audio-devices` | `GET /api/v1/health/audio_devices` | Enumerate available audio devices. |

LISTEN also has the shared settings, health probes, and server-side backup
operations. Every setting/config mutation uses the shared `If-Match`
precondition. Event publication is off by default; diagnostic test
requests do not publish external events.

## What LISTEN can do alone

It can classify text without an audio device; recognize live speech using
its configured audio pipeline; define wakewords, intents, slots and
profiles; and improve recognition from failed-utterance logs without
another OPAL service.

### Standalone example: build and test a command

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

The positional/group syntax is proposed; the request fields and route
operations are contract-defined.

---

# `opal look` — visual perception and camera operations

LOOK's normative CLI metadata requires the root `opal look`, group and
command names from `x-opal-cli`, kebab-case options, and no implicit
`create/delete/get/set` aliases. The command inventory below preserves its
canonical resource verbs (`add`, `remove`, `update`, `list`, `show`) and
explicit lifecycle verbs.

## Command map

| Group and commands | Contract capability | Options / inputs |
|---|---|---|
| `capabilities show` | Discover supported tasks, formats, filters and runtime capabilities. | No guessed capability is assumed; query before using optional tasks. |
| `engines list/show/update` | Inspect known engines, change enabled/options configuration. | Engine ID; update uses ETag/`--if-match`; engine-specific options. |
| `models list/add/show/update/remove` | Register/discover model resources. | `id`, `engine_id`, `resource_ref`, `tasks`, `options`; model add/update are protected mutations. No model download/install command is specified. |
| `sources list/add/show/update/remove/status` | Register and manage `usb`, `rtsp`, `http_mjpeg`, `file`, `media`, or `adapter` sources. | `id`, `kind`, `name`, `locator`, optional `secret_ref`, `options`, `enabled`. Use secret references for credentials. |
| `sources frame` | Get one current JPEG without retention/inference, optionally processed. | `pipeline_id`, `target_fps`, `width`, `height`, `quality`, `presentation_filter`; frame is fresh, not guaranteed identical to a running stream. |
| `sources stream` | View raw or transiently processed MJPEG. | `annotations`, `pipeline_id`, `classes`, `min_confidence`, `show_labels`, `show_boxes`, `show_confidence`, `target_fps`, `width`, `height`, `quality`, `presentation_filter`. Options fixed at stream start. |
| `sources capture` | Capture a current frame; optionally retain. | Source ID and capture request fields. |
| `pipelines list/add/show/update/remove/validate` | Configure ordered stage DAGs and validate topology/task compatibility. | Pipeline `id`, `name`, `stages`, optional `description`; validate is non-mutating. |
| `profiles list/add/show/update/remove/activate` | Manage reusable processing profiles. | Fields are from profile create/patch schemas; activation selects the active profile. |
| `zones list/add/show/update/remove` | Define line/polygon regions. | `id`, `source_id`, `name`, `kind`, points. |
| `rules list/add/show/update/remove` | Evaluate visual conditions. | Kinds include `object_appears`, `object_disappears`, `enters_zone`, `exits_zone`, `line_crosses`, `count_threshold`, `dwell_time`; optional zone/class filters, threshold, duration, cooldown, capture/clip-on-match. |
| `monitors list/add/show/update/remove` | Declare persistent source/pipeline work. | `id`, `name`, `source_id`, optional pipeline/profile, enabled and restart policy (`on_failure`, `always`, `never`). |
| `analyze run`, `analyze image` | Synchronous single-frame/media analysis. | Existing source or media, pipeline/profile/options/retention as declared; image route accepts upload and response negotiation. |
| `sessions start/list/show/stop/observations/stream/preview` | Long-running live analysis. | Start accepts source, pipeline/profile/options/retention/auto-start; list filters state/source/cursor/limit; SSE supports `Last-Event-ID` from bounded cache; preview is MJPEG. |
| `jobs submit/list/show/cancel` | Finite video analysis, annotated export, clip extraction. | Job kinds `analyze_video`, `export_annotated_video`, `extract_clip`; source or media, range/options/retention/output; list filters state/kind/cursor/limit. |
| `observations list/show` | Search immutable results. | `source_id`, `session_id`, `job_id`, `task`, `label`, `after`, `before`, `cursor`, `limit`. |
| `media list/upload/show/remove` | Manage uploaded image/video inputs. | Upload file; item ID for show/remove. |
| `captures list/show/download/remove` | Manage retained captures and exact bytes. | Cursor/limit; output file for download. |
| `recordings list/start/show/stop` | Explicit independent recording lifecycle. | Start source/options; stop recording ID. |
| `artifacts list/show/download/remove` | Manage clips/derived outputs. | Cursor/limit; byte range for supported downloads. |
| `metrics show`, `events status` | Operational counters and event-publication queue/drop status. | Event publication remains opt-in/allowlisted per contract. |
| `configuration export/validate/import` | Portable configuration operations (LOOK's route naming). | Export excludes secrets/history; import is validated and preconditioned. |

All settings/config mutations require the strong ETag precondition. Optional
vision tasks (such as OCR, pose, caption, VQA, anomaly, embeddings) are
capability-advertised; check `capabilities show` before depending on one.
The contract does not expose model downloads, training, identity
recognition, or arbitrary host shell execution.

## What LOOK can do alone

It can turn a camera, video file or uploaded image into live previews,
typed observations, finite analysis jobs, zone/rule detections and retained
media. It does not need EVENT to store/query observations; event
publication is an optional integration.

### Standalone example: camera to observations

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

The CLI should obtain IDs/ETags from API responses rather than fabricate
them. If a source-specific capability is absent, validation should fail
before a monitor/session is started.

---

# `opal say` — text-to-speech

SAY abstracts installed TTS engines, registered voices, profiles, and
generation. **Engine installation is not an API operation.** The contract
states that engines are installed/discovered by the implementation and
cannot be created or deleted through the API.

## Command map and options

| Proposed commands | REST routes | Inputs/options |
|---|---|---|
| `say engines list/show` | `GET /api/v1/engines/`, `GET /api/v1/engines/{engine_id}` | Catalog includes enabled/available/state; engine details include options and capability metadata. |
| `say engines update` | `PATCH /api/v1/engines/{engine_id}` | `enabled`, `options`; strong ETag required. |
| `say engines validate` | `POST /api/v1/engines/{engine_id}/validate` | Verify availability/configuration. |
| `say voices list/add/show/update/remove` | `/api/v1/voices/`, `/api/v1/voices/{voice_id}` | List filters `engine_id`, `enabled`; create fields `voice_id`, `name`, `engine_id`, `engine_voice_ref`, language/options. |
| `say voices validate/test` | `/validate`, `/test` under voice item | Validate engine voice reference; synthesize a test sample. |
| `say profiles list/add/show/update/remove/activate` | `/api/v1/profiles/`, profile item and activate route | Name, voice, speed, volume, output format, sample rate and engine options. |
| `say speak` | `POST /api/v1/generate` | Required text; optional profile/voice/engine IDs, speed, volume, output format, sample rate and engine options. |
| `say stream` | `POST /api/v1/generate/stream` | Same generation controls; response is headerless signed 16-bit little-endian mono PCM, not WAV. |
| `say backup ...` | SAY backup routes | Archive list/create/download/restore/delete; portable export/validate/import. Mutations use `If-Match`. |

The API does not name a single engine install command or a universal
package manager. Runtime, model file and paths are deployment-specific.

### Host setup followed by API registration

The host steps below are illustrative only; install the engine and model
using that engine's own instructions:

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

`--text` and `--output` in the proposed `voices test` command are CLI
conveniences for the request/response; implementations must follow the
actual test operation schema. Do not assume an installable engine exists
until `engines list` and `validate` confirm it.

## What SAY can do alone

It can produce completed audio files or stream PCM for any application
that can send text. Profiles centralize voice/speed/output defaults; callers
do not need to know the engine's native API.

---

# `opal think` — durable LLM tasks

THINK accepts a prompt, returns a durable task ID (HTTP 202), then exposes
task state/output and a stream. Sessions serialize turns. Model discovery
is read-only; provider endpoints and secrets are service configuration.

## Commands and options

The contract's `x-opal-cli` catalogue includes:

```text
opal think ask|chat
opal think task create|list|show|watch|cancel
opal think session add|list|show|remove
opal think model list|show
opal think settings list|show|set|remove
opal think health
```

Task-create fields: required `prompt`; optional `session_id`, `model_id`,
`context`, `max_steps`, `timeout_seconds`, and metadata. Task-list filters
include status/session and cursor pagination. Session add accepts a title;
model list is a bounded provider/model catalog and may include unavailable
models (`available: false`). No model-install/delete route exists.

`ask` is a proposed convenience implemented as task-create + task-watch;
`chat` is a proposed client loop using one session and one task per turn.
There is no separate chat REST endpoint. Treat context as untrusted input.
An idempotency key can make task admission retries safer but does not
promise exactly-once side effects.

## What THINK can do alone

It provides a durable, scriptable LLM task queue, a streamed answer, and
serialized multi-turn sessions. Other OPAL services are optional clients.

### Standalone example: submit and follow a task

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

The suite enables client-side chains rather than a single cross-service
endpoint. Preserve one transaction ID through the chain for traceability.
The command sequences below describe intent and contract operations; they
assume each service URL, credentials, optional capabilities and resource
IDs are configured. They are not turnkey deployments.

## Use cases a single service can handle

The previous service sections each include a CLI sequence. In summary:

- EVENT alone: publish, match, execute and audit.
- LISTEN alone: define vocabulary, recognize text/audio and regression-test.
- LOOK alone: ingest camera/media, analyze and query observations.
- SAY alone: validate an installed engine/voice and generate audio.
- THINK alone: submit durable tasks, stream output and retain sessions.

## Twenty cross-domain use cases with command sequences

Commands that create persistent rules or perform physical actions should
be reviewed and tested before enabling them. Secrets, external webhooks,
hardware availability and optional model capabilities are deployment
prerequisites.

### Home automation

### 1. Say aloud when a package appears

Configure LOOK detection and have an EVENT action call an already
configured SAY generation route or local playback adapter:

```console
opal look rules add --id porch-package --name package --source-id porch \
  --kind object_appears --class-filters '["package"]' --capture-on-match
opal event actions add http --id package-notice --method POST \
  --url <deployment-say-adapter-url> --body-mode json
opal event rules add --id announce-package --topic 'opal.look.*' \
  --condition 'data.class eq "package"' --action package-notice
opal event rules test announce-package --event @package-event.json
```

The SAY REST API generates/streams audio; routing audio to a particular
speaker is deployment-specific, not an API operation.

### 2. Person crossing a driveway zone

```console
opal look zones add --id driveway --source-id camera-1 --name driveway \
  --kind polygon --points @driveway-points.json
opal look rules add --id arrival --name arrival --source-id camera-1 \
  --kind enters_zone --zone-id driveway --class-filters '["person"]'
opal look events status
opal look observations list --source-id camera-1 --label person --limit 20
```

Optional event publication must be explicitly configured; without it,
LOOK still records/query observations.

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

The home-automation endpoint and event publication adapter are external
dependencies.

### 4. \"Is the garage open?\" visual check

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

The alert rule/action depends on an event publication contract from the
deployed LOOK implementation and a configured notification endpoint.

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
opal listen regression add --name french-library --phrase 'où est la bibliothèque' \
  --expected-intent location.query
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

This is aggregate visual detection, not identity recognition.

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

### 11. \"Ask OPAL a question\"

```console
opal listen recognition stream
# Capture the recognized utterance with the LISTEN client.
opal think task create '<recognized utterance>' --session-id <conversation-id>
opal think task watch <task-id>
opal say stream '<completed THINK response>' > answer.pcm
```

This is a client orchestration flow, not a single REST endpoint. Microphone
capture/playback are local CLI/device concerns.

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

### 14. \"Drop in on camera-1\"

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

The CI runner needs an EVENT publisher, a configured rule/action, and a
deployment-specific audio output.

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
`suggested_prompts`) can help a client or THINK discover registered tools.
Discovery does not itself authorize execution.

---

## Safety and implementation notes

- A Typer app can map one sub-app per contract, groups from tags/CLI
  metadata, and fields/options from OpenAPI parameters and request schemas.
- Only LOOK and THINK have normative `x-opal-cli` metadata. Do not describe
  proposed EVENT/LISTEN/SAY command spellings as existing contract
  requirements.
- Treat shell actions, HTTP actions, camera streams, event clearing,
  configuration imports and device controls as side-effecting. Require
  explicit confirmation where appropriate; never silently retry unsafe
  operations.
- Store bearer tokens and source credentials in a secure secret store.
  Never print them in `--json`, settings output, exports, or logs.
- Preserve correlation IDs across a compound flow; a transaction ID is
  tracing context, not a distributed transaction or atomicity guarantee.
- Capability discovery and preflight validation matter: optional model
  tasks, engines, devices, codecs and providers may not be installed.
- Before publishing a real CLI, generate a command/option coverage test
  from the OpenAPI documents and verify every command against request
  schemas and response status codes.
