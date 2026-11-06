# OPAL CLI Guide: A Typer-Powered Interface for the OPAL Suite

> **Architectural Specification & Command Blueprint**  
> *Target Artifact:* `docs/CLI.gemini_flash.md`  
> *Status:* Hypothetical CLI Design and Reference Guide  
> *Underlying Contracts:* OpenAPI 3.1 Suite (`opal_event.yaml`, `opal_listen.yaml`, `opal_look.yaml`, `opal_say.yaml`, `opal_think.yaml`, and `shared/opal_kernel.yaml`). All active service specifications evaluated at `version: 1.5.0`.

---

## 1. Executive Summary & Architecture

The **OPAL (Open Platform for Assistive Learning & Automation)** ecosystem provides a decoupled, resilient microservice foundation for ambient intelligence, multi-modal perception, intent understanding, auditory synthesis, and autonomous task reasoning.

This guide specifies an end-to-end command-line interface implemented using Python's [Typer](https://typer.tiangolo.com/) framework. The root application (`opal`) mounts each microservice as an independent sub-command application:

```text
                               ┌───────────────┐
                               │   opal CLI    │
                               │ (Typer Root)  │
                               └───────┬───────┘
          ┌──────────────┬─────────────┼─────────────┬──────────────┐
          ▼              ▼             ▼             ▼              ▼
    ┌───────────┐  ┌───────────┐ ┌───────────┐ ┌───────────┐  ┌───────────┐
    │   event   │  │  listen   │ │   look    │ │    say    │  │   think   │
    │ (Bus/Act) │  │(Voice/ASR)│ │ (Vision)  │ │   (TTS)   │  │   (LLM)   │
    └───────────┘  └───────────┘ └───────────┘ └───────────┘  └───────────┘
```

### 1.1 Normative Metadata vs. Hypothetical Mappings

In strict conformance with repository contracts:
1. **Normative CLI Definitions (`x-opal-cli`):**
   - **`opal look`**: Strictly governed by `x-opal-cli` metadata inside `openapi/opal_look.yaml`. Commands adhere to uniform nouns (`sources`, `pipelines`, `sessions`, `rules`, `zones`, `monitors`, `jobs`, `observations`, etc.) and canonical resource verbs (`add`, `remove`, `update`, `list`, `show`) alongside explicit operational verbs (`start`, `stop`, `stream`, `capture`, `probe`, `status`, `validate`, `cancel`, `reset`, `patch`). Implicit aliases (such as `create`, `delete`, `get`, `set`) are deliberately prohibited by the contract.
   - **`opal think`**: Strictly governed by `x-opal-cli` metadata inside `openapi/opal_think.yaml`. Defines explicit group commands (`task`, `session`, `model`, `settings`, `health`) and convenience compositions (`ask`, `chat`).
2. **Hypothetical CLI Mappings:**
   - **`opal event`**, **`opal listen`**, and **`opal say`** do not define full top-level `x-opal-cli` metadata in their OpenAPI contracts. Their command structures and parameter flags are mapped logically from REST paths, operation definitions, request schemas, and parameter specifications while adhering to Typer conventions.

### 1.2 Suite-Wide Conventions & Kernel Primitives

All five OPAL services mount canonical paths and schemas derived from `openapi/shared/opal_kernel.yaml`. The CLI exposes these suite-wide facilities uniformly:

#### 1. Distributed Tracing & Correlation Headers
Every sub-command accepts and propagates standard correlation headers:
- `--session-id <UUID>` (`X-Opal-Session-Id`): Identifies persistent user/client conversational contexts.
- `--transaction-id <UUID>` (`X-Opal-Transaction-Id`): Correlates cross-service distributed workflows.
- `--request-id <UUID>` (`X-Opal-Request-Id`): Unique per HTTP roundtrip.
- `--causation-id <UUID>` (`X-Opal-Causation-Id`): The upstream ID or event ID that triggered the operation.

#### 2. Concurrency Preconditions (`ETag` & `If-Match`)
All mutating operations (PUT, PATCH, DELETE) targeting settings, configuration, engines, voices, or pipelines require optimistic concurrency control:
- Pass `--if-match <ETag>` on state-altering commands.
- If omitted when required, the API responds with `428 Precondition Required`.
- If the remote representation has diverged, the API responds with `412 Precondition Failed`.

#### 3. Cursor-Based Pagination
List operations traversing unbounded event logs, observation stores, or job histories adhere to cursor pagination:
- `--limit <int>`: Bounded fetch size (subject to server-side caps).
- `--cursor <string>`: Opaque cursor returned in `next_cursor` metadata. Cursors are bound to initial filter criteria; changing filters invalidates the cursor.

#### 4. Shared Kernel Commands
Mounted identically on every sub-command (`opal <service> ...`):
```console
# Health and diagnostics
opal <service> health
opal <service> health live
opal <service> health ready

# Configuration management
opal <service> settings list
opal <service> settings show <setting_key>
opal <service> settings set <setting_key> <json_value> --if-match <etag>
opal <service> settings remove <setting_key> --if-match <etag>
opal <service> settings patch '{"key": "value"}' --if-match <etag>

# Configuration backup & migration (Event, Listen, Look, Say)
opal <service> backup export --output backup.json
opal <service> backup validate --input backup.json
opal <service> backup import --input backup.json --if-match <etag>
```

---

## 2. Independent Service Analysis & CLI References

---

### 2.1 OPAL Event (`opal event`)

#### Architecture & Role
OPAL Event serves as the deterministic publish/subscribe message broker and localized rule evaluation engine. It facilitates state distribution across the ecosystem using a 2-frame ZeroMQ transport (Topic frame + JSON Envelope body) and a companion HTTP REST ingress/egress gateway. 

#### Engine & Host Installation
The Event engine does not rely on third-party neural model engines or weight runtimes. It is deployed as a standalone daemon with an embedded event store (typically SQLite/PostgreSQL) and a ZeroMQ socket multiplexer. Configuration of network bind addresses, socket buffer sizes, and retention retention windows is managed via `opal event settings`.

#### Full CLI Command & Option Reference

| Command | Option Flags | Parameter / Schema Mapping | Description |
|---|---|---|---|
| `event publish` | `--topic <str>`<br>`--data <json>`<br>`--source <str>`<br>`--id <uuid>`<br>`--timestamp <iso>` | `EventInput` schema: `topic` (regex validated), `data` (JSON object), optional metadata envelope. | Ingresses an event into the bus. Triggers rule evaluation. |
| `event list` | `--topic <str>`<br>`--source <str>`<br>`--from <iso>`<br>`--to <iso>`<br>`--cursor <str>`<br>`--limit <int>` | Query parameters: `topic`, `source`, `from`, `to`, `cursor`, `limit`. | Retrieves chronologically sorted, paginated event history. |
| `event show` | `<event_id>` | Path parameter: `event_id`. | Fetches the raw stored event envelope by identifier. |
| `event delete` | `<event_id>` | Path parameter: `event_id`. | Permanently purges an individual event from storage. |
| `event clear` | `--confirm` | Operation: `DELETE /api/v1/events/`. | Truncates the stored event buffer. Destructive. |
| `event topics` | `--cursor <str>`<br>`--limit <int>` | Operation: `GET /api/v1/topics/`. | Enumerates active and registered topic namespaces. |
| `event rules list` | `--enabled/--disabled` | Operation: `GET /api/v1/rules/`. | Lists automation dispatch rules. |
| `event rules add` | `--id <str>`<br>`--topic <str>`<br>`--conditions <json>`<br>`--actions <json_array>`<br>`--enabled/--disabled` | Request body: `Rule` schema. Operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `exists`, `contains`. | Compiles an event evaluation rule. Conditions are ANDed. |
| `event rules show` | `<rule_id>` | Path parameter: `rule_id`. | Inspects rule condition trees and action bindings. |
| `event rules update`| `<rule_id>`<br>`--patch <json>`<br>`--if-match <etag>` | `PATCH /api/v1/rules/{rule_id}` with `If-Match`. | Modifies rule triggers or toggles operational state. |
| `event rules delete`| `<rule_id>`<br>`--if-match <etag>` | `DELETE /api/v1/rules/{rule_id}` with `If-Match`. | Removes an automated evaluation rule. |
| `event rules test`  | `<rule_id>`<br>`--event <json>` | `POST /api/v1/rules/{rule_id}/test`. | Validates condition matching dry-run without executing actions. |
| `event actions list`| `--cursor <str>`<br>`--limit <int>` | Operation: `GET /api/v1/actions/`. | Displays catalog of registered action executors. |
| `event actions add` | `--id <str>`<br>`--type [shell\|http\|python]`<br>`--config <json>`<br>`--description <str>` | `Action` schema discriminator: `shell` (exec/args/timeout), `http` (url/method/headers), `python` (module/fn). | Registers a persistent side-effect execution target. |
| `event actions show`| `<action_id>` | Path parameter: `action_id`. | Displays execution schemas and capability metadata. |
| `event actions delete`| `<action_id>`<br>`--if-match <etag>`| `DELETE /api/v1/actions/{action_id}`. | Unregisters an action (fails if bound to active rules). |
| `event actions execute`| `<action_id>`<br>`--payload <json>` | `POST /api/v1/actions/{action_id}/execute`. | Manually dispatches an action payload synchronously. |
| `event executions list`| `--status [pending\|running\|succeeded\|failed]`<br>`--rule-id <str>`<br>`--action-id <str>`<br>`--event-id <uuid>` | Query parameters on `/api/v1/executions/`. | Reviews audit log of executed actions and outputs. |
| `event executions show`| `<execution_id>` | Path parameter: `execution_id`. | Inspects stdout, stderr, HTTP status, and duration of run. |
| `event stats` | *None* | Operation: `GET /api/v1/stats/`. | Metrics on event throughput, queue drops, and rule hits. |

