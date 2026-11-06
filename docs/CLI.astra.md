# OPAL through a hypothetical Typer CLI

This is a proposal for a Python/Typer client of the five OPAL 1.5.0
OpenAPI contracts. There is no implemented CLI in this document, and the
commands have not been executed against running services. The examples
specify how a future client should behave.

The reference below was checked against the current service documents
with their shared kernel references resolved, rather than copied from
other CLI proposals. There are 253 HTTP operations: EVENT 32, LISTEN 74,
LOOK 90, SAY 38 and THINK 19. Shared operations are described once and
mounted explicitly for each service.

## A small executable over five independent APIs

```text
opal event     # publish events, configure rules, execute actions
opal listen    # recognize speech and maintain a vocabulary
opal look      # inspect cameras and run visual processing
opal say       # synthesize speech
opal think     # submit durable reasoning tasks
```

Each sub-application works with only its own service available. A root
Typer application mounts five child applications and shares HTTP transport,
authentication, error handling and serialization. It does not make the
services one transaction.

LOOK supplies normative `{group, command}` metadata in `x-opal-cli`.
THINK supplies command strings and an `ask`/`chat` composition catalogue.
Their names are preserved here. EVENT, LISTEN and SAY command names are
proposed mappings. A few operations inherited by THINK lack CLI metadata;
their proposed names are identified below.

### Installing the client and selecting services

There is no asserted PyPI package named `opal-cli`. Once someone implements
this proposal in a local Python project, an installation could look like:

```bash
# Replace this path with the future CLI project's checkout.
python -m pip install -e ./path/to/opal-cli
opal --help
opal look sources stream --help
```

Proposed environment variables are `OPAL_EVENT_URL`, `OPAL_LISTEN_URL`,
`OPAL_LOOK_URL`, `OPAL_SAY_URL`, `OPAL_THINK_URL`, and corresponding
`OPAL_<SERVICE>_TOKEN` variables. Set them to the actual deployment's URLs
and credentials. The API does not mandate these environment variable names.
Each command also accepts `--url` and `--token` overrides.

### One unambiguous option grammar

The following rules define **all options** used in this guide. The tables
later list every operation's request inputs; schema field names there are
converted mechanically to flags.

| Input or client feature | Proposed CLI syntax |
|---|---|
| Path parameter | Positional argument, in path order: `slots aliases remove SLOT VALUE ALIAS`. |
| Query or top-level body field | Kebab-case flag: `confidence_threshold` → `--confidence-threshold`. |
| Boolean | Explicit `true` or `false`, avoiding ambiguity between omitted and false. |
| Object, array, or arbitrary JSON | JSON argument, or `@file.json` to load JSON. This includes `--context`, `--conditions`, `--options` and `--retention`. |
| Complete JSON request | `--request JSON` or `--request @file.json`; mutually exclusive with individual body fields. Query/header options remain available. |
| Multipart binary field | Named field flag with a path: LISTEN `--file`, LOOK image analysis `--image`. |
| Raw request bytes | `--file PATH` for LOOK media upload, plus the required `--content-type`. This is not multipart. |
| JSON response | `--json`: unchanged API body, with diagnostics on stderr. |
| Binary response | `--output-file PATH`; absent this, bytes go to stdout. Never mix progress text into binary stdout. |
| Response negotiation | `--accept MIME` only when the operation offers that response media type. |
| Response headers | `--headers-file PATH`, a proposed JSON map with lowercase header names. The body remains separate. |
| HTTP precondition | `--if-match '"revision"'`, preserving quotes around a strong ETag. |
| Optional admission key | `--idempotency-key KEY` only on declared operations. |
| SSE resume / byte range | `--last-event-id ID` / `--range 'bytes=0-1023'` only where declared. |
| Help | `--help` at every group and command; generated descriptions, required fields, defaults, bounds and enums. |

`--body` can therefore mean the HTTP action's **body property**, while
`--request` always means the complete API request. Likewise, LOOK job
`--output` is a JSON export-options object, while `--output-file` is a local
destination. Passing `@notes.txt` to a JSON option is invalid unless that
file contains JSON.

The four correlation headers use `--correlation-session-id`,
`--transaction-id`, `--request-id`, and `--causation-id`. Deliberately,
`--session-id` retains its operation-specific meaning as a managed session
reference or query filter; it does not also set the correlation header.
IDs are opaque contract values, not necessarily UUIDs.

Unspecified optional fields remain omitted. Updates do not send defaults
for every field. Unknown options and schema-invalid JSON fail before HTTP.
Arbitrary engine settings remain JSON objects validated by the service;
their keys cannot be exhaustively specified by this suite.

## Shared operations, with the actual service differences

All route fragments below are under `/api/v1` unless shown as `/` or
`/healthz`. `!` marks a required input; `M` marks a required `If-Match`.
An empty input cell means no operation-specific input beyond path arguments.
All commands also inherit the client options above.

### Health, settings, and configuration

| Command suffix | HTTP route | Input |
|---|---|---|
| `health show` | GET `/health/` | |
| `health live`, `health ready` | GET `/health/live`, GET `/health/ready` | |
| `settings list` | GET `/settings/` | |
| `settings patch` | PATCH `/settings/` | M; arbitrary settings map via `--request`. |
| `settings show KEY` | GET `/settings/{key}` | |
| `settings set KEY` | PUT `/settings/{key}` | M; `value!` (any JSON). |
| `settings remove KEY` | DELETE `/settings/{key}` | M. |
| `backup export` | GET `/backup/export` | |
| `backup validate` | POST `/backup/validate` | Configuration export document. |
| `backup import` | POST `/backup/import` | M; optional import body, described below. |
| `backup validate-stored` | GET `/backup/validate` | Validate the implementation's staged configuration. |
| `backup list`, `backup create` | GET `/backup/list`, POST `/backup/create` | |
| `backup download FILENAME` | GET `/backup/download/{filename}` | |
| `backup restore FILENAME` | POST `/backup/restore/{filename}` | M. |
| `backup remove FILENAME` | DELETE `/backup/{filename}` | No declared `If-Match`. |
| `info`, `healthz` | GET `/`, GET `/healthz` | Compatibility/service-information routes. |

Mounts and naming:

- **EVENT:** health, all settings, export, POST validate, import.
- **LISTEN and SAY:** every row, including archives, GET validate, `/`,
  and `/healthz`.
- **LOOK:** health; settings `set` is named **`update`**, and `remove` is
  **`reset`**. Export/validate/import use **`configuration`** and
  `/configuration/...`; there are no archive commands or GET validate.
