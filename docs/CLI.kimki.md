# OPAL CLI: a Typer field guide

This document proposes a hypothetical [Typer](https://typer.tiangolo.com/)
CLI composed from the five OPAL OpenAPI specifications. It is a design for
an `opal` executable, not documentation of an already-installed program.

The CLI has one sub-application per service:

```text
opal event ...    EVENT: events, rules, actions and execution history
opal listen ...   LISTEN: wakewords, speech, intents and slots
opal look ...     LOOK: visual sources, analysis and observations
opal say ...      SAY: text-to-speech engines, voices and audio
opal think ...    THINK: durable language-model tasks and sessions
```

## What is contract-defined and what is proposed?

- **LOOK and THINK** contain `x-opal-cli` metadata. Their group and command
  names below follow that metadata.
- **EVENT, LISTEN and SAY** do not contain equivalent per-operation CLI
  metadata. Their command spelling is a proposed mapping from REST routes;
  the underlying routes, fields and behavior are contract-defined.
- `--json`, `--output`, `--body @file.json`, URL overrides and similar
  conveniences are proposed CLI features. They are not new API fields.
- `<task-id>`, `<session-id>`, `<etag>` and similar tokens are placeholders
  for values returned by earlier commands. `@file.json` means a local JSON
  request document.
- Examples use POSIX-style shell syntax. Playing audio, opening an MJPEG
  viewer, capturing a microphone and processing output with tools such as
  `jq` are local shell/application concerns, not OPAL API operations.

## Installation and configuration

A possible package installation would be:

```console
python -m pip install opal-cli
opal --help
```

Each service can be used without installing or running the other four.
Configure only the endpoints needed by the current task:

```console
export OPAL_EVENT_URL=http://event.example
export OPAL_LISTEN_URL=http://listen.example
export OPAL_LOOK_URL=http://look.example
export OPAL_SAY_URL=http://say.example
export OPAL_THINK_URL=http://think.example
export OPAL_TOKEN='<bearer-token>'
```

These URLs are examples, not deployment defaults. Prefer a secret manager
or protected environment injection for tokens. Do not put camera passwords
in RTSP URLs; LOOK source definitions support `secret_ref`.

### Shared options

| Proposed option | Purpose and contract mapping |
|---|---|
| `--url URL` | Override the selected service base URL. |
| `--token TOKEN` | Override bearer authentication; prefer `OPAL_TOKEN` to avoid shell history. |
| `--session-id ID` | Set `X-Opal-Session-Id`. |
| `--transaction-id ID` | Set `X-Opal-Transaction-Id`; reuse it across one logical ecosystem workflow. |
| `--request-id ID` | Set `X-Opal-Request-Id`. |
| `--causation-id ID` | Set `X-Opal-Causation-Id` when this request was caused by another request/event. |
| `--if-match ETAG` | Send the strong `If-Match` precondition on protected mutations. Missing preconditions produce 428; stale ones produce 412. |
| `--cursor CURSOR`, `--limit N` | Control cursor pagination where supported. A cursor remains bound to its original filters. |
| `--idempotency-key KEY` | Send `Idempotency-Key` only on operations that declare it. This does not guarantee exactly-once external side effects. |
| `--body @file.json` | Supply a complete JSON request body using the operation's schema. |
| `--json` | Emit machine-readable API responses for scripting. |
| `--output PATH` | Write returned audio, image, archive or artifact bytes to a file. |

For an ETag-protected update, read the current resource first, retain the
returned strong ETag, and pass it with the mutation. On 412, re-read and
reapply the intended change rather than blindly retrying. Correlation IDs
provide tracing, not authentication or distributed transaction atomicity.

---

# 1. EVENT independently

EVENT receives JSON events, evaluates topic rules and ANDed conditions,
executes registered actions, and retains event/execution history. It can be
used by scripts, webhooks, sensors or any other HTTP client without another
OPAL service.

## Command and option map

The following names are proposed:

| Command | Important inputs and behavior |
|---|---|
| `opal event publish --topic TOPIC --data JSON [--source ID]` | Publish an event. The request can also carry optional `id` and `timestamp` fields as allowed by `EventInput`. |
| `opal event list [--topic T] [--source S] [--from TIME] [--to TIME] [--cursor C] [--limit N]` | Search stored events. |
| `opal event show EVENT_ID` | Retrieve one stored event. |
| `opal event remove EVENT_ID` | Delete one stored event. |
| `opal event clear` | Delete stored event history; this is destructive and should require confirmation. |
| `opal event topics list` | List observed topics. |
| `opal event rules list` | List rules. |
| `opal event rules add --body @rule.json` | Create a rule with `id`, `enabled`, `topic`, `conditions` and `actions`. |
| `opal event rules show RULE_ID` | Inspect a rule and obtain its current ETag where returned. |
| `opal event rules update RULE_ID --body @patch.json --if-match ETAG` | Apply a partial rule update. |
| `opal event rules remove RULE_ID --if-match ETAG` | Remove a rule when the operation requires the precondition. |
| `opal event rules test RULE_ID --body @candidate-event.json` | Test rule matching without executing its actions. |
| `opal event actions list` | List registered actions. |
| `opal event actions add --body @action.json` | Register a shell, HTTP or Python action. |
| `opal event actions show ACTION_ID` | Inspect configuration, discovery metadata and schema. |
| `opal event actions update ACTION_ID --body @patch.json --if-match ETAG` | Patch an action. |
| `opal event actions remove ACTION_ID --if-match ETAG` | Delete an action only when it is not in use. |
| `opal event actions execute ACTION_ID [--body @input.json]` | Execute a registered action manually; side effects are real. |
| `opal event executions list [--status S] [--rule-id R] [--action-id A] [--event-id E] [--cursor C] [--limit N]` | Search action executions. |
| `opal event executions show EXECUTION_ID` | Inspect one execution and its result/error details. |
| `opal event stats` | Read event and execution statistics. |
| `opal event health show` / `health live` / `health ready` | Read service health and probes. |
| `opal event settings list` / `settings show KEY` | Read settings; secrets remain masked. |
| `opal event settings set KEY --value JSON --if-match ETAG` | Replace one setting. |
| `opal event settings patch --body @settings.json --if-match ETAG` | Patch the settings collection where supported. |
| `opal event settings remove KEY --if-match ETAG` | Reset/remove a setting according to the shared settings contract. |
| `opal event backup export [--output PATH]` | Export portable configuration without secrets/history. |
| `opal event backup validate --body @bundle.json` | Validate an import candidate. |
| `opal event backup import --body @bundle.json --if-match ETAG` | Atomically import configuration; a failed import preserves the previous configuration. |

Rule conditions support `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`,
`not_in`, `exists` and `contains`; multiple conditions are ANDed. Action
schemas discriminate between:

- **shell** — executable or script-path mode, arguments/options and timeout;
- **HTTP** — method, URL, headers and body mode;
- **Python** — module, function and timeout.

Actions can also carry `description`, `input_schema`, `keywords` and
`suggested_prompts` so clients can discover their purpose. Publishing to
ZeroMQ is a two-frame topic-plus-JSON protocol; the HTTP CLI must not imply
that it controls arbitrary transport frames.

## Standalone use case: temperature threshold with an audit trail

Assume `page-on-call` is already a reviewed HTTP action and an external
sensor publishes temperature readings.

```console
opal event actions show page-on-call
opal event rules add --body @hot-room-rule.json
opal event rules test hot-room --body @sample-temperature-event.json
opal event publish --topic sensor.lab \
  --data '{"temperature":33.2}' --source bench-pi
opal event list --topic sensor.lab --limit 10
opal event executions list --rule-id hot-room --limit 20
opal event stats
```

`hot-room-rule.json` selects `sensor.*`, tests `data.temperature gt 30`,
and references `page-on-call`. Testing the rule does not execute the pager.

EVENT alone can also deduplicate/audit incoming signals, route webhooks,
invoke approved local scripts, maintain topic-specific automation and
export its configuration. It cannot by itself recognize speech, inspect a
camera, synthesize audio or run an LLM.

---

# 2. LISTEN independently

LISTEN provides wakeword and speech recognition, intent and slot
extraction, recognition profiles, diagnostic tests, utterance logs and a
regression workflow. Text recognition works without an audio device. Live
recognition requires host audio configuration, but not LOOK, SAY, THINK or
EVENT.

## Command and option map

Proposed command names:

| Command | Important inputs and behavior |
|---|---|
| `opal listen wakewords list` | List wakewords. |
| `opal listen wakewords add --body @wakeword.json` | Create using fields such as `name`, `enabled` and `confidence_threshold`. |
| `opal listen wakewords show/update/remove WAKEWORD_ID` | Inspect, patch or remove one wakeword; protected mutations use `--if-match` where required. |
| `opal listen intents list` | List intents. |
| `opal listen intents add --body @intent.json` | Create with name, description, enabled state, confidence threshold and optional phrases. |
| `opal listen intents show/update/remove INTENT_ID` | Manage one intent. |
| `opal listen intents phrases list INTENT_ID` | List training phrases. |
| `opal listen intents phrases add INTENT_ID --text PHRASE` | Add a phrase; slot placeholders belong to the phrase grammar. |
| `opal listen intents phrases remove INTENT_ID PHRASE_ID` | Remove a phrase. |
| `opal listen slots list` | List slot definitions. |
| `opal listen slots add --body @slot.json` | Create with `name`, `slot_type` and optional description. |
| `opal listen slots show/update/remove SLOT_ID` | Manage a slot definition. |
| `opal listen slots values list SLOT_ID` | List canonical values. |
| `opal listen slots values add SLOT_ID --value VALUE` | Add a canonical string value. |
| `opal listen slots values remove SLOT_ID VALUE_ID` | Remove a value. |
| `opal listen slots aliases list SLOT_ID VALUE_ID` | List aliases for a value. |
| `opal listen slots aliases add SLOT_ID VALUE_ID --alias TEXT` | Add an alternate spoken form. |
| `opal listen slots aliases remove SLOT_ID VALUE_ID ALIAS_ID` | Remove an alias. |
| `opal listen profiles list` | List recognition profiles. |
| `opal listen profiles add --body @profile.json` | Configure profile name, wakewords, enabled intents/slots, confidence thresholds and VAD fields. |
| `opal listen profiles show/update/remove PROFILE_ID` | Manage a profile. |
| `opal listen profiles activate PROFILE_ID` | Make a profile active. |
| `opal listen recognition test-text --text TEXT [--save-log]` | Test text recognition. Diagnostic requests do not publish external events. |
| `opal listen recognition test-audio --file AUDIO.wav [--save-log] [--require-wakeword]` | Test uploaded audio; wakeword enforcement is optional. Diagnostic only. |
| `opal listen recognition start` | Start the configured recognition pipeline. |
| `opal listen recognition stop` | Stop it. |
| `opal listen recognition status` | Read pipeline state and metrics. |
| `opal listen recognition stream [--debug]` | Consume recognition results as a stream; Ctrl-C ends the local consumer, not necessarily the recognition pipeline. |
| `opal listen logs list [--intent-name NAME] [--matched BOOL] [--cursor C] [--limit N]` | Search recognition logs. |
| `opal listen logs count` | Count logs. |
| `opal listen logs show LOG_ID` | Inspect one utterance log. |
| `opal listen failed-utterances list [--reviewed BOOL] [--promoted BOOL] [--limit N] [--offset N]` | Review failed recognition. |
| `opal listen failed-utterances add --body @utterance.json` | Add a failed-utterance record where manual entry is desired. |
| `opal listen failed-utterances show/update/remove ID` | Manage a failed utterance. |
| `opal listen failed-utterances promote ID --body @promotion.json` | Promote it into training data and optionally create a regression test according to the promotion schema. |
| `opal listen regression list` | List regression tests. |
| `opal listen regression add --body @regression.json` | Define phrase, expected intent and expected slots. |
| `opal listen regression show/update/remove TEST_ID` | Manage a test. |
| `opal listen regression run [--enabled-only]` | Execute the regression suite. |
| `opal listen performance last` | Read the latest performance sample. |
| `opal listen performance summary [--limit N]` | Summarize performance. |
| `opal listen performance history [--cursor C] [--limit N]` | Page through performance history. |
| `opal listen health audio-devices` | Enumerate host audio devices. |
| `opal listen health show` / `health live` / `health ready` | Health and probes. |
| `opal listen settings list/show/set/patch/remove` | Shared settings commands with `--if-match` on protected mutations. |
| `opal listen backup list/create` | List or create server-side archives. |
| `opal listen backup download FILENAME --output PATH` | Download an archive. |
| `opal listen backup restore FILENAME --if-match ETAG` | Atomically restore an archive. |
| `opal listen backup remove FILENAME --if-match ETAG` | Delete an archive when supported by the route. |
| `opal listen backup export/validate/import` | Portable configuration operations; import/restore preserve the previous configuration on failure. |

LISTEN event publication is disabled by default and must be configured
separately. Its declared event metadata schema version is `2.0`; most other
OPAL producers declare `1.0`. Consumers must ignore unknown metadata fields,
but the contracts do not document a field-by-field 1.0-to-2.0 mapping.

## Standalone use case: add a room command and prevent regressions

```console
opal listen intents add --body @lights-intent.json
opal listen slots add --body @room-slot.json
opal listen slots values add <room-slot-id> --value kitchen
opal listen slots values add <room-slot-id> --value office
opal listen slots aliases add <room-slot-id> <kitchen-value-id> --alias 'the kitchen'
opal listen recognition test-text \
  --text 'turn on the kitchen lights' --save-log
opal listen regression add --body @kitchen-regression.json
opal listen regression run --enabled-only
opal listen logs list --intent-name lights.set --limit 10
opal listen performance last
```

For live audio, inspect devices and profile state first:

```console
opal listen health audio-devices
opal listen recognition status
opal listen recognition start
opal listen recognition stream
opal listen recognition stop
```

LISTEN alone supports vocabulary authoring, wakeword validation, offline
text/audio diagnosis, recognition quality review and regression testing.
Executing a light command or speaking an answer requires an external action
or another service.

---

# 3. LOOK independently

LOOK manages visual sources, engines, model registrations, processing
pipelines, profiles, zones, rules, monitors, synchronous analysis, live
sessions, finite jobs, immutable observations and retained media. It can
store and query observations without EVENT; event publication is optional.

LOOK command names are normative. Resource commands use `add`, `remove`,
`update`, `list` and `show`; operational verbs remain explicit. Options use
kebab-case. There are no implicit `create`, `delete`, `get` or `set`
aliases.

## Command and option map

| Command group | Operations and important options |
|---|---|
| `opal look capabilities` | `show` — discover engines/tasks/formats and optional capabilities before constructing a pipeline. |
| `opal look engines` | `list`, `show ENGINE_ID`, `update ENGINE_ID --body @patch.json --if-match ETAG`. Engine changes configure known engines; they do not install them. |
| `opal look models` | `list`, `show`, `add`, `update`, `remove`. Model registration uses `id`, `engine_id`, `resource_ref`, `tasks` and `options`; mutations use ETags where required. |
| `opal look sources` | `list`, `add`, `show`, `update`, `remove`, `status`, `probe`, `frame`, `capture`, `stream`. Create fields include `id`, `kind`, `name`, `locator`, `secret_ref`, `options` and `enabled`. Source kinds include `usb`, `rtsp`, `http_mjpeg`, `file`, `media` and `adapter`. |
| `opal look pipelines` | `list`, `add`, `show`, `update`, `remove`, `validate`. Inputs include `id`, `name`, ordered/DAG `stages` and optional description. Validation is non-mutating. |
| `opal look profiles` | `list`, `add`, `show`, `update`, `remove`, `activate`. Bodies follow the profile create/patch schemas. |
| `opal look zones` | `list`, `add`, `show`, `update`, `remove`. Define `id`, `source_id`, `name`, `kind` (`line` or `polygon`) and geometry points. |
| `opal look rules` | `list`, `add`, `show`, `update`, `remove`. Configure source, kind, zone/class filters, threshold, duration, cooldown and capture/clip-on-match fields. |
| `opal look monitors` | `list`, `add`, `show`, `update`, `remove`. Configure `id`, `name`, `source_id`, optional pipeline/profile, enabled state and `restart_policy` (`on_failure`, `always`, `never`). |
| `opal look analyze` | `run --body @analysis.json`, `image --file IMAGE ...`. Perform synchronous source or uploaded-image analysis with the declared pipeline/profile/options/retention fields. |
| `opal look sessions` | `start`, `list`, `show`, `stop`, `observations`, `stream`, `preview`. Start accepts source plus pipeline/profile/options/retention/auto-start. List filters include state/source/cursor/limit. |
| `opal look jobs` | `submit --body @job.json`, `list [--state S] [--kind K] [--cursor C] [--limit N]`, `show JOB_ID`, `cancel JOB_ID`. Kinds are `analyze_video`, `export_annotated_video` and `extract_clip`. |
| `opal look observations` | `list [--source-id S] [--monitor-id M] [--job-id J] [--task T] [--label L] [--after TIME] [--before TIME] [--cursor C] [--limit N]`, `show OBSERVATION_ID`. |
| `opal look media` | `upload --file PATH [--ttl-seconds N]`, `list [--kind K] [--source-id S] [--cursor C] [--limit N]`, `show`, `remove`. Uploads are immutable image/video inputs, not arbitrary filesystem paths. |
| `opal look captures` | `list`, `show`, `download CAPTURE_ID --output PATH`, `remove`. Supports exact retained capture bytes and pagination/filter fields declared by the routes. |
| `opal look recordings` | `start --body @recording.json`, `list`, `show RECORDING_ID`, `stop RECORDING_ID`. Recording is an explicit lifecycle independent of opening a viewer. |
| `opal look artifacts` | `list`, `show`, `download ARTIFACT_ID --output PATH`, `remove`. Download derived clips/output, with range support where declared. |
| `opal look metrics` | `show` — operational counters. |
| `opal look events` | `status` — event publication queue/drop status; publication remains opt-in and allowlisted. |
| `opal look settings` | `list`, `show KEY`, `patch --body @settings.json`, `update KEY --body @value.json`, `reset KEY`. Protected mutations require `--if-match`. |
| `opal look configuration` | `export`, `validate --body @configuration.json`, `import --body @configuration.json --if-match ETAG`. Export excludes secrets/history; import is validated and atomic. |
| `opal look health` | `show`, `live`, `ready`. |

### Frame, preview and stream options

`source frame` can accept pipeline/processing options including
`pipeline_id`, `target_fps`, `width`, `height`, `quality` and
`presentation_filter`. It returns a fresh JPEG and does not imply retained
inference.

`source stream` and session preview expose applicable presentation options
such as `annotations`, `pipeline_id`, `classes`, `min_confidence`,
`show_labels`, `show_boxes`, `show_confidence`, `target_fps`, `width`,
`height`, `quality` and `presentation_filter`. These options are fixed when
the stream starts; changing them requires a new stream. A source stream is
an ephemeral MJPEG viewer, not a durable session or recording.

Session event streaming is SSE. It can resume with `Last-Event-ID` while
the ID remains in the bounded cache; an expired cursor can produce 409.
Start a new stream/session decision rather than assuming unlimited replay.

LOOK rule kinds are `object_appears`, `object_disappears`, `enters_zone`,
`exits_zone`, `line_crosses`, `count_threshold` and `dwell_time`. Optional
tasks such as anomaly detection, captioning, OCR, segmentation, pose, VQA,
depth, embeddings and classification are available only when advertised by
`capabilities show` and supported by the selected pipeline.

### Engine and model installation

There is no `opal look engines install`, model download or training API.
Install a supported runtime and its model artifacts on the LOOK host using
that engine's own documentation, then register the already-available model
resource and validate the pipeline:

```console
# Host-level, engine-specific: install runtime and model files first.
opal look engines list
opal look models add --body @local-model-registration.json
opal look capabilities show
opal look pipelines validate --body @pipeline.json
```

`resource_ref` refers to an implementation-supported local/discovered
resource. It is not permission to read arbitrary host filesystem paths.

## Standalone use case: register a camera and collect observations

```console
opal look capabilities show
opal look sources add --body @camera-1.json
opal look sources probe camera-1
opal look sources status camera-1
opal look pipelines validate --body @person-pipeline.json
opal look pipelines add --body @person-pipeline.json
opal look sessions start --body @camera-1-session.json
opal look sessions observations <session-id> --limit 50
opal look observations list --source-id camera-1 --task detect \
  --label person --limit 50
opal look sessions preview <session-id> --show-labels --show-boxes
opal look sessions stop <session-id>
```

LOOK alone can also analyze uploaded video, export annotated media, capture
frames, retain rule-triggered clips and search results. It does not require
a language model or speech service for any of those tasks.

---

# 4. SAY independently

SAY discovers installed text-to-speech engines, registers voices and
profiles, generates completed audio and streams raw PCM. Applications can
use it without EVENT, LISTEN, LOOK or THINK.

## Command and option map

Proposed command names:

| Command | Important inputs and behavior |
|---|---|
| `opal say engines list` | List discovered engines, including enabled/available state. |
| `opal say engines show ENGINE_ID` | Inspect options, version, tasks, device types and capability metadata. |
| `opal say engines update ENGINE_ID --body @patch.json --if-match ETAG` | Change `enabled` and engine `options`. |
| `opal say engines validate ENGINE_ID` | Validate availability and configuration. |
| `opal say voices list [--engine-id ID] [--enabled BOOL]` | List voices with optional filters. |
| `opal say voices add --body @voice.json` | Register `voice_id`, `name`, `engine_id`, `engine_voice_ref` plus supported language/options fields. |
| `opal say voices show/update/remove VOICE_ID` | Inspect or modify a voice; use `--if-match` on protected mutations. |
| `opal say voices validate VOICE_ID` | Validate the engine voice reference. |
| `opal say voices test VOICE_ID --body @test.json [--output PATH]` | Generate a validation sample according to the voice-test schema. |
| `opal say profiles list` | List reusable generation profiles. |
| `opal say profiles add --body @profile.json` | Configure voice and generation defaults. |
| `opal say profiles show/update/remove PROFILE_ID` | Manage a profile. |
| `opal say profiles activate PROFILE_ID` | Activate a profile. |
| `opal say generate --text TEXT [--profile-id P] [--voice-id V] [--engine-id E] [--speed N] [--volume N] [--output-format F] [--sample-rate N] [--engine-options JSON] [--output PATH]` | Generate one completed audio result. `text` is required; other fields override/select generation behavior. |
| `opal say stream --text TEXT [generation options] [--output PATH]` | Stream headerless signed 16-bit little-endian mono PCM. WAV is not supported on this route. |
| `opal say settings list/show/set/patch/remove` | Shared settings operations; protected mutations require `--if-match`. |
| `opal say health show` / `health live` / `health ready` | Health and probes. |
| `opal say backup list/create` | List/create server-side archives. |
| `opal say backup download FILENAME --output PATH` | Download archive bytes. |
| `opal say backup restore FILENAME --if-match ETAG` | Atomically restore a previous archive. |
| `opal say backup remove FILENAME --if-match ETAG` | Remove an archive where supported. |
| `opal say backup export/validate/import` | Validate and atomically import portable configuration. |

Engine states are `ready`, `unavailable`, `error` and `disabled`. A voice
registration does not install its underlying engine voice; the engine
reference must already be meaningful to the selected engine.

### Engine installation

SAY explicitly leaves engine installation and discovery to the
implementation. On the SAY host:

1. Select an engine supported by the deployment.
2. Install that engine's runtime and voice/model files using the engine
   vendor's instructions and the host's normal package/file-management
   process.
3. Configure any engine-specific paths through deployment configuration or
   the declared engine options. Keep credentials and license material out
   of CLI output.
4. Restart or trigger host discovery only if that implementation requires
   it; there is no OpenAPI discovery/restart endpoint to invoke.
5. Verify discovery through the CLI, register a voice, and test it.

```console
# Host-level installation has already been completed here.
opal say engines list
opal say engines show <engine-id>
opal say engines validate <engine-id>
opal say voices add --body @local-voice.json
opal say voices validate <voice-id>
opal say voices test <voice-id> --body @voice-test.json --output voice-test.wav
```

## Standalone use case: reusable voice profile and two output modes

```console
opal say profiles add --body @narrator-profile.json
opal say profiles activate narrator
opal say generate --text 'The inspection is complete.' \
  --profile-id narrator --output inspection.wav
opal say stream --text 'Streaming playback is ready.' \
  --profile-id narrator --output playback.pcm
```

The PCM file has no WAV header. If piping it to a local player, supply the
sample rate selected by the request/profile; for example, `22050` is only
valid if that was the negotiated/configured rate. Audio output devices and
playback are outside the SAY API.

SAY alone handles announcements, notification audio, voice prototyping,
profile management and engine validation. It does not decide what to say.

---

# 5. THINK independently

THINK accepts prompts as durable tasks, returns task IDs with HTTP 202,
exposes progress/output and supports serialized conversational sessions.
It is useful for scripts and batch work without any other OPAL service.

## Command and option map

These names follow THINK's `x-opal-cli` metadata:

| Command | Important inputs and behavior |
|---|---|
| `opal think task create --prompt TEXT [--session-id ID] [--model-id ID] [--context JSON] [--max-steps N] [--timeout-seconds N] [--metadata JSON] [--idempotency-key KEY]` | Submit a durable task. `prompt` is required; the response is 202 with a task ID. |
| `opal think task list [--status S] [--session-id ID] [--cursor C] [--limit N]` | Search tasks. |
| `opal think task show TASK_ID` | Retrieve state, progress, result or error. |
| `opal think task watch TASK_ID` | Consume the task's stream until completion/failure or local interruption. Closing the viewer does not itself cancel the task. |
| `opal think task cancel TASK_ID` | Request cancellation; check the resulting task state. |
| `opal think session add --title TITLE` | Create a managed conversation session. |
| `opal think session list` | List sessions. |
| `opal think session show SESSION_ID` | Inspect session metadata/history exposed by the contract. |
| `opal think session remove SESSION_ID` | Remove a session. |
| `opal think model list` | List configured provider/model catalog entries, including unavailable entries. |
| `opal think model show MODEL_ID` | Inspect one model. |
| `opal think settings list` / `settings show KEY` | Read provider/runtime configuration with secrets masked. |
| `opal think settings set KEY --value JSON --if-match ETAG` | Update a setting. Provider endpoints and secret references belong here, not in prompts. |
| `opal think settings remove KEY --if-match ETAG` | Reset/remove a setting according to the shared contract. |
| `opal think health` | Read health; health probes are also exposed by the API. |
| `opal think ask ...` | Convenience name for task create followed by watch/show; it is not a separate REST endpoint. |
| `opal think chat ...` | Convenience loop that optionally creates a session and submits one task per turn. |

An existing managed session serializes active tasks so turns remain
ordered. Context, retrieved observations and transcripts should be treated
as untrusted data, not as instructions that override system policy.

### Provider and model setup

THINK has no model installation or deletion operation. Configure provider
adapters, endpoints and secret references on the THINK host/service through
settings, then inspect the discovered catalog:

```console
# Host/service provider configuration is already in place.
opal think model list
opal think model show <model-id>
opal think health
```

An entry with `available: false` is not made usable by repeatedly
submitting tasks. Fix its provider configuration or choose an available
model.

## Standalone use case: durable document analysis

```console
opal think model list
opal think session add --title 'Quarterly report review'
opal think task create \
  --prompt 'Identify the three largest risks in this report.' \
  --session-id <session-id> --context @report-context.json \
  --timeout-seconds 120
opal think task watch <task-id>
opal think task show <task-id>
opal think task create \
  --prompt 'Turn those risks into an action checklist.' \
  --session-id <session-id>
opal think task watch <second-task-id>
```

Cancellation and cleanup are explicit:

```console
opal think task cancel <task-id>
opal think task show <task-id>
opal think session remove <session-id>
```

THINK alone supports question answering, summarization, classification,
structured extraction, multi-turn sessions and cancellable background
reasoning. It does not acquire microphone/camera input or play audio.

---

# Ecosystem orchestration

There is no single cross-service OPAL endpoint. An ecosystem CLI performs
several API calls, passes returned IDs/data between them, and keeps their
failure semantics visible. For example, `sources stream` does not create a
LOOK session, `recognition test-text` does not publish an event, and
creating a THINK task does not send its result to SAY automatically.

For compound workflows:

1. Generate/reuse one transaction ID across related requests.
2. Discover capabilities and health before starting a long chain.
3. Capture returned IDs from JSON responses; never guess them.
4. Stop streams/watchers explicitly and cancel tasks/jobs when required.
5. Do not silently retry side-effecting actions.
6. Keep provider credentials, camera credentials and personal media out of
   prompts and logs.

The following 20 scenarios show command sequences. They assume the named
sources, pipelines, actions, profiles and host integrations have been
installed and configured. A sequence is a workflow blueprint, not a promise
that a default deployment already contains those resources.

## Home automation and property

### 1. Announce a package at the front door

**Goal:** detect a package, retain evidence, and invoke a configured speech
adapter without requiring the camera to know anything about audio.

```console
opal look capabilities show
opal look rules add --body @package-rule.json
opal event actions add --body @package-speech-adapter-action.json
opal event rules add --body @package-event-rule.json
opal event rules test package-announcement --body @sample-package-event.json
opal look observations list --source-id porch --label package --limit 10
opal event executions list --rule-id package-announcement --limit 10
```

The LOOK rule uses `object_appears` and a `package` class filter; the EVENT
rule selects the deployment's published `opal.look.*` topic. The HTTP
adapter is deployment-specific because SAY generates audio but does not
select a physical speaker.

### 2. Notify when the garage remains open

**Goal:** turn a persistent visual state into a delayed reminder instead of
an alert on every frame. This assumes the installed pipeline exposes a
`garage_open` class or equivalent typed observation.

```console
opal look sources probe garage-camera
opal look rules add --body @garage-open-rule.json
opal look monitors add --body @garage-monitor.json
opal event actions add --body @notify-resident-action.json
opal event rules add --body @garage-open-event-rule.json
opal look observations list --source-id garage-camera --label garage_open
opal event executions list --rule-id garage-open-reminder --limit 20
```

Use the rule's duration/cooldown fields to avoid repeated notifications.
The visual class must actually be supported; it is not a built-in guarantee.

### 3. Voice-activated “away from home” scene

**Goal:** recognize one command and call a reviewed home-automation HTTP
endpoint.

```console
opal listen intents add --body @away-intent.json
opal listen recognition test-text --text 'set the house to away mode'
opal event actions add --body @away-scene-http-action.json
opal event rules add --body @away-intent-event-rule.json
opal event rules test away-scene --body @sample-away-intent-event.json
opal say generate --text 'Away mode activated.' --output away-ack.wav
```

The last command demonstrates acknowledgment generation; connecting the
recognition result to EVENT and the acknowledgment to a speaker are local
integrations. Test text never publishes the intent by itself.

### 4. Basement anomaly escalation

**Goal:** monitor a pump/utility area with an optional anomaly pipeline and
route confirmed events to an escalation action.

```console
opal look capabilities show
opal look pipelines validate --body @basement-anomaly-pipeline.json
opal look monitors add --body @basement-monitor.json
opal look events status
opal event actions add --body @escalation-action.json
opal event rules add --body @basement-anomaly-event-rule.json
opal look observations list --source-id basement --task anomaly --limit 20
```

Proceed only if anomaly support is advertised. A camera anomaly signal is
not a substitute for certified leak, fire or life-safety sensors.

### 5. Vacation security digest

**Goal:** collect perimeter activity during a trip and summarize selected
observations on demand.

```console
opal look monitors add --body @vacation-monitor.json
opal look rules add --body @perimeter-person-rule.json
opal look observations list --source-id perimeter \
  --after '<start-time>' --before '<end-time>' --limit 100
opal think task create \
  --prompt 'Summarize these observations without identifying anyone.' \
  --context @perimeter-observations.json
opal think task watch <task-id>
opal say generate --text '<approved-summary>' --output vacation-digest.wav
```

Review the observations and generated summary before distributing it.
LOOK's contract does not provide identity recognition.

## Education and accessibility

### 6. Reading practice coach

**Goal:** compare a student's spoken reading with the assigned passage and
return encouraging feedback.

```console
opal listen recognition test-audio --file reading.wav --save-log
opal listen logs list --limit 1
opal think task create \
  --prompt 'Give brief supportive reading feedback using this transcript and passage.' \
  --context @reading-exercise.json
opal think task watch <task-id>
opal say generate --text '<reviewed-feedback>' --profile-id tutor \
  --output reading-feedback.wav
```

### 7. Language phrase laboratory

**Goal:** add a phrase, verify expected intent recognition, and keep a
repeatable regression before using it in a lesson.

```console
opal listen intents add --body @library-location-intent.json
opal listen regression add --body @french-library-regression.json
opal listen recognition test-audio --file french-attempt.wav --save-log
opal listen regression run --enabled-only
opal think task create \
  --prompt 'Explain the recognition error and suggest one pronunciation exercise.' \
  --context @language-attempt.json
opal think task watch <task-id>
opal say generate --text '<exercise>' --output pronunciation-coach.wav
```

Recognition confidence is not a definitive pronunciation score; a teacher
should remain in the loop.

### 8. Spoken flashcard deck

**Goal:** generate questions from approved notes, speak each question, and
evaluate the student's answer in a second THINK task.

```console
opal think task create \
  --prompt 'Create five short question-and-answer flashcards from these notes.' \
  --context @lesson-notes.json
opal think task watch <deck-task-id>
opal say generate --text '<first-question>' --output question-1.wav
opal listen recognition test-audio --file answer-1.wav --save-log
opal think task create \
  --prompt 'Compare the recognized answer to the expected answer and explain any gap.' \
  --context @flashcard-answer.json
opal think task watch <grading-task-id>
```

### 9. Museum exhibit explorer

**Goal:** read or caption an exhibit and generate an age-appropriate spoken
explanation.

```console
opal look capabilities show
opal look media upload --file exhibit.jpg
opal look analyze image --file exhibit.jpg --body @exhibit-analysis.json
opal look observations list --task ocr --limit 5
opal think task create \
  --prompt 'Explain this exhibit to a twelve-year-old using only the supplied evidence.' \
  --context @exhibit-observations.json
opal think task watch <task-id>
opal say generate --text '<grounded-explanation>' --output exhibit-guide.wav
```

OCR/caption support must be advertised. If it is absent, use a supported
pipeline or provide text directly to THINK rather than inventing a result.

### 10. Classroom occupancy and ventilation prompt

**Goal:** count aggregate person detections and notify staff when a chosen
threshold is exceeded.

```console
opal look rules add --body @classroom-occupancy-rule.json
opal event actions add --body @ventilation-notice-action.json
opal event rules add --body @classroom-threshold-event-rule.json
opal look observations list --source-id classroom --task detect --label person \
  --after '<class-start>' --before '<class-end>'
opal event executions list --rule-id classroom-threshold --limit 20
```

The LOOK rule uses `count_threshold`; it does not identify students. Any
ventilation control remains an external, safety-reviewed automation.

## Voice assistant

### 11. Ask OPAL a question

**Goal:** turn a recognized utterance into a spoken answer while keeping
the conversation session explicit.

```console
opal listen recognition status
opal listen recognition stream
# The local client supplies the recognized utterance to the next command.
opal think task create --prompt '<recognized-question>' \
  --session-id <conversation-id>
opal think task watch <task-id>
opal think task show <task-id>
opal say stream --text '<completed-answer>' --profile-id assistant \
  --output answer.pcm
```

This is client-side orchestration. Stopping the local LISTEN stream does
not implicitly stop recognition, and closing `task watch` does not cancel
the THINK task.

### 12. Drop in on camera-1

**Goal:** check the camera, open a live annotated view, and optionally start
persistent analysis separately.

```console
opal look sources show camera-1
opal look sources status camera-1
opal look sources stream camera-1 --annotations --show-labels --show-boxes
opal look sessions list --source-id camera-1 --limit 10
opal look sessions start --body @camera-1-session.json
opal look sessions observations <session-id> --limit 20
opal look sessions stop <session-id>
```

The `sources stream` viewer is ephemeral. The explicit session is only
needed when durable analysis/observations are desired; neither command is
an implicit recording.

### 13. Hands-free cooking assistant

**Goal:** preserve recipe context across turns and speak the next step.

```console
opal think session add --title 'Dinner: lentil soup'
opal think task create --prompt 'Build a recipe from these ingredients.' \
  --session-id <cooking-session-id> --context @ingredients.json
opal think task watch <recipe-task-id>
opal say generate --text '<first-step>' --profile-id kitchen --output step-1.wav
opal think task create --prompt 'I only have twenty minutes. Adjust the remaining steps.' \
  --session-id <cooking-session-id>
opal think task watch <adjustment-task-id>
opal say generate --text '<revised-next-step>' --profile-id kitchen \
  --output revised-step.wav
```

### 14. Voice-created reminder

**Goal:** recognize a duration, call a configured scheduler action, and
provide audible confirmation.

```console
opal listen intents add --body @timer-intent.json
opal listen slots add --body @minutes-slot.json
opal listen slots values add <minutes-slot-id> --value five
opal listen recognition test-text --text 'remind me in five minutes'
opal event actions show reminder-scheduler
opal event rules add --body @timer-intent-event-rule.json
opal event rules test reminder-start --body @sample-timer-event.json
opal say generate --text 'Reminder scheduled for five minutes.' \
  --output reminder-confirmation.wav
```

EVENT has no built-in timer resource; `reminder-scheduler` must be an
installed, reviewed action connected to a real scheduler.

### 15. Read a sign aloud

**Goal:** assist a low-vision user by converting a fresh camera image into
spoken text when OCR is available.

```console
opal look capabilities show
opal look sources frame entry-camera --output entry-sign.jpg
opal look analyze image --file entry-sign.jpg --body @ocr-analysis.json
opal look observations list --source-id entry-camera --task ocr --limit 1
opal say generate --text '<recognized-sign-text>' --profile-id accessible \
  --output sign.wav
```

Do not treat imperfect OCR as authoritative for hazards, medication,
finance or other high-stakes instructions.

## Custom, developer and organizational workflows

### 16. CI failure triage with an audible summary

**Goal:** publish a build result, summarize the failure, and generate a
short audio report for an optional office speaker integration.

```console
opal event publish --topic build.finished \
  --data @build-result.json --source ci
opal event rules test ci-failure --body @sample-build-event.json
opal event executions list --rule-id ci-failure --limit 20
opal think task create --prompt 'Summarize the likely failure and first diagnostic step.' \
  --context @build-result.json
opal think task watch <task-id>
opal say generate --text '<reviewed-summary>' --output build-summary.wav
```

Logs can contain secrets or untrusted instructions; sanitize them before
putting them in a model context.

### 17. Retail entrance and queue analytics

**Goal:** measure crossings and detect a queue threshold without retaining
identity information.

```console
opal look zones add --body @entrance-line-zone.json
opal look rules add --body @entrance-crossing-rule.json
opal look rules add --body @queue-count-rule.json
opal event actions add --body @queue-notice-action.json
opal event rules add --body @queue-event-rule.json
opal look observations list --source-id store-cam \
  --after '<opening-time>' --limit 100
opal event executions list --rule-id queue-notice --limit 20
```

`line_crosses` handles entrance crossings; `count_threshold` handles queue
size. Both depend on suitable camera geometry and person detection.

### 18. Wildlife clip catalog

**Goal:** retain animal-triggered clips, inspect the artifacts, and produce
a searchable natural-language summary.

```console
opal look monitors add --body @trail-monitor.json
opal look rules add --body @wildlife-clip-rule.json
opal look observations list --source-id trail-rtsp --task detect --limit 100
opal look artifacts list --limit 50
opal look artifacts download <artifact-id> --output wildlife-clip.mp4
opal think task create \
  --prompt 'Create a factual field log from these observations; do not infer species not present.' \
  --context @wildlife-observations.json
opal think task watch <task-id>
```

The rule uses supported class filters and `clip-on-match`; species labels
come from the deployed model, not from THINK's imagination.

### 19. Elder-care check-in with explicit escalation

**Goal:** detect an unusual dwell period, ask for a response, and route the
result to a configured human escalation path.

```console
opal look rules add --body @living-room-dwell-rule.json
opal event actions show human-check-in-escalation
opal event rules add --body @check-in-escalation-rule.json
opal say generate --text 'Would you like a check-in call?' \
  --profile-id calm --output check-in.wav
opal listen intents add --body @check-in-response-intent.json
opal listen recognition stream
opal event executions list --rule-id check-in-escalation --limit 20
```

This is only an orchestration example, not a medical monitoring guarantee.
Consent, privacy, thresholds, connectivity, false positives, response time
and reliable human escalation require separate design and validation.

### 20. Build a discoverable custom OPAL skill

**Goal:** publish a well-described action, let THINK help select from the
catalog, and execute only an explicitly approved action.

```console
opal event actions add --body @export-weekly-report-action.json
opal event actions list
opal event actions show export-weekly-report
opal think task create \
  --prompt 'Select a relevant registered action and explain its required input; do not execute it.' \
  --context @action-catalog.json
opal think task watch <selection-task-id>
opal event actions execute export-weekly-report --body @approved-input.json
opal event executions list --action-id export-weekly-report --limit 10
```

Use `description`, `input_schema`, `keywords` and `suggested_prompts` to
make the action discoverable. Discovery is not authorization: a person or
separate policy layer must approve execution and its inputs.

---

# Implementation checklist for the Typer CLI

1. Create one `typer.Typer` sub-application per OpenAPI document.
2. Use `x-opal-cli` directly for LOOK and THINK; version and test the
   proposed mapping for EVENT, LISTEN and SAY separately.
3. Generate options from parameters and request schemas rather than
   maintaining a second hand-written field catalog.
4. Preserve operation-specific behavior: 202 task/job admission, streaming
   responses, multipart uploads, byte downloads and SSE resume.
5. Implement read-ETag-then-mutate helpers, but surface 412/428 rather than
   hiding concurrency conflicts.
6. Keep host engine/model installation outside generated API commands.
7. Treat local tools such as `jq`, audio players and stream viewers as
   replaceable adapters, not as guaranteed service behavior.
8. Generate contract-coverage tests so every CLI command maps to an existing
   operation and every option maps to a declared parameter or schema field.