#### What OPAL Event Can Do Alone
OPAL Event functions independently as an enterprise-grade automation webhook coordinator, telemetry router, and script execution scheduler. It can accept sensor readings from IoT devices, match patterns across multi-variable telemetry streams, trigger system commands or external webhooks, and log all audit events.

#### Standalone Execution Walkthrough: Automated Temperature Sentry
Below is a complete command sequence to configure a standalone thermal alerting pipeline with diagnostic rule verification:

```console
# 1. Register a shell-based notification action for the operations team
opal event actions add \
  --id "notify-pager" \
  --type "shell" \
  --config '{"executable": "/usr/local/bin/send_pager_alert.sh", "timeout_seconds": 10}' \
  --description "Dispatches urgent SMS via on-call gateway"

# 2. Register an HTTP webhook action for telemetry storage
opal event actions add \
  --id "ingest-telemetry-db" \
  --type "http" \
  --config '{"url": "https://metrics.internal.net/v1/thermal", "method": "POST", "headers": {"Content-Type": "application/json"}}' \
  --description "Appends readings to external metrics database"

# 3. Create a rule monitoring server rack telemetry: triggers when temp >= 45.0 C
opal event rules add \
  --id "rack-thermal-overheat" \
  --topic "telemetry.rack.*" \
  --conditions '[{"field": "data.temperature_c", "operator": "gte", "value": 45.0}]' \
  --actions '["notify-pager", "ingest-telemetry-db"]' \
  --enabled

# 4. Dry-run test the rule using a synthetic payload to verify condition logic
opal event rules test "rack-thermal-overheat" \
  --event '{"topic": "telemetry.rack.alpha", "data": {"temperature_c": 47.8, "humidity": 38.2}}'

# 5. Ingest real-world telemetry events
opal event publish \
  --topic "telemetry.rack.alpha" \
  --data '{"temperature_c": 48.2, "humidity": 39.0}' \
  --source "sensor-rack-a12"

# 6. Audit action execution history and inspect operational outcomes
opal event executions list --rule-id "rack-thermal-overheat" --limit 5
opal event executions show "exec-8a192bf0-51a8"
```

---

### 2.2 OPAL Listen (`opal listen`)

#### Architecture & Role
OPAL Listen provides automatic speech recognition (ASR), wakeword spotting, and natural language intent classification. It extracts typed semantic slots from acoustic streams and manages speech recognition training logs, failed utterance recovery, and automated regression suites.

#### Engine & Host Installation
The Listen service coordinates underlying ASR runtimes (e.g., Whisper, Vosk, or Sherpa-ONNX) and Wakeword spotters (e.g., OpenWakeWord or Porcupine).
1. **Host-Level Engine Setup:**
   ```bash
   # System audio and neural engine runtime installation on the Listen host
   sudo apt-get update && sudo apt-get install -y portaudio19-dev libasound2-dev
   pip install sherpa-onnx openwakeword
   # Download models into the configured host directory:
   mkdir -p /opt/opal/listen/models/wakewords
   wget -O /opt/opal/listen/models/wakewords/hey_opal.onnx https://models.opal.ai/wakewords/hey_opal.onnx
   ```
2. **API Verification & Hardware Discovery:**
   The API does not manage physical binary downloads; rather, it queries host drivers and detects available audio devices:
   ```console
   opal listen health audio-devices
   opal listen settings patch '{"wakeword_engine": "openwakeword", "model_path": "/opt/opal/listen/models/wakewords"}'
   ```

#### Full CLI Command & Option Reference

| Command | Option Flags | Parameter / Schema Mapping | Description |
|---|---|---|---|
| `listen wakewords list` | *None* | `GET /api/v1/wakewords/`. | Lists registered wake phrases and thresholds. |
| `listen wakewords add` | `--name <str>`<br>`--threshold <float>`<br>`--enabled/--disabled` | `WakewordCreate` schema. | Configures an active acoustic wake trigger. |
| `listen intents list` | *None* | `GET /api/v1/intents/`. | Enumerates configured domain intents. |
| `listen intents add` | `--name <str>`<br>`--description <str>`<br>`--phrases <json_array>`<br>`--threshold <float>` | `IntentCreate` schema: defines canonical intent and phrase templates. | Registers semantic intent with template phrases. |
| `listen intents phrases add`| `<intent_id>`<br>`--phrase <str>` | `POST /api/v1/intents/{intent_id}/phrases`. | Appends training utterances to an intent. |
| `listen slots list` | *None* | `GET /api/v1/slots/`. | Lists recognized extraction entity types. |
| `listen slots add` | `--name <str>`<br>`--slot-type <str>`<br>`--description <str>` | `SlotCreate`: matches `{slot_name}` in intent phrases. | Defines a slot identifier and validation category. |
| `listen slots values add`| `<slot_id>`<br>`--value <str>` | `POST /api/v1/slots/{slot_id}/values`. | Adds an allowable canonical slot value. |
| `listen slots aliases add`| `<slot_id>`<br>`<value_id>`<br>`--alias <str>` | `POST /api/v1/slots/{slot_id}/values/{value_id}/aliases`. | Adds phonetic/spelling variation mapping to a value. |
| `listen profiles list` | *None* | `GET /api/v1/profiles/`. | Enumerates speech pipeline configuration profiles. |
| `listen profiles activate`| `<profile_id>` | `POST /api/v1/profiles/{profile_id}/activate`. | Atomically binds the active audio profile. |
| `listen recognition start`| *None* | `POST /api/v1/recognition/start`. | Activates the live acoustic processing daemon. |
| `listen recognition stop` | *None* | `POST /api/v1/recognition/stop`. | Deactivates the microphone and feature extractor. |
| `listen recognition status`| *None* | `GET /api/v1/recognition/status`. | Inspects device state, buffer health, and VAD status. |
| `listen recognition stream`| `--debug` | `GET /api/v1/recognition/stream` (SSE/Chunked). | Streams live recognized tokens, wakewords, and intent events. |
| `listen recognition test-text`| `--text <str>`<br>`--save-log/--no-save-log` | `POST /api/v1/recognition/test_text`. | Evaluates NLU intent/slot parsing on text input. |
| `listen recognition test-audio`| `--file <path>`<br>`--require-wakeword`<br>`--save-log` | `POST /api/v1/recognition/test_audio` (Multipart). | Diagnostic audio upload; tests acoustic & NLU pipeline. |
| `listen logs list` | `--intent <str>`<br>`--matched/--unmatched`<br>`--limit <int>` | Query params on `/api/v1/logs/`. | Inspects historical speech recognition attempts. |
| `listen failed list` | `--reviewed/--unreviewed`<br>`--limit <int>` | Operation: `GET /api/v1/failed_utterances/`. | Retrieves unrecognized speech events for triage. |
| `listen failed promote`| `<fu_id>`<br>`--target-intent <str>`<br>`--create-regression` | `POST /api/v1/failed_utterances/{fu_id}/promote`. | Promotes a failed audio utterance into an intent sample. |
| `listen regression list` | *None* | `GET /api/v1/regression/`. | Lists unit-test regression utterances. |
| `listen regression add` | `--name <str>`<br>`--phrase <str>`<br>`--expected-intent <str>`<br>`--expected-slots <json>` | `RegressionTestCreate` schema. | Adds deterministic assertion test for speech model. |
| `listen regression run` | `--enabled-only` | `POST /api/v1/regression/run`. | Executes the full regression suite; returns pass/fail metrics. |
| `listen performance summary`| `--limit <int>` | `GET /api/v1/performance/summary`. | Metrics on latency (VAD to text, intent inference). |