- **THINK:** all settings and health, no backup routes. Root health is
  **`opal think health`**. `health live`, `health ready`, and
  `settings patch` are proposed names for inherited operations without
  their own THINK CLI metadata.

Configuration export bodies have required `format_version` and `settings`;
optional fields are `exported_at`, `engines`, `voices`, `profiles`,
`wakewords`, `stt`, `intents`, `slots`, `models`, `sources`, `pipelines`,
`zones`, `rules`, `monitors`, `actions`. These are kernel union schemas:
field acceptance does not mean every service implements every section.
Prefer exporting a service's own document and validating it on the target.
Import accepts the forms declared by the shared route; use the portable
export document as `--request @export.json` to avoid relying on a
deployment-specific no-body import.

Settings and exports mask or exclude secrets as specified; exports do not
back up voice files, model weights, credentials, camera recordings, or
history. Import/restore atomicity is per service. Four successful imports
are not one suite-wide atomic migration.

### Shared profiles and engines

LISTEN, LOOK and SAY expose:

| Command suffix | HTTP route | Input |
|---|---|---|
| `profiles list` | GET `/profiles/` | |
| `profiles add` | POST `/profiles/` | M; profile-create fields. |
| `profiles show ID` | GET `/profiles/{profile_id}` | |
| `profiles update ID` | PATCH `/profiles/{profile_id}` | M; profile-patch fields. |
| `profiles remove ID` | DELETE `/profiles/{profile_id}` | M. |
| `profiles activate ID` | POST `/profiles/{profile_id}/activate` | M. |

Profile create fields are `name!`, `description`, `is_active`, `voice_id`,
`speed`, `volume`, `output_format`, `sample_rate`, `engine_options`,
`wakeword_names`, `confidence_thresholds`, `vad_settings`, `enabled_intents`,
`enabled_slots`, `model_paths`, `id`, `pipeline_id`, `inference`, `retention`.
Patch has the same fields except `id`, with no required name. This is the
effective shared schema, not a promise that a SAY voice setting has meaning
in LISTEN. Use the relevant subset: voice settings for SAY, vocabulary/VAD
for LISTEN, and pipeline/inference/retention for LOOK.

LOOK and SAY also expose `engines list` (GET collection), `engines show ID`
(GET item), and `engines update ID` (PATCH item, M). Update fields are
`enabled` and `options`. SAY alone adds `engines validate ID`.

### Concurrency in an actual shell

A proposed `--headers-file` exposes ETags without depending on an
undocumented HEAD endpoint:

```bash
opal look sources list --json --headers-file sources.headers.json > sources.json
SOURCE_ETAG=$(jq -er '.etag' sources.headers.json)
opal look sources add --id camera-1 --name 'Front door' --kind rtsp \
  --locator "$CAMERA_RTSP_URL" --secret-ref "$CAMERA_SECRET_REF" \
  --if-match "$SOURCE_ETAG"
```

Obtain the ETag for the representation the mutation protects, as described
by that operation/deployment; do not assume a settings ETag applies to
every resource. If the relevant read supplies no usable strong ETag, stop
and resolve that deployment gap. Do not substitute `*`. Missing
preconditions yield 428; stale ones yield 412. Re-read and review on 412.
This matters even for **creation** of LOOK resources and shared profiles.

## EVENT: a useful automation service on its own

EVENT ingests events, stores history, evaluates stateless rules and
dispatches registered shell, HTTP or Python actions. A publication receipt
does not acknowledge delivery to every subscriber. A rule is a topic
selection plus ANDed predicates; it is not a general scheduler or
time-window query engine.

### Complete EVENT-specific command map

Add `opal event` before each command. Shared operations above complete its
32-operation surface.

| Command | Method and route | Query/body options |
|---|---|---|
| `events list` | GET `/events/` | `cursor`, `limit`, `topic`, `source`, `from`, `to`. |
| `events publish` | POST `/events/` | `topic!`, `data!`, `id`, `source`, `timestamp`. |
| `events clear` | DELETE `/events/` | |
| `events show ID`, `events remove ID` | GET, DELETE `/events/{event_id}` | |
| `topics list` | GET `/topics/` | No pagination options. |
| `rules list`, `rules add` | GET, POST `/rules/` | Add: `id!`, `enabled!`, `topic!`, `conditions!`, `actions!`. |
| `rules show ID` | GET `/rules/{rule_id}` | |
| `rules update ID` | PATCH `/rules/{rule_id}` | M; `enabled`, `topic`, `conditions`, `actions`. |
| `rules remove ID` | DELETE `/rules/{rule_id}` | M. |
| `rules test ID` | POST `/rules/{rule_id}/test` | `event!` (complete EventInput object). |
| `actions list`, `actions add` | GET, POST `/actions/` | Add: one action variant below. |
| `actions show ID` | GET `/actions/{action_id}` | |
| `actions update ID` | PATCH `/actions/{action_id}` | M; variant-specific patch. |
| `actions remove ID` | DELETE `/actions/{action_id}` | M; referenced actions cannot simply be deleted. |
| `actions execute ID` | POST `/actions/{action_id}/execute` | `event!`, not an unwrapped payload. |
| `executions list` | GET `/executions/` | `status`, `rule_id`, `action_id`, `event_id`, `limit`, `cursor`. |
| `executions show ID` | GET `/executions/{execution_id}` | |
| `stats show` | GET `/stats/` | |

Event data may be any JSON value. Conditions require `{path, operator,
value}`; paths are relative to the normalized event, such as
`data.temperature`. Operators are `eq`, `ne`, `gt`, `gte`, `lt`, `lte`,
`in`, `not_in`, `exists`, `contains`. A missing path is false except for
`exists` with false. Topic suffix `.*` permits hierarchical prefix matching.

All action creates require `id`, `type`, `enabled`. Optional creation
metadata is `description`, `input_schema`, `keywords`, `suggested_prompts`.