#### What OPAL Listen Can Do Alone
OPAL Listen can function independently as an acoustic gateway, intelligent dictation classifier, or offline voice command parser. It handles end-to-end NLU evaluation from raw WAV files, runs automated regression verification across grammar iterations, and audits microphone hardware latency.

#### Standalone Execution Walkthrough: Building & Verifying a Kitchen Lighting Intent
```console
# 1. Enumerate available audio hardware
opal listen health audio-devices

# 2. Define a typed slot for rooms and populate canonical values and aliases
opal listen slots add --name "room" --slot-type "home_location" --description "Target room entity"
# Assuming returned slot ID is "slot-room-uuid"
opal listen slots values add "slot-room-uuid" --value "kitchen"
opal listen slots values add "slot-room-uuid" --value "basement"
opal listen slots aliases add "slot-room-uuid" "val-kitchen-uuid" --alias "scullery"

# 3. Create the lighting control intent with phrase templates
opal listen intents add \
  --name "device.light.set" \
  --description "Toggles or adjusts lighting state in a designated zone" \
  --threshold 0.75 \
  --phrases '["turn on the {room} lights", "switch off lights in the {room}", "illuminate the {room}"]'

# 4. Perform deterministic dry-run text recognition test (diagnostic mode - does NOT emit bus events)
opal listen recognition test-text \
  --text "turn on the scullery lights" \
  --save-log

# 5. Lock in quality by adding a regression test and running validation
opal listen regression add \
  --name "test-scullery-alias-recognition" \
  --phrase "turn on the scullery lights" \
  --expected-intent "device.light.set" \
  --expected-slots '{"room": "kitchen"}'

opal listen regression run --enabled-only

# 6. Stream live recognition from physical microphone
opal listen recognition start
opal listen recognition stream --debug
```

---

### 2.3 OPAL Look (`opal look`)

#### Architecture & Role
OPAL Look is the computer vision, spatial reasoning, and real-time video analytics engine. It manages cameras (RTSP, USB, HTTP-MJPEG, static files), defines directed acyclic graph (DAG) pipelines, tracks visual zones and tripwires, runs persistent background monitors, and writes immutable observation logs.

#### Engine & Host Installation
The contract strictly forbids dynamic arbitrary model downloads or training endpoints (`/models/train` or `/models/download` do not exist).
1. **Host-Level Engine Setup:**
   Install hardware-accelerated inferencing engines (e.g., ONNXRuntime-GPU, TensorRT, or OpenVINO) and place model weights in the host repository:
   ```bash
   sudo apt-get install -y ffmpeg libgstreamer1.0-0
   # Install vendor runtime:
   pip install onnxruntime-gpu
   mkdir -p /opt/opal/look/models
   wget -O /opt/opal/look/models/yolov8n.onnx https://models.opal.ai/vision/yolov8n.onnx
   ```
2. **API Model Registration & Discovery:**
   The service discovers capabilities and accepts registrations of pre-existing host assets via the normative CLI:
   ```console
   opal look capabilities show
   opal look engines list
   opal look models add \
     --id "yolo-v8n-coco" \
     --engine-id "onnx-cuda" \
     --resource-ref "/opt/opal/look/models/yolov8n.onnx" \
     --tasks '["detect", "track"]' \
     --options '{"confidence_threshold": 0.45, "nms_iou": 0.5}'
   ```

#### Full CLI Command & Option Reference (Normative `x-opal-cli`)

| Command Group | Verbs / Commands | Options & Arguments | OpenAPI Schema / Operation Mapping |
|---|---|---|---|
| `capabilities` | `show` | *None* | `GET /api/v1/capabilities/`. Discovers supported tasks (detect, segment, ocr, pose, anomaly, caption, depth). |
| `engines` | `list`, `show`, `update` | `<engine_id>`, `--options <json>`, `--if-match <etag>` | `GET/PATCH /api/v1/engines/{id}`. Inspects hardware acceleration engines. |
| `models` | `list`, `show`, `add`, `update`, `remove` | `--id <str>`, `--engine-id <str>`, `--resource-ref <path>`, `--tasks <json>`, `--if-match <etag>` | `ModelCreate`/`ModelPatch` schemas. Governs host model associations. |
| `sources` | `list`, `show`, `add`, `update`, `remove`, `status`, `probe` | `--id <str>`, `--kind [usb\|rtsp\|http_mjpeg\|file\|media\|adapter]`, `--locator <uri>`, `--secret-ref <str>`, `--options <json>` | `SourceCreate` on `/api/v1/sources/`. Manages video/imaging streams. `probe` inspects codec and FPS. |
| `sources` (ops) | `frame`, `capture`, `stream` | `<source_id>`, `--output <path>`, `--pipeline-id <str>`, `--annotations`, `--show-labels`, `--show-boxes`, `--quality <int>` | `frame`: fresh single JPEG. `capture`: snapshot retention. `stream`: live MJPEG stream. |
| `pipelines` | `list`, `show`, `add`, `update`, `remove`, `validate` | `--id <str>`, `--stages <json_array>`, `--file <path>`, `--if-match <etag>` | `PipelineCreate` on `/api/v1/pipelines/`. Validates and deploys ordered processing DAGs. |
| `profiles` | `list`, `show`, `add`, `update`, `remove`, `activate` | `--id <str>`, `--pipeline-id <str>`, `--options <json>`, `--if-match <etag>` | Reusable vision profiles. `activate` sets system default. |
| `zones` | `list`, `show`, `add`, `update`, `remove` | `--id <str>`, `--source-id <str>`, `--kind [line\|polygon]`, `--points <json_array>` | `ZoneCreate` on `/api/v1/zones/`. Defines spatial geometries for boundary crossing. |
| `rules` | `list`, `show`, `add`, `update`, `remove` | `--id <str>`, `--source-id <str>`, `--kind [object_appears\|object_disappears\|enters_zone\|exits_zone\|line_crosses\|count_threshold\|dwell_time]`, `--zone-id <str>`, `--class-filters <json>`, `--duration-ms <int>`, `--cooldown-seconds <int>`, `--capture-on-match` | `RuleCreate` on `/api/v1/rules/`. Spatial and temporal rule triggers. |
| `monitors` | `list`, `show`, `add`, `update`, `remove` | `--id <str>`, `--source-id <str>`, `--pipeline-id <str>`, `--restart-policy [always\|on_failure\|never]`, `--enabled/--disabled` | `MonitorCreate` on `/api/v1/monitors/`. Manages persistent background inference processes. |
| `sessions` | `start`, `list`, `show`, `stop`, `observations`, `stream`, `preview` | `--source-id <str>`, `--pipeline-id <str>`, `--auto-start`, `--last-event-id <str>`, `--limit <int>` | Ephemeral real-time inference sessions. `stream` provides SSE observation events. |
| `jobs` | `submit`, `list`, `show`, `cancel` | `--kind [analyze_video\|export_annotated_video\|extract_clip]`, `--source-id <str>`, `--media-id <str>`, `--pipeline-id <str>` | `JobCreate` on `/api/v1/jobs/`. Asynchronous batch processing of finite video media. |
| `observations` | `list`, `show` | `--source-id <str>`, `--session-id <str>`, `--job-id <str>`, `--task <str>`, `--label <str>`, `--after <iso>`, `--before <iso>`, `--cursor <str>`, `--limit <int>` | Immutable structured perception database. High-throughput query API. |
| `media` | `upload`, `list`, `show`, `remove` | `--file <path>`, `--ttl-seconds <int>` | Multipart file upload for finite analysis. Strictly size/MIME validated. |
| `captures` | `list`, `show`, `download`, `remove` | `<capture_id>`, `--output <path>` | Manages high-resolution disk captures triggered by rules or manual requests. |
| `recordings` | `list`, `show`, `start`, `stop` | `--source-id <str>`, `<recording_id>` | Dedicated video archiving lifecycle independent of visualization streams. |
| `artifacts` | `list`, `show`, `download`, `remove` | `<artifact_id>`, `--output <path>` | Manages derived video clips, cropped objects, and heatmaps. |

#### What OPAL Look Can Do Alone
OPAL Look is an autonomous computer vision workstation. Without any external assistance, it can ingest continuous RTSP/USB camera feeds, detect and track objects, trigger captures based on polygonal boundary intersections or dwell thresholds, record historical video clips, run batch analytics on pre-recorded MP4s, and serve live annotated MJPEG streams.

#### Standalone Execution Walkthrough: Perimeter Sentry & Tripwire Security
```console
# 1. Discover active vision acceleration and model capabilities
opal look capabilities show

# 2. Register a high-definition perimeter RTSP camera
opal look sources add \
  --id "cam-north-fence" \
  --kind "rtsp" \
  --name "North Fence Line" \
  --locator "rtsp://192.168.10.45:554/live/ch0" \
  --options '{"transport": "tcp", "buffer_size_mb": 4}'

# 3. Probe the camera to confirm network reachability and codec compatibility
opal look sources probe "cam-north-fence"
opal look sources status "cam-north-fence"

# 4. Define an intrusion detection pipeline DAG and validate its configuration
cat << 'EOF' > /tmp/fence_pipeline.json
{
  "stages": [
    {"name": "decoder", "stage_type": "input", "source_fps": 15},
    {"name": "detector", "stage_type": "inference", "model_id": "yolo-v8n-coco", "tasks": ["detect", "track"]},
    {"name": "filter", "stage_type": "filter", "classes": ["person", "vehicle"], "min_confidence": 0.50}
  ]
}
EOF
opal look pipelines validate --file /tmp/fence_pipeline.json
opal look pipelines add --id "pipeline-perimeter" --file /tmp/fence_pipeline.json

# 5. Define a geometric tripwire line along the fence boundary
opal look zones add \
  --id "zone-fence-tripwire" \
  --source-id "cam-north-fence" \
  --kind "line" \
  --name "Property Fence Boundary" \
  --points '[{"x": 0.05, "y": 0.72}, {"x": 0.95, "y": 0.78}]'

# 6. Bind an intrusion rule: trigger capture when a person crosses the line
opal look rules add \
  --id "rule-fence-crossing" \
  --source-id "cam-north-fence" \
  --kind "line_crosses" \
  --zone-id "zone-fence-tripwire" \
  --class-filters '["person"]' \
  --cooldown-seconds 30 \
  --capture-on-match

# 7. Spawn a permanent background monitor
opal look monitors add \
  --id "mon-north-fence" \
  --source-id "cam-north-fence" \
  --pipeline-id "pipeline-perimeter" \
  --restart-policy "always" \
  --enabled

# 8. Query retained detections and download triggered capture frames
opal look observations list --source-id "cam-north-fence" --label "person" --limit 10
opal look captures list --limit 5
opal look captures download "cap-91f82e1c" --output /tmp/intruder_evidence.jpg
```

---

### 2.4 OPAL Say (`opal say`)

#### Architecture & Role
OPAL Say provides auditory synthesis (Text-to-Speech). It discovers installed synthesis engines, manages localized voices, configures acoustic profiles (controlling pitch, speed, and volume), and produces both completed audio files (WAV, MP3, OGG, FLAC) and ultra-low-latency raw PCM streams.

#### Engine & Host Installation
The Say contract explicitly dictates: *TTS engines are installed and discovered by the implementation; they are not created or deleted via this REST API.*
1. **Host-Level Engine Setup:**
   Install backend TTS synthesis engines (such as Piper, Coqui TTS, or eSpeak-NG):
   ```bash
   sudo apt-get install -y espeak-ng
   pip install piper-tts
   mkdir -p /opt/opal/say/voices
   wget -O /opt/opal/say/voices/en_US-lessac-medium.onnx https://models.opal.ai/tts/en_US-lessac-medium.onnx
   wget -O /opt/opal/say/voices/en_US-lessac-medium.onnx.json https://models.opal.ai/tts/en_US-lessac-medium.onnx.json
   ```
2. **API Discovery & Verification:**
   The CLI identifies discovered engines and verifies their capability:
   ```console
   opal say engines list
   opal say engines validate "piper-neural"
   ```

#### Full CLI Command & Option Reference

| Command | Option Flags | Parameter / Schema Mapping | Description |
|---|---|---|---|
| `say engines list` | *None* | `GET /api/v1/engines/`. | Lists available engines (`ready`, `unavailable`, `error`, `disabled`). |
| `say engines show` | `<engine_id>` | Path parameter: `engine_id`. | Detailed inspect: version, latency specs, supported tasks. |
| `say engines update`| `<engine_id>`<br>`--enabled/--disabled`<br>`--options <json>`<br>`--if-match <etag>` | `PATCH /api/v1/engines/{engine_id}` with `If-Match`. | Toggles operational state or tunes buffer parameters. |
| `say engines validate`| `<engine_id>` | `POST /api/v1/engines/{engine_id}/validate`. | Probes underlying binary availability and device execution. |
| `say voices list` | `--engine-id <str>`<br>`--enabled/--disabled` | Query params on `/api/v1/voices/`. | Displays registered vocal personalities. |
| `say voices add` | `--id <str>`<br>`--name <str>`<br>`--engine-id <str>`<br>`--engine-voice-ref <str>`<br>`--language <str>`<br>`--gender [female\|male\|neutral]`<br>`--sample-rate <int>` | `VoiceCreate` schema on `POST /api/v1/voices/`. | Binds an engine-specific voice asset to an OPAL voice entity. |
| `say voices show` | `<voice_id>` | Path parameter: `voice_id`. | Fetches acoustic metadata for a specific voice. |
| `say voices validate`| `<voice_id>` | `POST /api/v1/voices/{voice_id}/validate`. | Checks voice file integrity on the host system. |
| `say voices test` | `<voice_id>`<br>`--text <str>`<br>`--output <path>` | `POST /api/v1/voices/{voice_id}/test`. | Synthesizes an ephemeral verification clip. |
| `say profiles list` | *None* | `GET /api/v1/profiles/`. | Enumerates configured acoustic delivery profiles. |
| `say profiles add` | `--name <str>`<br>`--voice-id <str>`<br>`--speed <float>`<br>`--volume <float>`<br>`--output-format [wav\|mp3\|ogg\|flac]`<br>`--sample-rate <int>` | `OpalProfileCreate` on `/api/v1/profiles/`. | Creates reusable profile (e.g. `urgent-alert`, `calm-narrator`). |
| `say profiles activate`| `<profile_id>` | `POST /api/v1/profiles/{profile_id}/activate`. | Sets the active default system profile. |
| `say speak` | `--text <str>`<br>`--profile-id <str>`<br>`--voice-id <str>`<br>`--speed <float>`<br>`--output <path>` | `GenerationRequest` on `POST /api/v1/generate`. | Synthesizes discrete completed audio file. |
| `say stream` | `--text <str>`<br>`--profile-id <str>`<br>`--voice-id <str>`<br>`--output-raw <path>` | `POST /api/v1/generate/stream`. | **Important:** Returns raw, headerless signed 16-bit little-endian mono PCM. |

#### What OPAL Say Can Do Alone
OPAL Say serves as a dedicated, high-performance speech synthesis microservice. Applications can route text notifications, generate static audiobook files, validate speaker profiles across languages, and stream low-latency raw PCM bytes straight to local audio hardware via pipes.

#### Standalone Execution Walkthrough: Voice Registration & Streaming Audio Pipeline
```console
# 1. Enumerate and validate installed host TTS engines
opal say engines list
opal say engines validate "piper-neural"

# 2. Register a high-quality neural voice model located on the host
opal say voices add \
  --id "voice-en-lessac" \
  --name "Lessac Medium Female" \
  --engine-id "piper-neural" \
  --engine-voice-ref "/opt/opal/say/voices/en_US-lessac-medium.onnx" \
  --language "en-US" \
  --gender "female" \
  --sample-rate 22050

# 3. Validate voice integrity and generate a diagnostic sample
opal say voices validate "voice-en-lessac"
opal say voices test "voice-en-lessac" \
  --text "Acoustic synthesis engine verification complete." \
  --output /tmp/test_voice.wav

# 4. Construct an emergency alert profile (accelerated tempo, elevated volume)
opal say profiles add \
  --name "profile-emergency" \
  --voice-id "voice-en-lessac" \
  --speed 1.25 \
  --volume 1.0 \
  --output-format "wav" \
  --sample-rate 22050

# 5. Synthesize a batch announcement file
opal say speak \
  --text "Attention: Scheduled facility maintenance commencing in ten minutes." \
  --profile-id "profile-emergency" \
  --output /tmp/announcement.wav

# 6. Stream live low-latency PCM directly into the Linux sound subsystem (aplay)
# Note: Stream endpoint outputs raw S16_LE PCM (22050 Hz, 1 channel).
opal say stream \
  --text "Streaming auditory packet transmission established." \
  --profile-id "profile-emergency" | \
  aplay -f S16_LE -r 22050 -c 1
```