| Variant | Additional input fields |
|---|---|
| `type=shell` | `mode!` (`exec`, `sh`, `bash`, `cmd`, `powershell`); `executable` required for exec, `script_path` for interpreter modes; `args`, `stdin` (`event_json` or `none`), `timeout_seconds`. |
| `type=http` | `method!` (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`), `url!`, `body_mode!` (`template`, `event_json`, `none`), `headers`, `body`, `timeout_seconds`. |
| `type=python` | `module!`, `function!`, `timeout_seconds`. |

Patches expose `enabled` and the variant's operational fields, without
`id`, `type`, or the optional discovery metadata. Respect conditional
requirements in shell patches. Fixed executables and HTTP destinations
must satisfy the service's configured allowlists.

An action's `input_schema` validates **event.data**. Manual execution
validation can fail synchronously with 422; rule-triggered dispatch can
produce a dropped execution with `input_validation_failed`. Execution
statuses are `queued`, `running`, `succeeded`, `failed`, `timed_out`,
`dropped`. Inspect execution status rather than equating admission to success.

### Standalone: a complete threshold-to-webhook workflow

Prerequisite: an operator has allowlisted `ALERT_WEBHOOK_URL`, a real
endpoint able to receive event JSON. No other OPAL service is required.

```bash
opal event actions add --id temperature-notify --type http --enabled true \
  --method POST --url "$ALERT_WEBHOOK_URL" --body-mode event_json
opal event rules add --id hot-room --enabled true --topic 'sensor.*' \
  --conditions '[{"path":"data.temperature","operator":"gt","value":30}]' \
  --actions '["temperature-notify"]'
opal event rules test hot-room \
  --event '{"topic":"sensor.lab","data":{"temperature":33}}' --json
# This publication, unlike the test above, can dispatch the configured action.
opal event events publish --topic sensor.lab --source bench-sensor \
  --data '{"temperature":33}' --json
opal event executions list --rule-id hot-room --limit 10 --json
opal event events list --topic sensor.lab --limit 10 --json
```

This also works for CI webhooks, telemetry forwarding and custom tools.
No timer is created by publishing an event containing a duration.

## LISTEN: vocabulary, recognition and quality control

LISTEN can recognize text without audio hardware, diagnose uploaded audio,
run a microphone pipeline and maintain an intent vocabulary. It also
supports failed-utterance review and regression tests. Recognition
confidence is not a pronunciation score or a general acoustic diagnosis.

### Complete LISTEN-specific command map

All names here are proposed. Add `opal listen`; shared health, settings,
profiles, archives, portable configuration, `info` and `healthz` complete
the 74 HTTP operations.

| Command | Method and route | Input options |
|---|---|---|
| `wakewords list`, `wakewords add` | GET, POST `/wakewords/` | Add: `name!`, `enabled`, `confidence_threshold`. |
| `wakewords show ID`, `update ID`, `remove ID` | GET, PATCH, DELETE `/wakewords/{wakeword_id}` | PATCH/DELETE M; patch uses the create fields, all optional. |
| `intents list`, `intents add` | GET, POST `/intents/` | Add: `name!`, `description`, `enabled`, `confidence_threshold`, `phrases`. |
| `intents show ID`, `update ID`, `remove ID` | GET, PATCH, DELETE `/intents/{intent_id}` | PATCH/DELETE M; patch: `name`, `description`, `enabled`, `confidence_threshold`. |
| `phrases list INTENT`, `phrases add INTENT` | GET, POST `/intents/{intent_id}/phrases` | Add: `phrase!`. |
| `phrases remove INTENT PHRASE` | DELETE `/intents/{intent_id}/phrases/{phrase_id}` | M. |
| `slots list`, `slots add` | GET, POST `/slots/` | Add: `name!`, `slot_type`, `description`. |
| `slots show ID`, `update ID`, `remove ID` | GET, PATCH, DELETE `/slots/{slot_id}` | PATCH/DELETE M; patch: `name`, `slot_type`, `description`. |
| `values list SLOT`, `values add SLOT` | GET, POST `/slots/{slot_id}/values` | Add: `value!`. |
| `values remove SLOT VALUE` | DELETE `/slots/{slot_id}/values/{value_id}` | M. |
| `aliases list SLOT VALUE`, `aliases add SLOT VALUE` | GET, POST `/slots/{slot_id}/values/{value_id}/aliases` | Add: `alias!`. |
| `aliases remove SLOT VALUE ALIAS` | DELETE `/slots/{slot_id}/values/{value_id}/aliases/{alias_id}` | M. |
| `recognition test-text` | POST `/recognition/test_text` | Body `text!`; query `save_log`. |
| `recognition test-audio` | POST `/recognition/test_audio` | Multipart `file!`; query `save_log`, `require_wakeword`. |
| `recognition start`, `recognition stop` | POST `/recognition/start`, POST `/recognition/stop` | |
| `recognition status`, `recognition stream` | GET `/recognition/status`, GET `/recognition/stream` | Stream query: `debug`. |
| `logs list` | GET `/logs/` | `limit`, `cursor`, `intent_name`, `matched`. |
| `logs count` | GET `/logs/count` | `limit`, `cursor` (as declared, despite the count name). |
| `logs show ID` | GET `/logs/{log_id}` | |
| `failed list`, `failed add` | GET, POST `/failed_utterances/` | List: `reviewed`, `promoted`, `limit`, `offset`; add: `transcript!`, `expected_intent`, `notes`, `recognition_log_id`. |
| `failed show ID`, `failed update ID`, `failed remove ID` | GET, PATCH, DELETE `/failed_utterances/{fu_id}` | Patch: `expected_intent`, `notes`, `reviewed`, `promoted_to_phrase`; no declared M. |
| `failed promote ID` | POST `/failed_utterances/{fu_id}/promote` | Query `intent_name!`, `create_regression`; no request body. |
| `regression list`, `regression add` | GET, POST `/regression/` | Add: `name!`, `phrase!`, `expected_intent!`, `enabled`, `expected_slots`. |
| `regression show ID`, `update ID`, `remove ID` | GET, PATCH, DELETE `/regression/{test_id}` | Patch uses all create fields optionally; no declared M. |
| `regression run` | POST `/regression/run` | Query `enabled_only`. |
| `performance last` | GET `/performance/last` | |
| `performance summary`, `performance history` | GET `/performance/summary`, GET `/performance/history` | Both: `limit`; history also `cursor`. |
| `health audio-devices` | GET `/health/audio_devices` | |

### Installing recognition engines and using LISTEN alone

Install only ASR/wakeword runtimes supported by the deployed LISTEN
implementation. Follow that implementation's runtime, model, microphone
permissions and device-selection instructions. The OpenAPI document does
not specify a universal package list, model download URL or install route.

```bash
opal listen health audio-devices --json
opal listen settings list --json
opal listen recognition status --json
opal listen intents add --name greeting \
  --phrases '["hello opal","good morning opal"]' --enabled true
opal listen recognition test-text --text 'hello opal' --save-log true --json
opal listen regression add --name greeting-basic --phrase 'hello opal' \
  --expected-intent greeting --expected-slots '{}' --enabled true
opal listen regression run --enabled-only true --json
```

After configuring the audio profile through the protected shared profile
operations, live use is `recognition start`, `recognition stream`, and
`recognition stop`. Run the stream in another terminal or interrupt it
before entering more commands. Disconnecting its viewer does not imply
the service stopped recognition.

Use the result of each diagnostic request directly: it has `transcript`,
`intent_name`, `slot_values`, `matched` and separate confidence fields.
Do not fetch the latest log and assume it belongs to your request.
Diagnostic tests do not publish external events, even with `save_log=true`.

## LOOK: live inspection, batch processing and retained evidence

LOOK handles cameras, finite inputs and visual pipelines. A viewer,
analysis session, monitor, recording, capture and stored observation have
different lifecycles. Starting one does not imply all the others.

### Complete LOOK-specific command map

Add `opal look`. All names below come from the contract. Shared engines,
profiles, settings, configuration and health complete the 90 operations.
Every resource `ID` below is the corresponding item path parameter.

| Resource commands and routes | Create fields (`POST`, command `add`, M) | Patch fields (`PATCH`, command `update ID`, M) |
|---|---|---|
| `models list/add`; `models show/update/remove ID`; `/models/`, `/models/{model_id}` | `id!`, `engine_id!`, `resource_ref!`, `tasks!`, `options` | `display_name`, `options` |
| `sources list/add`; `sources show/update/remove ID`; `/sources/`, `/sources/{source_id}` | `id!`, `kind!`, `name!`, `locator!`, `secret_ref`, `options`, `enabled` | `name`, `locator`, `secret_ref`, `enabled`, `options` |
| `pipelines list/add`; `pipelines show/update/remove ID`; `/pipelines/`, `/pipelines/{pipeline_id}` | `id!`, `name!`, `stages!`, `description` | `name`, `description`, `stages` |
| `zones list/add`; `zones show/update/remove ID`; `/zones/`, `/zones/{zone_id}` | `id!`, `source_id!`, `name!`, `kind!`, `points!`, `enabled` | `name`, `points`, `enabled` |
| `rules list/add`; `rules show/update/remove ID`; `/rules/`, `/rules/{rule_id}` | `id!`, `name!`, `source_id!`, `kind!`, `zone_id`, `class_filters`, `threshold`, `minimum_duration_ms`, `cooldown_ms`, `enabled`, `capture_on_match`, `clip_on_match` | All create fields except `id`, all optional. |
| `monitors list/add`; `monitors show/update/remove ID`; `/monitors/`, `/monitors/{monitor_id}` | `id!`, `name!`, `source_id!`, `pipeline_id`, `profile_id`, `enabled`, `restart_policy`, `options` | All create fields except `id`, all optional. |

For these six resources, list/show are GET without query filters; remove is
DELETE and requires M. These spellings do not imply CRUD for other groups.

| Operational command | Method and route | Inputs |
|---|---|---|
| `capabilities show` | GET `/capabilities/` | |
| `pipelines validate` | POST `/pipelines/validate` | Pipeline create fields; no M. |
| `sources status ID`, `sources probe ID` | GET `/sources/{source_id}/status`, POST `/sources/{source_id}/probe` | |
| `analyze run` | POST `/analyze/` | `source!`, `pipeline_id`, `profile_id`, `options`, `retention`. |
| `analyze image` | POST `/analyze/image` | Multipart `image!`, `pipeline_id`, `profile_id`, `options_json`, `persist_results`; response JSON or JPEG. |
| `sessions start` | POST `/sessions/` | `source_id!`, `pipeline_id`, `profile_id`, `options`, `retention`, `auto_start`; optional idempotency key. |
| `sessions list` | GET `/sessions/` | `cursor`, `limit`, `state`, `source_id`. |
| `sessions show ID`, `sessions stop ID` | GET `/sessions/{session_id}`, POST `/sessions/{session_id}/stop` | |
| `sessions observations ID` | GET `/sessions/{session_id}/observations/` | `cursor`, `limit`. |
| `sessions stream ID` | GET `/sessions/{session_id}/stream` | Optional `Last-Event-ID`. |
| `sessions preview ID` | GET `/sessions/{session_id}/preview` | Presentation query set P below. |
| `jobs submit` | POST `/jobs/` | `kind!`, exactly one `source_id`/`media_id`, `pipeline_id`, `profile_id`, `range`, `options`, `retention`, `output`; optional idempotency key. |
| `jobs list` | GET `/jobs/` | `cursor`, `limit`, `state`, `kind`. |
| `jobs show ID`, `jobs cancel ID` | GET `/jobs/{job_id}`, POST `/jobs/{job_id}/cancel` | |
| `observations list` | GET `/observations/` | `cursor`, `limit`, `source_id`, **`session_id`**, `job_id`, `task`, `label`, `after`, `before`. |
| `observations show ID` | GET `/observations/{observation_id}` | |
| `media list` | GET `/media/` | `cursor`, `limit`. |
| `media upload` | POST `/media/` | Raw binary file and required `Content-Type`; no multipart `ttl_seconds` in this operation. |
| `media show ID`, `media remove ID` | GET, DELETE `/media/{media_id}` | No M. |
| `sources frame ID` | GET `/sources/{source_id}/frame` | `pipeline_id`, `target_fps`, `width`, `height`, `quality`, `presentation_filter`. |
| `sources capture ID` | POST `/sources/{source_id}/captures/` | `retain!`, `annotate`, `session_id`, `observation_id`. |
| `captures list` | GET `/captures/` | `cursor`, `limit`. |
| `captures show ID`, `captures remove ID` | GET, DELETE `/captures/{capture_id}` | No M. |
| `captures download ID` | GET `/captures/{capture_id}/content` | |
| `artifacts list` | GET `/artifacts/` | `cursor`, `limit`. |
| `artifacts show ID`, `artifacts remove ID` | GET, DELETE `/artifacts/{artifact_id}` | No M. |
| `artifacts download ID` | GET `/artifacts/{artifact_id}/content` | Optional Range header. |
| `metrics show`, `events status` | GET `/metrics/`, GET `/events/status` | |
| `recordings start` | POST `/recordings/` | `source_id!`, `include_audio`, `max_duration_seconds`, `output`; optional idempotency key. |
| `recordings list` | GET `/recordings/` | `cursor`, `limit`. |
| `recordings show ID`, `recordings stop ID` | GET `/recordings/{recording_id}`, POST `/recordings/{recording_id}/stop` | |
| `sources stream ID` | GET `/sources/{source_id}/stream` | `annotations`, `pipeline_id`, plus presentation query set P. |

P = `classes`, `min_confidence`, `show_labels`, `show_boxes`,
`show_confidence`, `target_fps`, `width`, `height`, `quality`,
`presentation_filter`. Query `presentation_filter` is compact JSON;
unsupported filters/parameters produce 422. Presentation options change
display, not underlying inference results.

Important nested JSON options:

- `source`: exactly one of `source_id`, `media_id`, `capture_id`, plus
  optional `frame_at_ms`.
- `options`: `target_fps`, `max_frames`, `confidence_threshold`, `classes`,
  `roi`, `engine_options`, `video`, `annotations`. Keep engine-specific
  keys inside `engine_options`.
- `retention`: `persist_results`, `save_raw_frames`,
  `save_annotated_frames`, `ttl_seconds`. Persistence is explicit.
- `range`: required `start_ms`, `end_ms` when supplied.
- `output`: `container` (`mp4`), `video_codec` (`h264`), `annotations`,
  `include_audio`.
- Each pipeline stage: `id!`, `kind!`, `model_id`, `task`, `inputs`,
  `options`, `enabled`, `portable`, `phase`. Kinds are `preprocess`,
  `inference`, `tracker`, `filter`, `transform`, `annotate`; phase is
  `inference_input` or `presentation`.
- `portable`: `filter`, `gate`, `annotation`, `video`.
  A filter has `type!` and `parameters`. Types are `grayscale`,
  `brightness_contrast`, `blur`, `sharpen`, `threshold`, `edges`, `rotate`,
  `flip`, `crop`, `resize`, `motion`; parameter validity is defined by
  `x-opal-filter-catalog`, not by free-form CLI guesses.
- Motion parameters: `sensitivity`, `minimum_area`, `warmup_frames`,
  `visualization` (`none`, `highlight`, `mask`), `roi`. Gate fields are
  `motion_stage_id!`, `when=motion_present`, `periodic_sample_frames`,
  `on_unknown` (`run`, `skip`). Warmup yields unknown, not a negative result.
- Annotation JSON fields: `enabled`, `show_boxes`, `show_labels`,
  `show_confidence`, `show_track_ids`, `classes`, `min_confidence`,
  `show_zones`; video JSON fields: `target_fps`, `width`, `height`, `quality`.
  These nested fields are not automatically standalone query flags.
- Points use normalized `{x,y}` coordinates; an ROI is `{points:[...]}`.

Source kinds are `usb`, `rtsp`, `http_mjpeg`, `file`, `media`, `adapter`.
Rule kinds are `object_appears`, `object_disappears`, `enters_zone`,
`exits_zone`, `line_crosses`, `count_threshold`, `dwell_time`.
Monitor restart policies are `on_failure`, `always`, `never`.
Job kinds are `analyze_video`, `export_annotated_video`, `extract_clip`.
Capabilities determine actual engine tasks and valid labels; a `package`
or `garage_open` label is not universally available.

### Install an engine, then register and use its model

The installation procedure is deployment-specific:

1. Choose an engine adapter the LOOK implementation supports.
2. On the service host, install its runtime and compatible CPU/GPU drivers.
3. Obtain licensed model artifacts from that engine/model publisher and
   make them available to the service account/container.
4. Configure discovery using the implementation's deployment instructions;
   restart only if that implementation requires it.
5. Inspect `engines list`, register the existing opaque resource reference,
   and validate a pipeline. Registration does not download or train.

```bash
opal look engines list --json
opal look capabilities show --json
opal look models list --headers-file model.headers.json --json > models.json
MODEL_ETAG=$(jq -er '.etag' model.headers.json)
opal look models add --id detector --engine-id "$LOOK_ENGINE_ID" \
  --resource-ref "$LOOK_MODEL_REF" --tasks '["detect"]' --if-match "$MODEL_ETAG"
STAGES='[{"id":"detect","kind":"inference","model_id":"detector","task":"detect"}]'
opal look pipelines validate --id detector-pipeline --name Detector --stages "$STAGES"
opal look pipelines list --headers-file pipeline.headers.json --json > pipelines.json
PIPELINE_ETAG=$(jq -er '.etag' pipeline.headers.json)
opal look pipelines add --id detector-pipeline --name Detector --stages "$STAGES" \
  --if-match "$PIPELINE_ETAG"
```

Only use `detect` if the selected engine/model advertises it.

### Standalone: a bounded analysis session and a separate viewer

Prerequisite: `camera-1` was registered using the earlier source example.

```bash
opal look sources probe camera-1 --json
SID=$(opal look sessions start --source-id camera-1 \
  --pipeline-id detector-pipeline --retention '{"persist_results":true}' \
  --json | jq -er '.id')
opal look sessions show "$SID" --json
opal look sessions observations "$SID" --limit 25 --json
opal look sessions stop "$SID" --json
opal look observations list --session-id "$SID" --limit 25 --json
# A separate viewer; Ctrl-C disconnects it. No recording is created.
opal look sources stream camera-1 --annotations false | ffplay -i -
```

A session SSE stream supports bounded `Last-Event-ID` replay; an expired
cursor can return 409. Neither SSE reconnect nor opening MJPEG should
silently create a replacement session. For one-shot image analysis, use
the returned `observations` directly; do not assume an unretained upload
has appeared in `/observations/` under the camera's ID.

## SAY: speech files and PCM streams

SAY alone generates audio from supplied text, manages voice registrations,
validates engines and stores voice defaults. Playback to a physical
speaker is a client/deployment responsibility.

### Complete SAY-specific command map

Add `opal say`. Shared engines, profiles, health, settings, backups and
compatibility routes complete its 38 operations.

| Command | Method and route | Inputs |
|---|---|---|
| `engines validate ID` | POST `/engines/{engine_id}/validate` | |
| `voices list` | GET `/voices/` | Query `engine_id`, `enabled`. |
| `voices add` | POST `/voices/` | `voice_id!`, `name!`, `engine_id!`, `engine_voice_ref!`, `description`, `language`, `enabled`, `engine_options`. |
| `voices show ID` | GET `/voices/{voice_id}` | |
| `voices update ID` | PATCH `/voices/{voice_id}` | M; all create fields except `voice_id`, optional. |
| `voices remove ID` | DELETE `/voices/{voice_id}` | M. |
| `voices validate ID` | POST `/voices/{voice_id}/validate` | |
| `voices test ID` | POST `/voices/{voice_id}/test` | `text`, `speed`, `volume`, `output_format`, `sample_rate`, `engine_options`. |
| `generate` | POST `/generate` | `text!`, `profile_id`, `voice_id`, `engine_id`, `speed`, `volume`, `output_format`, `sample_rate`, `engine_options`. |
| `stream` | POST `/generate/stream` | Same as generate **without `output_format`**. |

`AudioFormat` declares **`wav` and `pcm`**. The stream always emits
headerless signed 16-bit little-endian mono PCM. A filename ending in
`.wav` cannot turn that stream into a WAV file. Engine states are `ready`,
`unavailable`, `error`, `disabled`. Voice registration has no gender field.

### Host installation and standalone narration

Install a TTS runtime supported by this SAY implementation on its host,
obtain the compatible voice artifacts, and give its service account access.
Engine packaging, artifact locations, discovery/restart and GPU setup are
implementation-specific; the API has no engine create/delete/install route.
`engine_voice_ref` is opaque, even when the host uses a filesystem path.

```bash
opal say engines list --json
opal say engines validate "$SAY_ENGINE_ID" --json
opal say voices add --voice-id narrator --name Narrator \
  --engine-id "$SAY_ENGINE_ID" --engine-voice-ref "$SAY_VOICE_REF" \
  --language en-US --enabled true
opal say voices validate narrator --json
opal say voices test narrator --text 'Voice ready.' \
  --output-format wav --output-file voice-test.wav
opal say generate --voice-id narrator --text 'Your export is ready.' \
  --output-format wav --output-file announcement.wav
```

If the engine supports 22050 Hz, this explicitly requests the same rate the
local player consumes:

```bash
opal say stream --voice-id narrator --text 'Live audio.' --sample-rate 22050 \
  | aplay -f S16_LE -r 22050 -c 1
```

To create/activate a profile, obtain its required strong ETag and use the
shared profile operations; profile names are not necessarily profile IDs.
The examples use a known voice ID to avoid assuming a generated profile ID.

## THINK: durable tasks and explicit conversation sessions

THINK accepts work with HTTP 202 and exposes progress, cancellation and a
final answer. A task without `session_id` is stateless; it does not create a
session implicitly. Session GET returns metadata and task count, not a
complete transcript. Retrieve tasks to inspect their answers.

### Complete THINK-specific command map

Add `opal think`; shared settings and health complete its 19 operations.

| Command | Method and route | Inputs |
|---|---|---|
| `task create` | POST `/tasks/` | `prompt!`, `session_id`, `model_id`, `context`, `max_steps`, `timeout_seconds`, `metadata`; optional idempotency key. |
| `task list` | GET `/tasks/` | `status`, `session_id`, `limit`, `cursor`. |
| `task show ID` | GET `/tasks/{task_id}` | |
| `task watch ID` | GET `/tasks/{task_id}/stream` | No declared `Last-Event-ID`. |
| `task cancel ID` | POST `/tasks/{task_id}/cancel` | |
| `session add`, `session list` | POST, GET `/sessions/` | Add: optional `title`; list: `limit`, `cursor`. |
| `session show ID`, `session remove ID` | GET, DELETE `/sessions/{session_id}` | |
| `model list`, `model show ID` | GET `/models/`, GET `/models/{model_id}` | |

`ask` composes task submission and watch/show. `chat` manages an optional
session and submits a task per turn. They are CLI compositions named by the
catalogue, not additional HTTP endpoints. Apply task-create options to each
turn; wait for a session's active task before submitting the next.

`context` is a JSON object; `metadata` is separate tracking data, not model
instructions. `max_steps` is 1–100; `timeout_seconds` is 1–3600, with server
policy caps. Task statuses are `queued`, `running`, `completed`, `failed`,
`cancelled`, `timed_out`. Final user-facing text is `.answer`, authoritative
after `completed`. Stream steps are bounded, redacted summaries, not hidden
reasoning. Admission idempotency does not ensure exactly-once external work.

### Model setup and a standalone analysis

Configure a provider adapter supported by the implementation. For a local
provider, install its runtime/model using that provider's instructions;
for a hosted provider, configure its endpoint and secret reference.
Discover through `model list/show`. No THINK REST operation installs or
deletes models; an unavailable catalog entry is not ready for use.

```bash
opal think model list --json
TID=$(opal think task create --prompt 'Summarize the incident and suggest two checks.' \
  --context '{"report":"The lab sensor stopped reporting after a power interruption."}' \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json > task.json
jq -er 'select(.status=="completed") | .answer | select(type=="string")' task.json
```

Closing `watch` does not cancel the task. Reconnect or use show; cancel
explicitly with `task cancel "$TID"` and inspect its resulting state.

## Ecosystem recipes with explicit data handoffs

The twenty recipes below are client workflows, not claims that cross-service
automation exists by default. They use Bash, `jq` and local files. Set
service URLs/tokens first. Audio recordings such as `question.wav` are
user-supplied inputs: LISTEN's upload endpoint does not record the local mic.

For repeated examples, define these **local shell functions** once. They
use only the proposed CLI commands above; they add no new OPAL endpoint.
`reason` takes a prompt, a JSON-object file and an answer destination.
`say_file` takes a text file and a WAV destination. `inspect_camera` takes
a source ID, a configured pipeline ID and a JSON result destination.

```bash
set -euo pipefail
reason() {
  local tid result
  jq -e 'type=="object"' "$2" >/dev/null
  tid=$(opal think task create --prompt "$1" --context "@$2" \
    --timeout-seconds 120 --json | jq -er '.id')
  opal think task watch "$tid" >&2
  result=$(opal think task show "$tid" --json)
  printf '%s' "$result" |
    jq -er 'select(.status=="completed") | .answer | select(type=="string")' > "$3"
}
say_file() {
  opal say generate --voice-id "$SAY_VOICE_ID" --text "$(cat "$1")" \
    --output-format wav --output-file "$2"
}
inspect_camera() {
  opal look analyze run --source "$(jq -nc --arg id "$1" '{source_id:$id}')" \
    --pipeline-id "$2" --retention '{"persist_results":false}' --json > "$3"
}
```

Set `SAY_VOICE_ID=narrator` after the SAY walkthrough. Set pipeline variables
to already-installed, validated pipelines: `DETECT_PIPELINE`,
`OCR_PIPELINE`, `CAPTION_PIPELINE`, `GARAGE_PIPELINE` or `PLANT_PIPELINE`
as needed. Run `opal look capabilities show` and inspect each pipeline's
model/task support first. If an optional task is unavailable, that recipe
requires deployment work; querying capabilities does not install it.

Long-running monitors and automatic routing are optional extensions to
these finite recipes. Use the documented monitor/rule operations and actual
published topic schemas to automate them. Do not invent per-camera event
topics or assume a diagnostic LISTEN request emits one.

### 1. Ask OPAL a question — voice assistant

Read the exact uploaded recognition response and only synthesize a completed
THINK answer. This avoids treating SSE's last line as answer text.

```bash
opal listen recognition test-audio --file question.wav --save-log false \
  --json > question.json
QUESTION=$(jq -er '.transcript | select(type=="string" and length>0)' question.json)
printf '{}\n' > empty-context.json
reason "$QUESTION" empty-context.json answer.txt
say_file answer.txt answer.wav
# Optional local playback: aplay answer.wav
```

### 2. Drop in on camera-1 — home monitoring

Inspect a current image and open a finite-lifetime viewer. No session,
recording or retained analysis is silently created.

```bash
opal look sources status camera-1 --json
opal look sources probe camera-1 --json
opal look sources frame camera-1 --output-file camera-1.jpg
opal look sources stream camera-1 --annotations false | ffplay -i -
```

Ctrl-C/closing the player disconnects the stream. For an annotated view,
supply a supported pipeline and `--annotations true`.

### 3. Voice-controlled light — home automation

Prerequisites: vocabulary for `lights.on` and a reviewed EVENT HTTP action
`kitchen-light-on` wired to the lighting bridge. This is an explicit
diagnostic-to-action composition, not automatic LISTEN publication.

```bash
opal listen recognition test-text --text 'turn on the kitchen light' \
  --json > light-intent.json
jq -e '.matched==true and .intent_name=="lights.on"' light-intent.json >/dev/null
jq '{topic:"assistant.lights.request",data:{room:"kitchen",state:"on"}}' \
  light-intent.json > light-event.json
EID=$(opal event actions execute kitchen-light-on --event @light-event.json \
  --json | jq -er '.id')
opal event executions show "$EID" --json
```

If the execution is queued/running, check again until terminal before
claiming the light changed. An EVENT action schema/allowlist remains the
authority over the requested effect.

### 4. Is the garage door open? — household status

Prerequisite: a validated garage-state pipeline with documented output
classes. Send its actual result, not an invented confidence value.

```bash
opal look capabilities show --json
inspect_camera garage-camera "$GARAGE_PIPELINE" garage.json
reason 'Report the garage state supported by this observation; say unknown if inconclusive.' \
  garage.json garage-answer.txt
say_file garage-answer.txt garage-answer.wav
```

### 5. Porch delivery review — home notifications

A one-shot review works without assuming a universal package detector.
The caption pipeline must actually advertise caption support.

```bash
opal look capabilities show --json
inspect_camera porch-camera "$CAPTION_PIPELINE" porch.json
reason 'Describe visible objects relevant to a delivery. Do not infer a delivery history.' \
  porch.json porch-summary.txt
say_file porch-summary.txt porch-summary.wav
opal event events publish --topic household.porch.review \
  --data "$(jq -nc --rawfile summary porch-summary.txt '{summary:$summary}')" --json
```

### 6. Greenhouse inspection journal — gardening

A configured plant pipeline provides classifications/measurements. THINK
writes a journal entry from those outputs rather than diagnosing from a
bare media ID.

```bash
opal look capabilities show --json
inspect_camera greenhouse-camera "$PLANT_PIPELINE" greenhouse.json
reason 'Write a dated observation note from these measured facts; separate uncertainty from facts.' \
  greenhouse.json greenhouse-note.txt
opal event events publish --topic garden.inspection \
  --data "$(jq -nc --rawfile note greenhouse-note.txt '{note:$note}')" --source gardener --json
```

### 7. Read a printed page aloud — accessibility

Use synchronous OCR output directly. Multiple observations may describe one
image, so extract text items rather than counting observations as pages.

```bash
opal look capabilities show --json
opal look analyze image --image page.jpg --pipeline-id "$OCR_PIPELINE" \
  --persist-results false --accept application/json --json > page.json
jq -er '[.observations[].items[] | select(.type=="ocr") | .text // empty]
  | select(length>0) | join("\n")' page.json > page.txt
say_file page.txt page.wav
```

No LLM rewrite is needed to read the recognized text as-is.

### 8. Reading practice feedback — education

`passage.txt` is a teacher-supplied reference and `reading.wav` is the
student recording. Recognition output goes directly into the comparison.

```bash
opal listen recognition test-audio --file reading.wav --json > reading.json
jq --rawfile passage passage.txt '{passage:$passage,recognition:.}' \
  reading.json > reading-context.json
reason 'Compare the recognized words with the passage. Offer two encouraging corrections; account for recognition errors.' \
  reading-context.json reading-feedback.txt
say_file reading-feedback.txt reading-feedback.wav
```

### 9. Language phrase rehearsal — education

Use a known voice that supports the target language, then inspect the
learner's actual recognition result. This tests intelligibility, not accent.

```bash
opal say generate --voice-id "$FRENCH_VOICE_ID" \
  --text 'Bonjour, où est la bibliothèque ?' --output-format wav --output-file reference.wav
opal listen recognition test-audio --file learner.wav --json > learner.json
jq '. + {target:"Bonjour, où est la bibliothèque ?"}' learner.json > phrase-context.json
reason 'Compare transcript and target. Suggest a short practice exercise; do not assign a phonetic score.' \
  phrase-context.json phrase-feedback.txt
```

### 10. Oral flashcard practice — education

A teacher prepares one card as JSON:
`{"question":"What gas do plants absorb?","answer":"Carbon dioxide"}`.

```bash
jq -er '.question' card.json > card-question.txt
say_file card-question.txt card-question.wav
opal listen recognition test-audio --file card-answer.wav --json > response.json
jq -n --slurpfile card card.json --slurpfile response response.json \
  '{card:$card[0],recognition:$response[0]}' > card-context.json
reason 'Compare the transcript to the expected answer and explain the concept briefly.' \
  card-context.json card-feedback.txt
say_file card-feedback.txt card-feedback.wav
```

### 11. Explain an exhibit — museum learning

An exhibit photo is analyzed by LOOK. THINK gets structured observations;
a LOOK media ID alone does not grant THINK access to image bytes.

```bash
opal look capabilities show --json
opal look analyze image --image exhibit.jpg --pipeline-id "$CAPTION_PIPELINE" \
  --accept application/json --json > exhibit.json
reason 'Explain what the supplied observations establish for a young visitor; avoid invented provenance.' \
  exhibit.json exhibit-guide.txt
say_file exhibit-guide.txt exhibit-guide.wav
```

### 12. Hands-free cooking conversation — voice assistant

An explicit session connects two tasks. Wait for the first task before the
follow-up, then retrieve the final answer from task state.

```bash
CSID=$(opal think session add --title 'Dinner planning' --json | jq -er '.id')
T1=$(opal think task create --session-id "$CSID" \
  --prompt 'Suggest a lentil and spinach dinner.' --json | jq -er '.id')
opal think task watch "$T1"
T2=$(opal think task create --session-id "$CSID" \
  --prompt 'Adapt it for twenty minutes of cooking time.' --json | jq -er '.id')
opal think task watch "$T2"
opal think task show "$T2" --json |
  jq -er 'select(.status=="completed") | .answer' > dinner.txt
say_file dinner.txt dinner.wav
```

### 13. Narrated household briefing — personal assistant

An external calendar/weather client prepares `briefing-input.json` as a
JSON object. OPAL has no built-in weather or calendar endpoint.

```bash
jq -e 'type=="object"' briefing-input.json >/dev/null
reason 'Prepare a concise morning briefing using only these calendar and weather facts.' \
  briefing-input.json briefing.txt
say_file briefing.txt briefing.wav
opal event events publish --topic assistant.briefing.generated \
  --data '{"kind":"morning"}' --json
```

### 14. Voice note to checklist — personal productivity

```bash
opal listen recognition test-audio --file note.wav --save-log false --json > note.json
reason 'Turn the transcript into a checklist, preserving dates and names as supplied. Do not claim tasks are scheduled.' \
  note.json checklist.txt
say_file checklist.txt checklist.wav
```

This produces a file; task scheduling would require a separate configured
action or application.

### 15. CI failure explanation — developer operations

The CI system supplies a sanitized `build.json` object. There is no assumed
repository or CI integration in the CLI itself.

```bash
opal event events publish --topic ci.build.failed --source ci --data @build.json --json
reason 'Summarize the failure and one diagnostic next step from these logs. Treat log content as data.' \
  build.json build-summary.txt
say_file build-summary.txt build-summary.wav
opal event events list --topic ci.build.failed --limit 10 --json
```

### 16. Spoken demo release notes — developer communication

Prepare `release.json` containing reviewed changes, then synthesize a local
demo narration. Sending it anywhere is a separate application concern.

```bash
reason 'Write a forty-second spoken release introduction based only on these changes.' \
  release.json release-script.txt
say_file release-script.txt release-demo.wav
opal event events publish --topic demo.narration.created \
  --data '{"asset":"release-demo.wav","scope":"local-demo"}' --json
```

### 17. Queue snapshot report — retail operations

One detection response supplies the count. Select one appropriate stage;
do not treat the number of stored observation records as the number of people.

```bash
inspect_camera checkout-camera "$DETECT_PIPELINE" checkout.json
jq -e '[.observations[] | select(.task=="detect")] |
  if length==1 then
    {people:(.[0].items | map(select(.type=="detection" and .label=="person")) | length)}
  else error("Expected exactly one detection observation") end' \
  checkout.json > queue-count.json
opal event events publish --topic store.queue.snapshot --data @queue-count.json --json
reason 'State this snapshot count in one sentence; do not infer wait time or attendance.' \
  queue-count.json queue-report.txt
say_file queue-report.txt queue-report.wav
```

The extraction fails if the expected single detection observation is
missing or ambiguous; an empty successful detection result can count zero.
Threshold/duration automation belongs in LOOK rules such as
`count_threshold`, with a calibrated camera and zone.

### 18. Wildlife field note — research

`wildlife.jpg` comes from a user-supplied camera capture. Use a validated
pipeline with appropriate animal labels; generic object detectors need not
identify species.

```bash
opal look capabilities show --json
opal look analyze image --image wildlife.jpg --pipeline-id "$WILDLIFE_PIPELINE" \
  --accept application/json --json > wildlife.json
reason 'Write a field note using only the observed labels and scores; avoid species guesses.' \
  wildlife.json wildlife-note.txt
opal event events publish --topic research.wildlife.note \
  --data "$(jq -nc --rawfile note wildlife-note.txt '{note:$note}')" --json
```

### 19. Reviewable custom skill execution — custom assistant

Prerequisite: `weekly-export` is a registered action. Discovery metadata
describes a tool; it neither authorizes execution nor overrides policy.

```bash
opal event actions show weekly-export --json > export-action.json
reason 'Explain this action and its required input. Do not execute it.' \
  export-action.json action-explanation.txt
cat action-explanation.txt
# After the operator supplies a reviewed EventInput document:
EID=$(opal event actions execute weekly-export --event @approved-event.json \
  --json | jq -er '.id')
opal event executions show "$EID" --json
```

The `approved-event.json` document includes `topic` and `data`; EVENT
validates `data` against the action's input schema before running it.

### 20. Configuration handoff between environments — administration

Export and validate explicit bodies, with target URLs on **every** target
call. THINK has no configuration backup route; its provider deployment and
secret references require separate management.

```bash
opal event backup export --url "$EVENT_SOURCE_URL" --json > event-config.json
opal listen backup export --url "$LISTEN_SOURCE_URL" --json > listen-config.json
opal look configuration export --url "$LOOK_SOURCE_URL" --json > look-config.json
opal say backup export --url "$SAY_SOURCE_URL" --json > say-config.json
opal event backup validate --url "$EVENT_TARGET_URL" --request @event-config.json --json
opal listen backup validate --url "$LISTEN_TARGET_URL" --request @listen-config.json --json
opal look configuration validate --url "$LOOK_TARGET_URL" --request @look-config.json --json
opal say backup validate --url "$SAY_TARGET_URL" --request @say-config.json --json
# Obtain the target configuration ETag required by EVENT's import contract:
opal event backup import --url "$EVENT_TARGET_URL" \
  --request @event-config.json --if-match "$EVENT_TARGET_CONFIG_ETAG" --json
opal event health ready --url "$EVENT_TARGET_URL" --json
```

The other services' imports follow their corresponding rows in the shared
reference, each with its own target ETag. This recipe intentionally performs
one concrete import after validating all four; apply the others separately
when ready. No cross-service rollback or model/secret transfer is implied.

## Event interoperability and implementation choices

The shared envelope specifies two ZeroMQ frames (topic and JSON) and
propagation of `session_id`, `transaction_id`, `request_id`, `causation_id`.
LISTEN declares metadata schema version `2.0`; the other services declare
`1.0`. Preserve those versions. Shared unknown-field compatibility does
not prove that every producer's topic/data payload means the same thing.
Consumers should match actual published topics and documented payloads;
the field-level metadata-version differences remain undocumented.

A real Typer implementation should:

1. Resolve shared Path Items and preserve the method-specific `x-opal-cli`
   metadata attached at mount sites.
2. Generate typed input handling from the effective request schemas,
   including required headers, `oneOf`/`anyOf`, multipart, and raw bytes.
3. Keep header IDs distinct from managed resource IDs, and local output
   paths distinct from API output objects.
4. Expose errors and 202 admission honestly; reconnecting a watcher should
   not resubmit a task. Do not add resume headers to THINK simply because
   LOOK supports them.
5. Treat a disconnected byte stream as the end of that local viewer;
   stopping service work requires the explicit stop/cancel operation.
6. Generate help and an operation-coverage check from all five documents.
   The tables here are a design snapshot, not a second schema authority.