---

### 2.5 OPAL Think (`opal think`)

#### Architecture & Role
OPAL Think manages complex reasoning, conversational state, and asynchronous tool-augmented tasks via Large Language Models (LLMs). It handles long-running cognitive requests via a durable Task queue with HTTP 202 admission, supports multi-turn Session trees, and discovers available models.

#### Engine & Host Installation
The contract explicitly specifies: *Models are discovered from configured provider adapters, not installed or deleted via this REST API.*
1. **Host-Level Engine & Adapter Setup:**
   Run local LLM servers (e.g. llama.cpp, vLLM, or Ollama) or configure remote API provider credentials (e.g. OpenAI, Anthropic):
   ```bash
   # Example: Host running Ollama daemon
   ollama pull mistral:instruct
   ```
2. **Provider Discovery & Configuration:**
   Configure connection credentials via kernel settings and verify availability via `model list`:
   ```console
   opal think settings set "providers.ollama.endpoint" '"http://127.0.0.1:11434"'
   opal think model list
   ```

#### Full CLI Command & Option Reference (Normative `x-opal-cli`)

| Command Group | Command / Alias | Options & Arguments | OpenAPI Schema / Operation Mapping |
|---|---|---|---|
| `task` | `create` | `--prompt <str>`<br>`--session-id <uuid>`<br>`--model-id <str>`<br>`--context <json>`<br>`--max-steps <int>`<br>`--timeout <int>`<br>`--metadata <json>`<br>`--idempotency-key <str>` | `POST /api/v1/tasks/`. Submits durable LLM task. Returns HTTP 202 Accepted with `Task` envelope & `Location` header. |
| `task` | `list` | `--session-id <uuid>`<br>`--status [pending\|running\|completed\|failed\|cancelled]`<br>`--cursor <str>`<br>`--limit <int>` | `GET /api/v1/tasks/`. Bounded query of asynchronous execution history. |
| `task` | `show` | `<task_id>` | `GET /api/v1/tasks/{task_id}`. Retrieves current state, steps completed, error, and result payload. |
| `task` | `watch` | `<task_id>` | `GET /api/v1/tasks/{task_id}/stream`. Streams SSE real-time reasoning tokens, tool calls, and final answer. |
| `task` | `cancel` | `<task_id>` | `POST /api/v1/tasks/{task_id}/cancel`. Sends cancellation signal to abort running generation. |
| `session`| `add` | `--title <str>`<br>`--metadata <json>` | `SessionCreate` on `POST /api/v1/sessions/`. Allocates a multi-turn conversation thread. |
| `session`| `list` | `--limit <int>`<br>`--cursor <str>` | `GET /api/v1/sessions/`. Lists active conversation threads. |
| `session`| `show` | `<session_id>` | `GET /api/v1/sessions/{session_id}`. Displays turn history and session context. |
| `session`| `remove` | `<session_id>` | `DELETE /api/v1/sessions/{session_id}`. Purges conversational session memory. |
| `model` | `list` | *None* | `GET /api/v1/models/`. Catalogs available models, context windows, and availability flags. |
| `model` | `show` | `<model_id>` | `GET /api/v1/models/{model_id}`. Detailed parameter limits, temperature bounds, and provider tag. |
| *Composite* | `ask` | `<prompt>`<br>`[--model-id]`<br>`[--context]` | Compound CLI convenience: Submits `task create`, blocks on `task watch`, outputs final text. |
| *Composite* | `chat`| `[--session-id]`<br>`[--model-id]` | Interactive terminal REPL loop: maintains a persistent session across prompt turns. |

#### What OPAL Think Can Do Alone
OPAL Think can independently operate as an autonomous coding assistant, structured data extractor, long-document summarizer, and multi-turn planning agent. It manages its own durable execution queue, handles network disconnection gracefully via resumable task watching, and serializes conversational state without requiring other OPAL components.

#### Standalone Execution Walkthrough: Long-Running Document Synthesis
```console
# 1. Enumerate configured models and verify backend availability
opal think model list

# 2. Allocate a persistent session for an engineering review
opal think session add --title "OPAL v1.5.0 Architecture Audit"
# Captured session ID: "sess-018f-a940-b8c1"

# 3. Submit a long-running, multi-step synthesis task (returns immediately with 202 Accepted)
opal think task create \
  --session-id "sess-018f-a940-b8c1" \
  --model-id "mistral-large" \
  --prompt "Analyze this OpenAPI specification extract and identify state synchronization bottlenecks." \
  --context '{"spec_fragment": "paths: /api/v1/sessions/{id}/stream: ..."}' \
  --timeout 120 \
  --idempotency-key "task-idemp-902184"

# 4. Stream real-time reasoning tokens to the console
opal think task watch "task-df81a029-7c11"

# 5. Fetch completed task artifact and inspect execution metadata
opal think task show "task-df81a029-7c11"

# 6. Submit a follow-up contextual query within the same serialized session
opal think task create \
  --session-id "sess-018f-a940-b8c1" \
  --prompt "Generate a mitigating circuit breaker schema for the identified bottleneck."

opal think task watch "task-ef902b11-8a02"
```

---

## 3. Ecosystem Workflows & Multi-Service Composition

The power of the OPAL suite emerges from composition. Because no monolithic cross-service API exists, the CLI coordinates client-side orchestration patterns, passing typed identifiers, linking event topics, and maintaining correlation context (`X-Opal-Transaction-Id`).

### Foundational Compositions

#### A. "Ask OPAL a Question" (Listen $\to$ Think $\to$ Say)
A user speaks into the microphone; OPAL recognizes the speech, derives an intelligent response, and synthesizes speech playback:

```console
# Step 1: Capture acoustic intent via Listen streaming endpoint (or test file)
RAW_QUERY=$(opal listen recognition test-audio --file /tmp/user_voice_query.wav | jq -r '.transcript')

# Step 2: Forward recognized transcript to Think for synthesis
TASK_ID=$(opal think task create --prompt "$RAW_QUERY" | jq -r '.id')
ANSWER_TEXT=$(opal think task watch "$TASK_ID" | tail -n 1)

# Step 3: Stream synthesized verbal answer directly to speaker output
opal say stream --text "$ANSWER_TEXT" | aplay -f S16_LE -r 22050 -c 1
```

#### B. "Drop In on Camera-1" (Look Live Observation & Streaming)
Allows an operator to inspect live video, examine detections, and launch an ephemeral viewer:

```console
# Step 1: Probe physical source readiness
opal look sources status "camera-1"

# Step 2: Grab an instantaneous high-res still frame
opal look sources frame "camera-1" --output /tmp/camera_1_live.jpg

# Step 3: Launch an ephemeral annotated MJPEG video stream viewer
# Uses ffplay to render the HTTP MJPEG stream locally
opal look sources stream "camera-1" \
  --annotations \
  --show-labels \
  --show-boxes \
  --show-confidence | \
  ffplay -i - -autoexit
```

---

### Twenty Compelling Cross-Domain Use Cases

---

#### Domain 1: Home Automation & Ambient Assisted Living

##### Use Case 1: Automated Porch Package Delivery Guardian (Look $\to$ Event $\to$ Say)
*Scenario:* A courier approaches the front door and deposits a parcel. The camera detects the package, triggers an internal event, routes the event via the bus, and issues an audio alert inside the house.
```console
# 1. Look: Configure an object detection rule for parcels on the porch camera
opal look rules add \
  --id "rule-porch-package" \
  --source-id "cam-porch" \
  --kind "object_appears" \
  --class-filters '["package", "box"]' \
  --capture-on-match

# 2. Event: Register an action that triggers Say synthesis via local command
opal event actions add \
  --id "action-announce-package" \
  --type "shell" \
  --config '{"executable": "opal", "args": ["say", "speak", "--text", "A delivery package has been placed on the front porch.", "--profile-id", "chime-alert"]}'

# 3. Event: Bind rule to Look's emitted detection topic
opal event rules add \
  --id "rule-route-package-event" \
  --topic "opal.look.cam-porch.rule.rule-porch-package" \
  --actions '["action-announce-package"]' \
  --enabled

# 4. Verification: Test event flow
opal event rules test "rule-route-package-event" \
  --event '{"topic": "opal.look.cam-porch.rule.rule-porch-package", "data": {"label": "package", "confidence": 0.92}}'
```

##### Use Case 2: Intelligent Driveway Perimeter Warning (Look $\to$ Think $\to$ Say)
*Scenario:* An unknown vehicle enters the property driveway after dark. Look records the intrusion, Think formulates an escalating deterrent announcement, and Say speaks through an outdoor loudspeaker.
```console
# 1. Look: Create zone and entry rule
opal look zones add --id "zone-driveway" --source-id "cam-driveway" --kind "polygon" --points '[{"x":0.1,"y":0.4},{"x":0.9,"y":0.4},{"x":0.9,"y":0.9},{"x":0.1,"y":0.9}]'
opal look rules add --id "rule-driveway-vehicle" --source-id "cam-driveway" --kind "enters_zone" --zone-id "zone-driveway" --class-filters '["car", "truck"]' --capture-on-match

# 2. Look: Extract capture ID on violation
CAPTURE_ID=$(opal look captures list --limit 1 | jq -r '.items[0].id')
opal look captures download "$CAPTURE_ID" --output /tmp/driveway_car.jpg

# 3. Think: Assess context and generate warning message
WARNING_PROMPT="A vehicle crossed into the restricted driveway zone at $(date). Generate a brief, authoritative warning announcement informing the driver they are under surveillance."
TASK_ID=$(opal think task create --prompt "$WARNING_PROMPT" --context '{"zone": "driveway", "class": "vehicle"}' | jq -r '.id')
WARNING_TEXT=$(opal think task watch "$TASK_ID" | tail -n 1)

# 4. Say: Broadcast warning over outdoor audio horn
opal say speak --text "$WARNING_TEXT" --speed 1.1 --output /tmp/outdoor_warning.wav
aplay -D plughw:1,0 /tmp/outdoor_warning.wav
```

##### Use Case 3: Conversational Voice-Controlled Lighting (Listen $\to$ Event $\to$ Say)
*Scenario:* A resident says "Turn on the reading lamp in the parlor." Listen parses the intent and slots, Event dispatches an HTTP request to the smart lighting bridge, and Say confirms completion.
```console
# 1. Listen: Verify intent parsing
INTENT_RES=$(opal listen recognition test-text --text "Turn on the reading lamp in the parlor")
TARGET_ROOM=$(echo "$INTENT_RES" | jq -r '.slots.room')
TARGET_STATE=$(echo "$INTENT_RES" | jq -r '.slots.state // "on"')

# 2. Event: Execute registered smart home HTTP webhook
opal event actions execute "act-hue-light-toggle" \
  --payload "{\"room\": \"$TARGET_ROOM\", \"state\": \"$TARGET_STATE\"}"

# 3. Say: Vocalize confirmation
opal say speak --text "Affirmative, the $TARGET_ROOM lights are now $TARGET_STATE." --profile-id "voice-assistant"
```

##### Use Case 4: Elderly Ambient Fall & Immobility Guardian (Look $\to$ Event $\to$ Think $\to$ Say)
*Scenario:* A living room camera tracks a resident. If a dwell time exceeding 4 hours occurs during daytime hours outside bed, Event schedules a welfare check.
```console
# 1. Look: Configure dwell-time alert for living room floor zone
opal look rules add \
  --id "rule-immobility-alert" \
  --source-id "cam-living-room" \
  --kind "dwell_time" \
  --duration-ms 14400000 \
  --class-filters '["person"]'

# 2. Event: Route event to automated verbal check-in
opal event rules add \
  --id "rule-checkin-prompt" \
  --topic "opal.look.cam-living-room.rule.rule-immobility-alert" \
  --actions '["action-trigger-checkin-speech"]'

# 3. Say: Prompt the resident gently
opal say speak --text "Hello, checking in. Are you feeling alright? Please say yes or wave to the camera."

# 4. Listen: Monitor for affirmative response
CHECKIN_REPLY=$(opal listen recognition test-audio --file /tmp/resident_checkin.wav | jq -r '.transcript')

# 5. Think: Evaluate status; if distressed or non-responsive, trigger emergency escalation
TASK_ID=$(opal think task create --prompt "Evaluate resident response: '$CHECKIN_REPLY'. State EMERGENCY if help needed, otherwise OK." | jq -r '.id')
EVAL_OUT=$(opal think task watch "$TASK_ID" | tail -n 1)
```

##### Use Case 5: "Is the Garage Door Shut?" Verification (Listen $\to$ Look $\to$ Think $\to$ Say)
*Scenario:* A resident asks the voice assistant if the garage is open. The system captures a fresh frame from the garage camera, analyzes it with a vision pipeline, and speaks the confirmation.
```console
# 1. Listen: Recognize the query
opal listen recognition test-text --text "Did I remember to close the garage door?"

# 2. Look: Capture a fresh frame from the garage camera
opal look sources frame "cam-garage" --output /tmp/garage_status.jpg

# 3. Look: Run synchronous image analysis using captioning/classification
CAPABILITIES=$(opal look capabilities show | jq -r '.tasks[]')
# Confirm captioning or detection task is present
opal look analyze image --file /tmp/garage_status.jpg --options '{"classes": ["garage_door_open", "garage_door_closed"]}'

# 4. Think: Formulate conversational confirmation
TASK_ID=$(opal think task create \
  --prompt "Based on image analysis stating 'garage_door_closed' with 94% confidence, answer the user." | jq -r '.id')
ANSWER=$(opal think task watch "$TASK_ID" | tail -n 1)

# 5. Say: Speak answer to resident
opal say speak --text "$ANSWER"
```

---

#### Domain 2: Education & Assistive Learning

##### Use Case 6: Interactive Spoken Flashcard Coach (Think $\to$ Say $\to$ Listen)
*Scenario:* An automated tutor tests a biology student on photosynthesis, listens to the spoken answer, evaluates conceptual accuracy, and provides constructive guidance.
```console
# 1. Think: Generate a flashcard challenge question
TASK_ID=$(opal think task create --prompt "Generate one challenging high school biology question about ATP synthesis." | jq -r '.id')
QUESTION=$(opal think task watch "$TASK_ID" | tail -n 1)

# 2. Say: Read the question to the student
opal say speak --text "$QUESTION" --profile-id "tutor-voice" --output /tmp/question.wav
aplay /tmp/question.wav

# 3. Listen: Capture the student's verbal answer via microphone
STUDENT_ANSWER=$(opal listen recognition test-audio --file /tmp/student_answer.wav | jq -r '.transcript')

# 4. Think: Grade answer and explain nuance
EVAL_TASK=$(opal think task create \
  --prompt "Student was asked: '$QUESTION'. Student answered: '$STUDENT_ANSWER'. Grade the response (Correct/Incorrect) and explain missing nuances." | jq -r '.id')
EVAL_FEEDBACK=$(opal think task watch "$EVAL_TASK" | tail -n 1)

# 5. Say: Speak feedback
opal say speak --text "$EVAL_FEEDBACK" --profile-id "tutor-voice"
```

##### Use Case 7: Visual Specimen Discovery & Explanation (Look $\to$ Think $\to$ Say)
*Scenario:* A student places a rock or botanical specimen under a USB microscope camera and says "What is this?" Look captures the frame, Think classifies the object, and Say delivers an educational lesson.
```console
# 1. Look: Capture specimen still from high-res USB microscope
opal look sources frame "microscope-usb-0" --output /tmp/specimen.jpg

# 2. Look: Ingest into media registry for retention
MEDIA_ID=$(opal look media upload --file /tmp/specimen.jpg | jq -r '.id')

# 3. Think: Multi-modal identification and educational script generation
TASK_ID=$(opal think task create \
  --prompt "This specimen media ID is $MEDIA_ID. Provide a 3-sentence educational overview covering geological era, mineral composition, and common origins." \
  --context '{"media_id": "'"$MEDIA_ID"'"}' | jq -r '.id')
LESSON_TEXT=$(opal think task watch "$TASK_ID" | tail -n 1)

# 4. Say: Speak the generated educational brief
opal say speak --text "$LESSON_TEXT" --profile-id "tutor-voice"
```

##### Use Case 8: Multilingual Pronunciation Drill with Automated Regression (Listen $\to$ Say)
*Scenario:* A language learner practices French phrases. Listen audits phonetics, tracks failed pronunciations in the regression store, and Say demonstrates correct accentuation.
```console
# 1. Listen: Test audio input against expected French intent
AUDIO_RESULT=$(opal listen recognition test-audio --file /tmp/french_learner_attempt.wav --require-wakeword)
CONFIDENCE=$(echo "$AUDIO_RESULT" | jq -r '.confidence')

# 2. Listen: If confidence < 0.65, register as failed utterance for teacher review
if (( $(echo "$CONFIDENCE < 0.65" | bc -l) )); then
  FU_ID=$(opal listen failed list --limit 1 | jq -r '.items[0].id')
  opal listen failed promote "$FU_ID" --target-intent "phrase.french.bonjour" --create-regression
fi

# 3. Say: Demonstrate correct pronunciation using a native French voice profile
opal say speak \
  --text "Bonjour, comment allez-vous aujourd'hui?" \
  --voice-id "voice-fr-native-fem" \
  --speed 0.85
```

##### Use Case 9: Automated Classroom Attendance & Headcount Audit (Look $\to$ Event)
*Scenario:* A ceiling camera monitors an auditorium. Every 30 minutes, Look counts person instances in the classroom zone and publishes metrics to the school administration dashboard.
```console
# 1. Look: Define classroom bounding polygon and count threshold rule
opal look zones add --id "zone-classroom" --source-id "cam-ceiling" --kind "polygon" --points '[{"x":0,"y":0},{"x":1,"y":0},{"x":1,"y":1},{"x":0,"y":1}]'
opal look rules add \
  --id "rule-classroom-headcount" \
  --source-id "cam-ceiling" \
  --kind "count_threshold" \
  --zone-id "zone-classroom" \
  --class-filters '["person"]' \
  --threshold 0

# 2. Look: Extract current observation metrics
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
HEADCOUNT=$(opal look observations list --source-id "cam-ceiling" --label "person" --after "$TIMESTAMP" | jq '.total')

# 3. Event: Publish attendance metric on administrative bus
opal event publish \
  --topic "school.attendance.room101" \
  --data "{\"headcount\": $HEADCOUNT, \"timestamp\": \"$TIMESTAMP\"}" \
  --source "cam-ceiling"
```

##### Use Case 10: Reading Assistant for Visually Impaired Students (Look $\to$ Think $\to$ Say)
*Scenario:* A student holds a printed textbook page in front of the camera. Look extracts text via OCR, Think corrects formatting/OCR noise, and Say reads the passage aloud.
```console
# 1. Look: Capture reading frame
opal look sources frame "cam-desk" --output /tmp/book_page.jpg

# 2. Look: Run synchronous OCR pipeline
OCR_RAW=$(opal look analyze image --file /tmp/book_page.jpg --pipeline-id "pipeline-ocr-doc" | jq -r '.text')

# 3. Think: Structure raw OCR text into fluid reading sentences
TASK_ID=$(opal think task create \
  --prompt "Normalize this raw OCR output into clean, spoken English prose. Retain all original phrasing: $OCR_RAW" | jq -r '.id')
CLEAN_PROSE=$(opal think task watch "$TASK_ID" | tail -n 1)

# 4. Say: Stream clear acoustic reading
opal say stream --text "$CLEAN_PROSE" --speed 0.95 | aplay -f S16_LE -r 22050 -c 1
```

---

#### Domain 3: Voice Assistant & Ambient Interfaces

##### Use Case 11: Multi-Turn Collaborative Recipe Assistant (Listen $\to$ Think $\to$ Say)
*Scenario:* A home cook with messy hands asks for a gluten-free substitution, then asks a follow-up question ("How long do I bake it?"). Think maintains conversational state across turns.
```console
# 1. Think: Allocate a persistent conversational session
SESSION_ID=$(opal think session add --title "Dinner Prep Session" | jq -r '.id')

# Turn 1:
# 2. Listen & Think: Initial inquiry
PROMPT_1="I am making sourdough bread but ran out of rye flour. What can I substitute?"
TASK_1=$(opal think task create --session-id "$SESSION_ID" --prompt "$PROMPT_1" | jq -r '.id')
RESP_1=$(opal think task watch "$TASK_1" | tail -n 1)
opal say speak --text "$RESP_1"

# Turn 2:
# 3. Follow-up inquiry referencing conversational context
PROMPT_2="Will that change the recommended baking time at 450 degrees?"
TASK_2=$(opal think task create --session-id "$SESSION_ID" --prompt "$PROMPT_2" | jq -r '.id')
RESP_2=$(opal think task watch "$TASK_2" | tail -n 1)
opal say speak --text "$RESP_2"
```

##### Use Case 12: Voice-Created Kitchen Reminder (Listen $\to$ Event $\to$ Say)
*Scenario:* A resident says "Set a tea timer for 4 minutes." Listen parses the slot, Event registers a scheduled delayed action, and Say acknowledges the command immediately.
```console
# 1. Listen: Extract duration and label slots
PARSE_OUT=$(opal listen recognition test-text --text "Set a timer for 4 minutes for green tea")
DURATION_SEC=240

# 2. Event: Schedule delayed reminder action
opal event actions add \
  --id "act-timer-tea" \
  --type "shell" \
  --config '{"executable": "opal", "args": ["say", "speak", "--text", "Your green tea is ready!"]}'

# Ingest an event indicating timer creation
opal event publish --topic "timers.created" --data "{\"duration\": $DURATION_SEC, \"action\": \"act-timer-tea\"}"

# 3. Say: Vocalize immediate acknowledgment
opal say speak --text "Timer started for four minutes: green tea."
```

##### Use Case 13: "Drop In on the Nursery" (Look $\to$ Listen $\to$ Say)
*Scenario:* A parent issues a command to check the baby's crib. Look opens a low-latency annotated video stream, Listen reports room noise thresholds, and Say confirms quiet status.
```console
# 1. Look: Probe crib camera and grab snapshot
opal look sources probe "cam-crib"
opal look sources frame "cam-crib" --output /tmp/crib_live.jpg

# 2. Listen: Check microphone status and sound pressure levels in the nursery
NURSERY_AUDIO_STATUS=$(opal listen health)

# 3. Look: Inspect observations for child movement or standing
BABY_STATUS=$(opal look observations list --source-id "cam-crib" --limit 1 | jq -r '.items[0].label // "sleeping"')

# 4. Say: Deliver status summary to living room speaker
opal say speak --text "Nursery check complete. The room is quiet and baby is currently $BABY_STATUS."
```

##### Use Case 14: Automated Doorbell Intercom with Visual Screen (Look $\to$ Think $\to$ Say)
*Scenario:* A visitor rings the doorbell. Look inspects their identity attributes (uniform, clipboard, delivery truck), Think decides how to greet them, and Say conducts the dialogue through the door speaker.
```console
# 1. Look: Trigger capture on doorbell press
opal look sources capture "cam-doorbell" --output /tmp/visitor.jpg

# 2. Look: Classify visitor visual elements
VISITOR_LABELS=$(opal look analyze image --file /tmp/visitor.jpg --pipeline-id "pipeline-delivery-screen" | jq -r '.labels[]')

# 3. Think: Formulate appropriate greeting
GREETING_TASK=$(opal think task create \
  --prompt "A visitor is at the door with detected attributes: $VISITOR_LABELS. Formulate a polite greeting asking them to leave parcels in the lockbox." | jq -r '.id')
GREETING=$(opal think task watch "$GREETING_TASK" | tail -n 1)

# 4. Say: Speak through exterior intercom speaker
opal say speak --text "$GREETING" --output /tmp/door_reply.wav
aplay -D plughw:2,0 /tmp/door_reply.wav
```

##### Use Case 15: Acoustic Appliance Diagnostic (Listen $\to$ Think $\to$ Say)
*Scenario:* A dishwasher emits an unusual grinding noise. Listen records the acoustic stream, Think reviews mechanical fault frequencies, and Say explains the probable defective pump impeller.
```console
# 1. Listen: Capture 10 seconds of mechanical acoustic telemetry
opal listen recognition test-audio --file /tmp/dishwasher_grind.wav --save-log

# 2. Think: Analyze acoustic signature and symptoms
DIAG_TASK=$(opal think task create \
  --prompt "A domestic dishwasher emits rhythmic 120Hz grinding during the drain cycle. Diagnose likely mechanical failures and recommended user action." | jq -r '.id')
DIAG_SUMMARY=$(opal think task watch "$DIAG_TASK" | tail -n 1)

# 3. Say: Explain diagnosis to homeowner
opal say speak --text "$DIAG_SUMMARY"
```

---

#### Domain 4: Developer Operations, Enterprise & Custom Workflows

##### Use Case 16: CI/CD Build Failure Triage & Auditory Broadcast (Event $\to$ Think $\to$ Say)
*Scenario:* A GitHub Actions workflow fails on `main`. Event receives the webhook, Think summarizes the stack trace, and Say announces the root cause over the developer team room speakers.
```console
# 1. Event: Ingest CI failure webhook payload
opal event publish \
  --topic "ci.build.failed" \
  --data '{"repo": "opal-api", "branch": "main", "commit": "3f96d29", "error": "AssertionError: test_say_preconditions failed at line 84"}' \
  --source "github-actions"

# 2. Think: Summarize the build failure for spoken broadcast
TASK_ID=$(opal think task create \
  --prompt "Summarize this build failure in one spoken sentence for an engineering office: repo opal-api, branch main, error in test_say_preconditions." | jq -r '.id')
SPOKEN_SUMMARY=$(opal think task watch "$TASK_ID" | tail -n 1)

# 3. Say: Announce over engineering room audio system
opal say speak --text "$SPOKEN_SUMMARY" --profile-id "office-alert"
```

##### Use Case 17: Wildlife Camera Trap with Automated Species Cataloging (Look $\to$ Event $\to$ Think)
*Scenario:* A solar-powered trail camera detects an animal crossing. Look extracts a 5-second video clip artifact, Event routes the discovery, and Think logs a factual field entry.
```console
# 1. Look: Configure wildlife monitor with automatic clip retention
opal look rules add \
  --id "rule-wildlife-clip" \
  --source-id "cam-trail-01" \
  --kind "object_appears" \
  --class-filters '["deer", "bear", "coyote", "fox"]' \
  --clip-on-match

# 2. Look: Download triggered video artifact
ARTIFACT_ID=$(opal look artifacts list --limit 1 | jq -r '.items[0].id')
opal look artifacts download "$ARTIFACT_ID" --output /tmp/wildlife_clip.mp4

# 3. Think: Generate scientific field log entry from metadata
OBS_DATA=$(opal look observations list --source-id "cam-trail-01" --limit 5 | jq -c '.')
TASK_ID=$(opal think task create \
  --prompt "Generate a field observation entry based strictly on these visual observations: $OBS_DATA. Note timestamp and estimated confidence." | jq -r '.id')
FIELD_LOG=$(opal think task watch "$TASK_ID" | tail -n 1)

# 4. Event: Ingest field log entry into natural resource database
opal event publish --topic "research.wildlife.log" --data "{\"entry\": \"$FIELD_LOG\"}"
```

##### Use Case 18: Retail Store Footfall & Queue Bottleneck Sentry (Look $\to$ Event)
*Scenario:* An overhead store entrance camera counts customers crossing a threshold line. If customer occupancy in the checkout queue exceeds 8 people for 3 minutes, an alert requests staff assistance.
```console
# 1. Look: Create line tripwire at store entrance
opal look zones add --id "zone-entrance-door" --source-id "cam-overhead" --kind "line" --points '[{"x":0.2,"y":0.5},{"x":0.8,"y":0.5}]'
opal look rules add --id "rule-inbound-traffic" --source-id "cam-overhead" --kind "line_crosses" --zone-id "zone-entrance-door" --class-filters '["person"]'

# 2. Look: Create checkout zone occupancy count rule
opal look zones add --id "zone-checkout-line" --source-id "cam-overhead" --kind "polygon" --points '[{"x":0.1,"y":0.6},{"x":0.5,"y":0.6},{"x":0.5,"y":0.95},{"x":0.1,"y":0.95}]'
opal look rules add \
  --id "rule-queue-overflow" \
  --source-id "cam-overhead" \
  --kind "count_threshold" \
  --zone-id "zone-checkout-line" \
  --threshold 8 \
  --duration-ms 180000

# 3. Event: Register manager pager action when queue threshold is breached
opal event rules add \
  --id "rule-notify-floor-manager" \
  --topic "opal.look.cam-overhead.rule.rule-queue-overflow" \
  --actions '["notify-pager"]' \
  --enabled
```

##### Use Case 19: Dynamic AI Agent Tool Discovery & Execution (Event $\to$ Think $\to$ Event)
*Scenario:* An autonomous agent running in Think inspects the Event service action catalog, selects an appropriate tool to export a backup archive, and requests its execution.
```console
# 1. Event: Query the registered action catalog and extract descriptions & schemas
ACTION_CATALOG=$(opal event actions list | jq -c '[.items[] | {id: .id, description: .description, schema: .input_schema}]')

# 2. Think: Agent analyzes user goal and selects the target action with payload
AGENT_PROMPT="Goal: Export the latest database state. Catalog: $ACTION_CATALOG. Output the exact action ID and JSON payload to invoke."
TASK_ID=$(opal think task create --prompt "$AGENT_PROMPT" | jq -r '.id')
AGENT_DECISION=$(opal think task watch "$TASK_ID" | tail -n 1)

TARGET_ACTION=$(echo "$AGENT_DECISION" | jq -r '.action_id')
TARGET_PAYLOAD=$(echo "$AGENT_DECISION" | jq -r '.payload')

# 3. Event: Safely execute the chosen action
opal event actions execute "$TARGET_ACTION" --payload "$TARGET_PAYLOAD"
```

##### Use Case 20: Disaster Recovery Suite Backup, Migration & Validation (Kernel $\to$ All Services)
*Scenario:* Prior to a data center migration, the DevOps administrator executes atomic backup exports across Event, Listen, Look, and Say, validates their bundles against target schemas, and verifies health.
```console
# 1. Export configuration bundles across all four stateful services
opal event backup export --output /var/backups/opal/event_config.json
opal listen backup export --output /var/backups/opal/listen_config.json
opal look configuration export --output /var/backups/opal/look_config.json
opal say backup export --output /var/backups/opal/say_config.json

# 2. Validate bundles against target deployment schemas prior to import
opal event backup validate --input /var/backups/opal/event_config.json
opal listen backup validate --input /var/backups/opal/listen_config.json
opal look configuration validate --input /var/backups/opal/look_config.json
opal say backup validate --input /var/backups/opal/say_config.json

# 3. Import atomically into the destination cluster (requires strong ETag)
EVENT_ETAG=$(curl -sI http://target-cluster:8080/api/v1/settings/ | grep -i ETag | tr -d '\r' | awk '{print $2}')
opal event backup import --input /var/backups/opal/event_config.json --if-match "$EVENT_ETAG"

# 4. Probe target cluster liveness and readiness across the suite
opal event health ready
opal listen health ready
opal look health ready
opal say health ready
opal think health ready
```

---

## 4. Typer Implementation Design Notes

When realizing this specification as an executable Python distribution:

```python
# Conceptual Typer application hierarchy:
import typer

app = typer.Typer(name="opal", help="OPAL Ambient Intelligence Suite CLI")

event_app = typer.Typer(name="event", help="Event bus and automation")
listen_app = typer.Typer(name="listen", help="Acoustic and speech recognition")
look_app = typer.Typer(name="look", help="Computer vision and spatial analysis")
say_app = typer.Typer(name="say", help="Text-to-speech auditory synthesis")
think_app = typer.Typer(name="think", help="Durable cognitive task engine")

app.add_typer(event_app)
app.add_typer(listen_app)
app.add_typer(look_app)
app.add_typer(say_app)
app.add_typer(think_app)
```

1. **Sub-App Independence:**
   Each sub-app resolves its target service URL from environment variables (`OPAL_LOOK_URL`, `OPAL_THINK_URL`, etc.) with fallback to the OpenAPI `servers.url` default. Missing peer services do not prevent independent operation.
2. **HTTP Preconditions:**
   Mutations should fetch the remote ETag via a preliminary `GET` when `--if-match auto` is specified, but strictly mandate `--if-match <ETag>` when scripted in headless CI pipelines.
3. **Chunked Streaming & Process Interop:**
   Endpoints such as `opal say stream` and `opal look sources stream` pipe raw binary bytes directly to standard output (`sys.stdout.buffer`), enabling clean Unix piping (`| aplay`, `| ffplay`, `| ffmpeg`).
4. **JSON Serialization:**
   All commands support `--json` output, ensuring responses conform to the corresponding schema in `openapi/*.yaml` and integrate cleanly with `jq`.
