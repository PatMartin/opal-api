# The OPAL CLI Cookbook (v1.7.1)

*Field manual for commanding five microservices that can see your porch, hear your excuses, ponder your life choices, gossip over ZeroMQ, and read the verdict out loud in a polite British baritone.*

This cookbook covers the unified `opal` Typer CLI built on the v1.7.1 OpenAPI contracts (`openapi/*.yaml`) and the shared OPAL Suite Kernel (`openapi/shared/opal_kernel.yaml`).

## Ground Rules & CLI Conventions

- **Canonical verbs**: Resource CRUD uses `list | add | show | update | remove`. Operational endpoints use explicit verbs (`generate`, `stream`, `test`, `validate`, `activate`, `start`, `stop`, `watch`, `cancel`, `probe`, `capture`, `submit`, `promote`, `run`, `publish`, `execute`, `fetch`).
- **Standardized groups**:
  - `config` holds mutable configuration (`voice`, `wakeword`, `intent`, `slot`, `model`, `pipeline`, `zone`, `rule`, `monitor`, `action`, `profile`, `persona`, `setting`).
  - `data` / `history` holds runtime artifacts and historical records (`job`, `observation`, `media`, `capture`, `artifact`, `recording`, `failed-utterance`, `event`, `execution`).
  - `info` holds probes and telemetry (`health`, `version`, `ping`, `live`, `ready`, `capabilities`, `metrics`, `events`, `stats`, `audio-devices`).
  - `service` controls daemon lifecycle (`start`, `stop`, `log`).
  - `backup` handles snapshots and portable configuration (`list`, `create`, `download`, `restore`, `remove`, `export`, `import`, `validate`).
- **Settings parity**: Across all five services, `opal <service> config setting` exposes `list`, `update` (alias `patch`), `show`, `set`, and `remove` (alias `reset`).
- **Optimistic concurrency without the tears**: Config mutations require `If-Match` against the service's strong ETag. The Typer CLI automatically fetches and attaches the current ETag unless you explicitly pass `--if-match`.
- **Portable Personas**: `opal-think` is the authoritative persona writer (`origin: local`); other services can cache owner personas (`origin: owner`) or run standalone. Resolution order is always **explicit request field > persona binding > active/selected profile > service default**.

---

## INTERFACE: `opal-say`

*Text-to-speech synthesis over host-installed engines (Piper, Kokoro, etc.) without caring how many ONNX files live under `/opt`.*

### 1. Typer Command Tree

```text
opal say
├── generate                synthesize completed WAV/PCM (or progressive PCM with --stream)
├── stream                  synthesize progressive raw s16le mono PCM stream
├── engine
│   ├── list
│   ├── show
│   ├── update
│   └── validate
├── config
│   ├── voice
│   │   ├── list
│   │   ├── add
│   │   ├── show
│   │   ├── update
│   │   ├── remove
│   │   ├── validate
│   │   └── test
│   ├── profile
│   │   ├── list
│   │   ├── add
│   │   ├── show
│   │   ├── update
│   │   ├── remove
│   │   └── activate
│   ├── persona
│   │   ├── list
│   │   ├── add
│   │   ├── show
│   │   ├── update
│   │   ├── remove
│   │   └── validate
│   └── setting
│       ├── list
│       ├── update          (alias: patch)
│       ├── show
│       ├── set
│       └── remove          (alias: delete)
├── service
│   ├── start
│   ├── stop
│   └── log
├── info
│   ├── health
│   ├── version
│   ├── ping
│   ├── live
│   └── ready
└── backup
    ├── list
    ├── create
    ├── download
    ├── restore
    ├── remove
    ├── export
    ├── import
    └── validate
```

### 2. REST Tree (`openapi/opal_say.yaml`)

```text
/api/v1
├── /generate                               POST
├── /generate/stream                        POST
├── /engine/                                GET
│   └── /{engine_id}                        GET, PATCH
│       └── /validate                       POST
├── /voice/                                 GET, POST
│   └── /{voice_id}                         GET, PATCH, DELETE
│       ├── /validate                       POST
│       └── /test                           POST
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
├── /info/                                  GET
│   └── /ping                               GET
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
└── /backup
    ├── /list                               GET
    ├── /create                             POST
    ├── /download/{filename}                GET
    ├── /restore/{filename}                 POST
    ├── /{filename}                         DELETE
    ├── /export                             GET
    ├── /import                             POST
    └── /validate                           GET, POST
```

### 3. Command Reference

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal say generate` | `--text TEXT`, `--text-file PATH`, `--profile INT`, `--persona ID`, `--voice ID`, `--engine ID`, `--speed FLOAT`, `--volume FLOAT`, `--sample-rate INT`, `--output-format [wav\|pcm]`, `--engine-options JSON`, `--stream`, `--out PATH` | Synthesize speech audio from plain text (`POST /api/v1/generate`, or `/generate/stream` with `--stream`). |
| `opal say stream` | `--text TEXT`, `--text-file PATH`, `--profile INT`, `--persona ID`, `--voice ID`, `--engine ID`, `--speed FLOAT`, `--volume FLOAT`, `--sample-rate INT`, `--engine-options JSON`, `--out PATH` | Stream raw `s16le` mono PCM audio progressively (`POST /api/v1/generate/stream`). |
| `opal say engine list` | `--json` | List installed TTS synthesis engines (`GET /api/v1/engine/`). |
| `opal say engine show` | `<engine_id>` | Inspect a single TTS engine (`GET /api/v1/engine/{engine_id}`). |
| `opal say engine update` | `<engine_id>`, `--enabled/--disabled`, `--options JSON`, `--if-match ETAG` | Enable/disable an engine or update its options (`PATCH /api/v1/engine/{engine_id}`). |
| `opal say engine validate` | `<engine_id>` | Verify engine binary and runtime readiness (`POST /api/v1/engine/{engine_id}/validate`). |
| `opal say config voice list` | `--engine ID`, `--language TAG`, `--enabled BOOL` | List registered OPAL voices (`GET /api/v1/voice/`). |
| `opal say config voice add` | `--voice-id ID`, `--name TEXT`, `--engine ID`, `--engine-voice-ref REF`, `--language TAG`, `--description TEXT`, `--enabled/--disabled`, `--engine-options JSON` | Register a host voice/model resource (`POST /api/v1/voice/`). |
| `opal say config voice show` | `<voice_id>` | Show details of a registered voice (`GET /api/v1/voice/{voice_id}`). |
| `opal say config voice update` | `<voice_id>`, `--name TEXT`, `--description TEXT`, `--engine ID`, `--engine-voice-ref REF`, `--language TAG`, `--enabled/--disabled`, `--engine-options JSON` | Update a registered voice (`PATCH /api/v1/voice/{voice_id}`). |
| `opal say config voice remove` | `<voice_id>` | Unregister a voice without deleting host files (`DELETE /api/v1/voice/{voice_id}`). |
| `opal say config voice validate` | `<voice_id>` | Check that a voice's model files and engine resolve (`POST /api/v1/voice/{voice_id}/validate`). |
| `opal say config voice test` | `<voice_id>`, `--text TEXT`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON`, `--out PATH` | Synthesize a short audition clip for a voice (`POST /api/v1/voice/{voice_id}/test`). |
| `opal say config profile list` | `--json` | List generation preset profiles (`GET /api/v1/profile/`). |
| `opal say config profile add` | `--name TEXT`, `--description TEXT`, `--voice ID`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON`, `--active/--inactive` | Create a generation profile (`POST /api/v1/profile/`). |
| `opal say config profile show` | `<profile_id>` | Show one generation profile (`GET /api/v1/profile/{profile_id}`). |
| `opal say config profile update` | `<profile_id>`, `--name TEXT`, `--description TEXT`, `--voice ID`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON` | Update a generation profile (`PATCH /api/v1/profile/{profile_id}`). |
| `opal say config profile remove` | `<profile_id>` | Delete a non-active profile (`DELETE /api/v1/profile/{profile_id}`). |
| `opal say config profile activate` | `<profile_id>` | Make a profile the active default (`POST /api/v1/profile/{profile_id}/activate`). |
| `opal say config persona list` | `--enabled BOOL` | List personas and their bound `voice_id` (`GET /api/v1/persona/`). |
| `opal say config persona add` | `--persona-id ID`, `--name TEXT`, `--voice ID`, `--description TEXT`, `--enabled/--disabled` | Create a persona with a required `voice_id` (`POST /api/v1/persona/`). |
| `opal say config persona show` | `<persona_id>` | Show a persona and its `origin` (`GET /api/v1/persona/{persona_id}`). |
| `opal say config persona update` | `<persona_id>`, `--name TEXT`, `--voice ID`, `--description TEXT`, `--enabled/--disabled` | Update a persona's voice or metadata (`PATCH /api/v1/persona/{persona_id}`). |
| `opal say config persona remove` | `<persona_id>` | Delete a persona (`DELETE /api/v1/persona/{persona_id}`). |
| `opal say config persona validate` | `<persona_id>` | Validate that the persona's bound `voice_id` is resolvable (`POST /api/v1/persona/{persona_id}/validate`). |
| `opal say config setting list` | `--json` | List all runtime settings (`GET /api/v1/setting/`). |
| `opal say config setting update` | `--data JSON` | Atomically patch multiple settings (`PATCH /api/v1/setting/`). |
| `opal say config setting show` | `<key>` | Inspect one setting key (`GET /api/v1/setting/{key}`). |
| `opal say config setting set` | `<key>`, `<value_json>` | Set a single setting key (`PUT /api/v1/setting/{key}`). |
| `opal say config setting remove` | `<key>` | Reset a setting key to its default (`DELETE /api/v1/setting/{key}`). |
| `opal say service start\|stop\|log` | `--append BOOL`, `--lines INT` | Start/stop the background service or tail its log (`/api/v1/service/*`). |
| `opal say info health\|version\|ping\|live\|ready` | `--json` | Service health, build info, and readiness probes (`/api/v1/health/*`, `/api/v1/info/*`). |
| `opal say backup list\|create\|download\|restore\|remove\|export\|import\|validate` | `<filename>`, `--file PATH`, `--out PATH` | Manage snapshots and portable config bundles (`/api/v1/backup/*`). |

---

## INTERFACE: `opal-listen`

*Wakeword detection, speech-to-text, deterministic intent & slot extraction, and a regression harness for people tired of repeating "turn on the kitchen lights" at 2 AM.*

### 1. Typer Command Tree

```text
opal listen
├── recognition
│   ├── test                unified dry-run: --text <utt> OR --audio <wav>
│   ├── test-text           dry-run text through normalization + intent + slot matching
│   ├── test-audio          dry-run 16-bit PCM WAV through wakeword + STT + NLU
│   ├── start               start live microphone recognition pipeline
│   ├── stop                stop live microphone recognition pipeline
│   ├── status              pipeline state and counter snapshot
│   └── stream              SSE stream of live recognition events
├── config
│   ├── wakeword            list | add | show | update | remove
│   ├── intent              list | add | show | update | remove
│   │   └── phrase          list | add | remove
│   ├── slot                list | add | show | update | remove
│   │   ├── value           list | add | remove
│   │   └── alias           list | add | remove
│   ├── profile             list | add | show | update | remove | activate
│   ├── persona             list | add | show | update | remove | validate
│   └── setting             list | update | show | set | remove
├── data
│   └── failed-utterance    list | add | show | update | remove | promote
├── regression              list | add | show | update | remove | run
├── performance             last | summary | history
├── service                 start | stop | log
├── info                    health | audio-devices | version | ping | live | ready
└── backup                  list | create | download | restore | remove | export | import | validate
```

### 2. REST Tree (`openapi/opal_listen.yaml`)

```text
/api/v1
├── /wakeword/                              GET, POST
│   └── /{wakeword_id}                      GET, PATCH, DELETE
├── /intent/                                GET, POST
│   └── /{intent_id}                        GET, PATCH, DELETE
│       └── /phrase                         GET, POST
│           └── /{phrase_id}                DELETE
├── /slot/                                  GET, POST
│   └── /{slot_id}                          GET, PATCH, DELETE
│       └── /value                          GET, POST
│           └── /{value_id}                 DELETE
│               └── /alias                  GET, POST
│                   └── /{alias_id}         DELETE
├── /recognition
│   ├── /test_text                          POST
│   ├── /test_audio                         POST
│   ├── /start                              POST
│   ├── /stop                               POST
│   ├── /status                             GET
│   └── /stream                             GET (SSE)
├── /failed_utterance/                      GET, POST
│   └── /{fu_id}                            GET, PATCH, DELETE
│       └── /promote                        POST
├── /regression/                            GET, POST
│   ├── /run                                POST
│   └── /{test_id}                          GET, PATCH, DELETE
├── /performance
│   ├── /last                               GET
│   ├── /summary                            GET
│   └── /history                            GET
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
├── /info/                                  GET
│   └── /ping                               GET
├── /health/                                GET
│   ├── /audio_devices                      GET
│   ├── /live                               GET
│   └── /ready                              GET
└── /backup
    ├── /list                               GET
    ├── /create                             POST
    ├── /download/{filename}                GET
    ├── /restore/{filename}                 POST
    ├── /{filename}                         DELETE
    ├── /export                             GET
    ├── /import                             POST
    └── /validate                           GET, POST
```

### 3. Command Reference

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal listen recognition test` | `--text TEXT` \| `--audio WAV`, `--save/--no-save`, `--require-wakeword`, `--expect-intent NAME`, `--verbose` | Unified recognition test: pass `--text` or `--audio` (XOR) (`POST /api/v1/recognition/test_text` or `/test_audio`). |
| `opal listen recognition test-text` | `--text TEXT`, `--save/--no-save`, `--expect-intent NAME`, `--verbose` | Run text through normalization, intent matching, and slot extraction (`POST /api/v1/recognition/test_text`). |
| `opal listen recognition test-audio` | `<wav_path>`, `--save/--no-save`, `--require-wakeword`, `--expect-intent NAME`, `--verbose` | Run a 16-bit PCM WAV file through wakeword + STT + NLU (`POST /api/v1/recognition/test_audio`). |
| `opal listen recognition start\|stop\|status` | `--json` | Start, stop, or inspect the live microphone pipeline (`/api/v1/recognition/start\|stop\|status`). |
| `opal listen recognition stream` | `--debug BOOL` | Stream live recognition matches and debug telemetry over SSE (`GET /api/v1/recognition/stream`). |
| `opal listen config wakeword list\|add\|show\|update\|remove` | `<wakeword_id>`, `--name TEXT`, `--confidence-threshold FLOAT`, `--enabled/--disabled` | Manage wakeword models and thresholds (`/api/v1/wakeword/*`). |
| `opal listen config intent list\|add\|show\|update\|remove` | `<intent_id>`, `--name TEXT`, `--description TEXT`, `--confidence-threshold FLOAT`, `--phrase TEXT...`, `--enabled/--disabled` | Manage intents and initial training phrases (`/api/v1/intent/*`). |
| `opal listen config intent phrase list\|add\|remove` | `<intent_id>`, `<phrase_id>`, `--phrase TEXT` | List, add, or delete training phrases on an intent (`/api/v1/intent/{id}/phrase/*`). |
| `opal listen config slot list\|add\|show\|update\|remove` | `<slot_id>`, `--name TEXT`, `--slot-type TEXT`, `--description TEXT` | Manage named entity slots (`/api/v1/slot/*`). |
| `opal listen config slot value list\|add\|remove` | `<slot_id>`, `<value_id>`, `--value TEXT` | Manage canonical values inside a slot (`/api/v1/slot/{id}/value/*`). |
| `opal listen config slot alias list\|add\|remove` | `<slot_id>`, `<value_id>`, `<alias_id>`, `--alias TEXT` | Manage spoken synonyms for a canonical slot value (`/api/v1/slot/{id}/value/{vid}/alias/*`). |
| `opal listen data failed-utterance list` | `--reviewed BOOL`, `--promoted BOOL`, `--limit INT`, `--offset INT` | List unrecognized utterances queued for human review (`GET /api/v1/failed_utterance/`). |
| `opal listen data failed-utterance add\|show\|update\|remove` | `<fu_id>`, `--transcript TEXT`, `--expected-intent NAME`, `--notes TEXT`, `--reviewed BOOL` | Record, inspect, annotate, or delete a failed utterance (`/api/v1/failed_utterance/*`). |
| `opal listen data failed-utterance promote` | `<fu_id>`, `--intent-name NAME`, `--create-regression BOOL` | Promote a miss into an intent training phrase and optional regression test (`POST /api/v1/failed_utterance/{id}/promote`). |
| `opal listen regression list\|add\|show\|update\|remove` | `<test_id>`, `--name TEXT`, `--phrase TEXT`, `--expected-intent NAME`, `--expected-slots JSON`, `--enabled/--disabled` | Manage saved NLU regression test cases (`/api/v1/regression/*`). |
| `opal listen regression run` | `--enabled-only BOOL` | Execute the regression suite and report pass/fail counts (`POST /api/v1/regression/run`). |
| `opal listen performance last\|summary\|history` | `--limit INT` | Inspect stage latency metrics for the last utterance, rolling summary, or bounded history (`/api/v1/performance/*`). |
| `opal listen config profile list\|add\|show\|update\|remove\|activate` | `<profile_id>`, `--name TEXT`, `--wakeword-names JSON`, `--enabled-intents JSON`, `--enabled-slots JSON`, `--vad-settings JSON` | Manage recognition profiles and activate the default (`/api/v1/profile/*`). |
| `opal listen config persona list\|add\|show\|update\|remove\|validate` | `<persona_id>`, `--name TEXT`, `--voice ID`, `--description TEXT`, `--enabled/--disabled` | Manage portable persona records in Listen (`/api/v1/persona/*`). |
| `opal listen config setting list\|update\|show\|set\|remove` | `<key>`, `<value_json>`, `--data JSON` | Manage Listen runtime settings (`/api/v1/setting/*`). |
| `opal listen info health\|audio-devices\|version\|ping\|live\|ready` | `--json` | Inspect service health and enumerate host microphones (`GET /api/v1/health/audio_devices`, `/api/v1/info/*`). |
| `opal listen service start\|stop\|log` | `--append BOOL` | Control the Listen daemon process (`/api/v1/service/*`). |
| `opal listen backup list\|create\|download\|restore\|remove\|export\|import\|validate` | `<filename>`, `--file PATH`, `--out PATH` | Backup and restore recognition catalogs (`/api/v1/backup/*`). |

---

## INTERFACE: `opal-look`

*Visual observation, DAG pipelines, polygon zones, tripwires, self-healing camera monitors, and unified `OutputRef` byte retrieval.*

### 1. Typer Command Tree

```text
opal look
├── analyze
│   ├── run                 synchronous single-frame analysis on a source/media/capture
│   └── image               multipart upload + immediate analysis of a still image
├── session
│   ├── start               start a live observation session on a source
│   ├── list
│   ├── show
│   ├── stop
│   ├── stream              SSE stream of live session observations
│   └── preview             MJPEG stream with live bounding-box overlays
├── source
│   ├── list
│   ├── add
│   ├── show
│   ├── update
│   ├── remove
│   ├── status              live connectivity and frame-drop telemetry
│   ├── probe               actively probe camera/stream dimensions and codecs
│   ├── frame               grab an immediate JPEG frame (optional overlay)
│   ├── capture             persist an exact frame Capture (with OutputRef)
│   └── stream              MJPEG live view of a source
├── engine
│   ├── list
│   ├── show
│   └── update
├── output
│   └── fetch               download bytes from any OutputRef content_url
├── config
│   ├── model               list | add | show | update | remove
│   ├── pipeline            list | add | show | update | remove | validate
│   ├── zone                list | add | show | update | remove
│   ├── rule                list | add | show | update | remove
│   ├── monitor             list | add | show | update | remove
│   ├── profile             list | add | show | update | remove | activate
│   ├── persona             list | add | show | update | remove | validate
│   └── setting             list | update | show | set | remove
├── data
│   ├── job                 submit | list | show | cancel
│   ├── observation         list | show
│   ├── media               upload | list | show | remove
│   ├── capture             list | show | remove | download
│   ├── artifact            list | show | remove | download
│   └── recording           start | list | show | stop
├── service                 start | stop | log
├── info                    capabilities | health | version | ping | live | ready | metrics | events
└── backup                  list | create | download | restore | remove | export | import | validate
```

### 2. REST Tree (`openapi/opal_look.yaml`)

```text
/api/v1
├── /capabilities/                          GET
├── /engine/                                GET
│   └── /{engine_id}                        GET, PATCH
├── /model/                                 GET, POST
│   └── /{model_id}                         GET, PATCH, DELETE
├── /source/                                GET, POST
│   └── /{source_id}                        GET, PATCH, DELETE
│       ├── /status                         GET
│       ├── /probe                          POST
│       ├── /frame                          GET
│       ├── /capture/                       POST
│       └── /stream                         GET (MJPEG)
├── /pipeline/                              GET, POST
│   ├── /validate                           POST
│   └── /{pipeline_id}                      GET, PATCH, DELETE
├── /zone/                                  GET, POST
│   └── /{zone_id}                          GET, PATCH, DELETE
├── /rule/                                  GET, POST
│   └── /{rule_id}                          GET, PATCH, DELETE
├── /monitor/                               GET, POST
│   └── /{monitor_id}                       GET, PATCH, DELETE
├── /analyze/                               POST
│   └── /image                              POST (multipart)
├── /session/                               GET, POST
│   └── /{session_id}                       GET
│       ├── /stop                           POST
│       ├── /stream                         GET (SSE)
│       └── /preview                        GET (MJPEG)
├── /job/                                   GET, POST
│   └── /{job_id}                           GET
│       └── /cancel                         POST
├── /observation/                           GET
│   └── /{observation_id}                   GET
├── /media/                                 GET, POST (multipart)
│   └── /{media_id}                         GET, DELETE
├── /capture/                               GET
│   └── /{capture_id}                       GET, DELETE
│       └── /content                        GET (bytes)
├── /artifact/                              GET
│   └── /{artifact_id}                      GET, DELETE
│       └── /content                        GET (bytes)
├── /recording/                             GET, POST
│   └── /{recording_id}                     GET
│       └── /stop                           POST
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /metrics/                               GET
├── /events/status                          GET
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
├── /info/                                  GET
│   └── /ping                               GET
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
└── /backup
    ├── /list                               GET
    ├── /create                             POST
    ├── /download/{filename}                GET
    ├── /restore/{filename}                 POST
    ├── /{filename}                         DELETE
    ├── /export                             GET
    ├── /import                             POST
    └── /validate                           POST
```

### 3. Command Reference

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal look analyze run` | `--source ID`, `--pipeline ID`, `--profile ID`, `--options JSON`, `--retention JSON` | Run synchronous single-frame analysis (`POST /api/v1/analyze/`). |
| `opal look analyze image` | `<image_path>`, `--pipeline ID`, `--profile ID`, `--tasks JSON` | Upload a still image and analyze it immediately (`POST /api/v1/analyze/image`). |
| `opal look source list\|add\|show\|update\|remove` | `<source_id>`, `--id ID`, `--kind [rtsp\|camera\|http\|media]`, `--name TEXT`, `--locator URI`, `--secret-ref REF`, `--options JSON`, `--enabled/--disabled` | Register and manage visual input sources (`/api/v1/source/*`). |
| `opal look source status` | `<source_id>` | Show connection health, FPS, and dropped-frame counters (`GET /api/v1/source/{id}/status`). |
| `opal look source probe` | `<source_id>` | Actively connect and probe resolution/codec metadata (`POST /api/v1/source/{id}/probe`). |
| `opal look source frame` | `<source_id>`, `--pipeline ID`, `--width INT`, `--height INT`, `--quality INT`, `--presentation-filter TEXT`, `--out PATH` | Fetch an immediate JPEG frame from a source (`GET /api/v1/source/{id}/frame`). |
| `opal look source capture` | `<source_id>`, `--retain/--no-retain`, `--annotate/--no-annotate`, `--session ID`, `--observation ID` | Persist an exact frame capture returning `output_ref` (`POST /api/v1/source/{id}/capture/`). |
| `opal look source stream` | `<source_id>`, `--annotations BOOL`, `--pipeline ID`, `--classes LIST`, `--min-confidence FLOAT`, `--target-fps FLOAT`, `--out PATH` | Stream live MJPEG video from a source (`GET /api/v1/source/{id}/stream`). |
| `opal look session start` | `--source ID`, `--pipeline ID`, `--profile ID`, `--options JSON`, `--retention JSON`, `--auto-start BOOL` | Admit and start a continuous observation session (`POST /api/v1/session/`). |
| `opal look session list\|show\|stop` | `<session_id>`, `--state STATE`, `--source ID`, `--limit INT` | List, inspect, or stop active observation sessions (`/api/v1/session/*`). |
| `opal look session stream` | `<session_id>`, `--last-event-id ID` | Follow live session observations over SSE (`GET /api/v1/session/{id}/stream`). |
| `opal look session preview` | `<session_id>`, `--classes LIST`, `--min-confidence FLOAT`, `--show-labels BOOL`, `--show-boxes BOOL`, `--target-fps FLOAT` | Stream annotated MJPEG preview for a running session (`GET /api/v1/session/{id}/preview`). |
| `opal look engine list\|show\|update` | `<engine_id>`, `--enabled/--disabled`, `--options JSON` | Inspect or configure vision inference backends (`/api/v1/engine/*`). |
| `opal look config model list\|add\|show\|update\|remove` | `<model_id>`, `--id ID`, `--engine ID`, `--resource-ref PATH`, `--tasks JSON`, `--display-name TEXT`, `--options JSON` | Register and manage vision models (`/api/v1/model/*`). |
| `opal look config pipeline list\|add\|show\|update\|remove\|validate` | `<pipeline_id>`, `--id ID`, `--name TEXT`, `--stages JSON`, `--description TEXT` | Manage and dry-run multi-stage vision DAG pipelines (`/api/v1/pipeline/*`). |
| `opal look config zone list\|add\|show\|update\|remove` | `<zone_id>`, `--id ID`, `--source ID`, `--name TEXT`, `--kind [polygon\|line]`, `--points JSON`, `--enabled/--disabled` | Define spatial polygons or tripwire lines on a source (`/api/v1/zone/*`). |
| `opal look config rule list\|add\|show\|update\|remove` | `<rule_id>`, `--id ID`, `--name TEXT`, `--source ID`, `--zone ID`, `--kind KIND`, `--class-filters JSON`, `--threshold FLOAT`, `--minimum-duration-ms INT`, `--cooldown-ms INT`, `--capture-on-match`, `--clip-on-match` | Manage visual detection rules (`enters_zone`, `dwell_time`, `line_crosses`, `object_appears`, etc.) (`/api/v1/rule/*`). |
| `opal look config monitor list\|add\|show\|update\|remove` | `<monitor_id>`, `--id ID`, `--name TEXT`, `--source ID`, `--pipeline ID`, `--profile ID`, `--restart-policy [always\|on_failure\|never]`, `--enabled/--disabled` | Manage always-on supervised camera monitors (`/api/v1/monitor/*`). |
| `opal look data job submit\|list\|show\|cancel` | `<job_id>`, `--kind KIND`, `--source ID`, `--media ID`, `--pipeline ID`, `--range JSON`, `--output JSON`, `--state STATE`, `--limit INT` | Submit, list, inspect (with `output_refs`), or cancel asynchronous video/export jobs (`/api/v1/job/*`). |
| `opal look data observation list\|show` | `<observation_id>`, `--source ID`, `--session ID`, `--job ID`, `--task TEXT`, `--label TEXT`, `--after ISO`, `--before ISO`, `--limit INT` | Query immutable retained visual observations (`/api/v1/observation/*`). |
| `opal look data media upload\|list\|show\|remove` | `<media_id>`, `<file_path>`, `--limit INT` | Upload or manage input media files for offline analysis (`/api/v1/media/*`). |
| `opal look data capture list\|show\|remove\|download` | `<capture_id>`, `--limit INT`, `--out PATH` | Inspect captures (with `output_ref`), delete, or download JPEG/PNG bytes (`/api/v1/capture/*`). |
| `opal look data artifact list\|show\|remove\|download` | `<artifact_id>`, `--limit INT`, `--out PATH` | Inspect derived video/clip artifacts, delete, or download bytes (`/api/v1/artifact/*`). |
| `opal look data recording start\|list\|show\|stop` | `<recording_id>`, `--source ID`, `--include-audio BOOL`, `--max-duration-seconds INT`, `--limit INT` | Start, inspect, or finalize source recordings into artifacts (`artifact_ref`) (`/api/v1/recording/*`). |
| `opal look output fetch` | `<content_url>`, `--out PATH` | Unified byte retrieval: download any capture, recording, or export job via its `OutputRef.content_url`. |
| `opal look config profile\|persona\|setting ...` | Standard suite options | Manage Look profiles, portable personas, and settings (`/api/v1/profile/*`, `/persona/*`, `/setting/*`). |
| `opal look info capabilities\|health\|version\|ping\|live\|ready\|metrics\|events` | `--json` | Query supported tasks/codecs, health, frame counters, and ZeroMQ publisher status. |
| `opal look service start\|stop\|log` | `--append BOOL` | Control the Look daemon process (`/api/v1/service/*`). |
| `opal look backup list\|create\|download\|restore\|remove\|export\|import\|validate` | `<filename>`, `--file PATH`, `--out PATH` | Manage Look configuration backups (`/api/v1/backup/*`). |

---

## INTERFACE: `opal-think`

*Asynchronous LLM reasoning, multi-turn conversation sessions, provider model discovery, and the suite's authoritative persona registry.*

### 1. Typer Command Tree

```text
opal think
├── ask                     shortcut: create a stateless task, stream/wait, print answer
├── chat                    shortcut: interactive or single-turn session-bound task
├── task
│   ├── create              submit an asynchronous reasoning task (202 Accepted)
│   ├── list                list retained tasks (bounded array)
│   ├── show                authoritative snapshot of task state and output
│   ├── watch               follow SSE stream of task progress and token deltas
│   └── cancel              request cooperative cancellation
├── session
│   ├── add                 create a conversation session container
│   ├── list                list retained sessions (bounded array)
│   ├── show                inspect session metadata and turn history
│   └── remove              delete a session
├── model
│   ├── list                list discovered provider models and capabilities
│   └── show                inspect one model's context length and features
├── config
│   ├── profile             list | add | show | update | remove | activate
│   ├── persona             list | add | show | update | remove | validate
│   └── setting             list | update | show | set | remove
├── service
│   ├── start
│   ├── stop
│   └── log
├── info
│   ├── health
│   ├── version
│   ├── ping
│   ├── live
│   └── ready
└── backup
    ├── list
    ├── create
    ├── download
    ├── restore
    ├── remove
    ├── export
    ├── import
    └── validate
```

### 2. REST Tree (`openapi/opal_think.yaml`)

```text
/api/v1
├── /task/                                  GET, POST
│   └── /{task_id}                          GET
│       ├── /stream                         GET (SSE)
│       └── /cancel                         POST
├── /session/                               GET, POST
│   └── /{session_id}                       GET, DELETE
├── /model/                                 GET
│   └── /{model_id}                         GET
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
├── /info/                                  GET
│   └── /ping                               GET
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
└── /backup
    ├── /list                               GET
    ├── /create                             POST
    ├── /download/{filename}                GET
    ├── /restore/{filename}                 POST
    ├── /{filename}                         DELETE
    ├── /export                             GET
    ├── /import                             POST
    └── /validate                           POST
```

### 3. Command Reference

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal think ask` | `<prompt>`, `--model ID`, `--context JSON`, `--max-steps INT`, `--timeout-seconds INT`, `--no-stream` | Shortcut for `task create` + `task watch`: submit a stateless prompt and print the answer (`POST /api/v1/task/`). |
| `opal think chat` | `<prompt>`, `--session ID`, `--title TEXT`, `--model ID`, `--context JSON` | Shortcut for session-bound turns: create or reuse a session and run a task (`POST /api/v1/session/` + `POST /api/v1/task/`). |
| `opal think task create` | `--prompt TEXT`, `--session ID`, `--model ID`, `--context JSON`, `--max-steps INT`, `--timeout-seconds INT`, `--metadata JSON`, `--idempotency-key KEY` | Submit an asynchronous reasoning task (`POST /api/v1/task/`). |
| `opal think task list` | `--status STATE`, `--session ID`, `--limit INT` | List retained tasks in deterministic newest-first order (`GET /api/v1/task/`). |
| `opal think task show` | `<task_id>` | Fetch the authoritative snapshot of a task (`GET /api/v1/task/{task_id}`). |
| `opal think task watch` | `<task_id>`, `--last-event-id ID` | Follow a task's live SSE token and progress stream (`GET /api/v1/task/{task_id}/stream`). |
| `opal think task cancel` | `<task_id>` | Request cooperative cancellation of a queued or running task (`POST /api/v1/task/{task_id}/cancel`). |
| `opal think session add` | `--title TEXT` | Create a multi-turn conversation session (`POST /api/v1/session/`). |
| `opal think session list` | `--limit INT` | List conversation sessions (`GET /api/v1/session/`). |
| `opal think session show` | `<session_id>` | Inspect a session and its associated tasks (`GET /api/v1/session/{session_id}`). |
| `opal think session remove` | `<session_id>` | Delete a conversation session (`DELETE /api/v1/session/{session_id}`). |
| `opal think model list` | `--json` | List available LLM models across configured providers (`GET /api/v1/model/`). |
| `opal think model show` | `<model_id>` | Show capabilities (`streaming`, `tool_calling`, `vision`) for one model (`GET /api/v1/model/{model_id}`). |
| `opal think config persona list\|add\|show\|update\|remove\|validate` | `<persona_id>`, `--persona-id ID`, `--name TEXT`, `--voice ID`, `--description TEXT`, `--enabled/--disabled` | Authoritative suite persona CRUD (`origin: local`) (`/api/v1/persona/*`). |
| `opal think config profile list\|add\|show\|update\|remove\|activate` | `<profile_id>`, `--name TEXT`, `--description TEXT`, `--active/--inactive` | Manage Think preset profiles (`/api/v1/profile/*`). |
| `opal think config setting list\|update\|show\|set\|remove` | `<key>`, `<value_json>`, `--data JSON` | Manage Think runtime settings (`models.default_id`, provider URLs, etc.) (`/api/v1/setting/*`). |
| `opal think service start\|stop\|log` | `--append BOOL` | Control the Think daemon process (`/api/v1/service/*`). |
| `opal think info health\|version\|ping\|live\|ready` | `--json` | Health, provider readiness, and version probes (`/api/v1/health/*`, `/api/v1/info/*`). |
| `opal think backup list\|create\|download\|restore\|remove\|export\|import\|validate` | `<filename>`, `--file PATH`, `--out PATH` | Backup and restore Think configuration (`/api/v1/backup/*`). |

---

## INTERFACE: `opal-event`

*The suite's nervous system: ZeroMQ + HTTP event publishing, wildcard topic routing, condition evaluation, and guarded shell/HTTP/Python action execution.*

### 1. Typer Command Tree

```text
opal event
├── publish                 publish an event to the bus and rule engine (202 Accepted)
├── topic
│   └── list                list observed topics and event counts
├── action
│   └── execute             synchronously validate input and trigger an action
├── history                 stored event log (legacy aliases under data event)
│   ├── list
│   ├── show
│   ├── remove
│   ├── clear
│   └── topics
├── config
│   ├── rule                list | add | show | update | remove | test
│   ├── action              list | add | show | update | remove
│   ├── profile             list | add | show | update | remove | activate
│   ├── persona             list | add | show | update | remove | validate
│   └── setting             list | update | show | set | remove
├── data
│   ├── event               list | show | remove | clear
│   └── execution           list | show
├── service
│   ├── start
│   ├── stop
│   └── log
├── info
│   ├── health
│   ├── stats
│   ├── version
│   ├── ping
│   ├── live
│   └── ready
└── backup
    ├── list
    ├── create
    ├── download
    ├── restore
    ├── remove
    ├── export
    ├── import
    └── validate
```

### 2. REST Tree (`openapi/opal_event.yaml`)

```text
/api/v1
├── /event/                                 GET, POST, DELETE
│   └── /{event_id}                         GET, DELETE
├── /topic/                                 GET
├── /rule/                                  GET, POST
│   └── /{rule_id}                          GET, PATCH, DELETE
│       └── /test                           POST
├── /action/                                GET, POST
│   └── /{action_id}                        GET, PATCH, DELETE
│       └── /execute                        POST
├── /execution/                             GET
│   └── /{execution_id}                     GET
├── /stats/                                 GET
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
├── /info/                                  GET
│   └── /ping                               GET
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
└── /backup
    ├── /list                               GET
    ├── /create                             POST
    ├── /download/{filename}                GET
    ├── /restore/{filename}                 POST
    ├── /{filename}                         DELETE
    ├── /export                             GET
    ├── /import                             POST
    └── /validate                           POST
```

### 3. Command Reference

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal event publish` | `--topic TOPIC`, `--data JSON`, `--source TEXT`, `--id ID`, `--timestamp ISO` | Publish an event into the store and rule engine (`POST /api/v1/event/`). |
| `opal event history list` | `--topic TOPIC`, `--source TEXT`, `--from ISO`, `--to ISO`, `--limit INT` | List stored events (bounded array, newest first) (`GET /api/v1/event/`). |
| `opal event history show` | `<event_id>` | Inspect a single stored event (`GET /api/v1/event/{event_id}`). |
| `opal event history remove` | `<event_id>` | Delete one stored event (`DELETE /api/v1/event/{event_id}`). |
| `opal event history clear` | `--yes` | Purge all stored events (`DELETE /api/v1/event/`). |
| `opal event topic list` | `--json` | List observed event topics and counts (`GET /api/v1/topic/`). |
| `opal event config rule list\|add\|show\|update\|remove` | `<rule_id>`, `--id ID`, `--topic PATTERN`, `--conditions JSON`, `--actions JSON`, `--enabled/--disabled` | Manage topic-matching rules (`*` and `#` wildcards supported) (`/api/v1/rule/*`). |
| `opal event config rule test` | `<rule_id>`, `--event JSON` | Dry-run an event payload against a rule without firing actions (`POST /api/v1/rule/{rule_id}/test`). |
| `opal event config action list\|add\|show\|update\|remove` | `<action_id>`, `--id ID`, `--type [shell\|http\|python]`, `--mode [exec\|bash]`, `--executable PATH`, `--script-path PATH`, `--args JSON`, `--method HTTP`, `--url URL`, `--body-mode MODE`, `--module MOD`, `--function FN`, `--input-schema JSON`, `--timeout-seconds FLOAT`, `--description TEXT`, `--keywords JSON` | Register and manage shell, HTTP, or Python actions (`/api/v1/action/*`). |
| `opal event action execute` | `<action_id>`, `--event JSON` | Manually fire an action (validates `input_schema` synchronously; returns `422` on mismatch, `202` on admission) (`POST /api/v1/action/{action_id}/execute`). |
| `opal event data execution list\|show` | `<execution_id>`, `--status [queued\|running\|succeeded\|failed\|timed_out\|dropped]`, `--rule-id ID`, `--action-id ID`, `--event-id ID`, `--limit INT` | Inspect action execution records and error codes (`GET /api/v1/execution/*`). |
| `opal event config profile\|persona\|setting ...` | Standard suite options | Manage Event profiles, personas, and settings (`/api/v1/profile/*`, `/persona/*`, `/setting/*`). |
| `opal event info health\|stats\|version\|ping\|live\|ready` | `--json` | Inspect service health and event/execution counters (`GET /api/v1/stats/`, `/api/v1/health/*`). |
| `opal event service start\|stop\|log` | `--append BOOL` | Control the Event daemon process (`/api/v1/service/*`). |
| `opal event backup list\|create\|download\|restore\|remove\|export\|import\|validate` | `<filename>`, `--file PATH`, `--out PATH` | Backup and restore rules, actions, and settings (`/api/v1/backup/*`). |

---

## USECASES

Ten single-service recipes per service. No `jq` gymnastics, no bash loops—just the Typer CLI doing its day job.

### `opal-say`

**1. Cut a museum audio-guide track at 0.9x speed so visitors can actually absorb the dates.**

```bash
opal say generate \
  --text "To your left stands a 14th-century astrolabe, used by sailors who refused to ask for directions." \
  --voice en-gb-alan-low --speed 0.9 --output-format wav --out room3-astrolabe.wav
```

**2. Stream a progressive raw PCM boarding announcement straight to a PA pipe (`--stream` on `generate`).**

```bash
opal say generate \
  --text "Final boarding call for flight 404 to Nowhere. Gate closes in ninety seconds." \
  --stream --sample-rate 22050 --out boarding-404.pcm
```

**3. Register a Japanese Kokoro voice model that already lives on disk and verify the engine accepts it.**

```bash
opal say config voice add \
  --voice-id ja-jp-kokoro-alpha \
  --name "Kokoro Alpha (JP)" \
  --engine kokoro \
  --engine-voice-ref /opt/models/kokoro/ja_alpha.pt \
  --language ja-JP
opal say config voice validate ja-jp-kokoro-alpha
```

**4. Audition a newly registered voice with a pangram before letting it near production.**

```bash
opal say config voice test ja-jp-kokoro-alpha \
  --text "Sphinx of black quartz, judge my vow." \
  --speed 1.05 --volume 1.0 --output-format wav --out audition-kokoro.wav
```

**5. Create a "Midnight Whisper" preset profile for late-night notifications and make it the active default.**

```bash
opal say config profile add \
  --name midnight-whisper \
  --description "Low volume, unhurried cadence for after-hours alerts" \
  --voice en-us-lessac-medium --speed 0.82 --volume 0.35 --output-format wav
opal say config profile activate 2
```

**6. Demonstrate the three-tier voice precedence: active profile vs. named persona vs. explicit `--voice` override.**

```bash
# 1. Uses the active profile's voice (en-us-lessac-medium):
opal say generate --text "Spoken in the active profile voice." --out tier1-profile.wav

# 2. Persona 'duchess' overrides the active profile with her bound voice:
opal say config persona add --persona-id duchess --name "The Duchess" --voice en-gb-alan-low
opal say generate --text "Spoken in the Duchess persona voice." --persona duchess --out tier2-persona.wav

# 3. Explicit --voice overrides both the persona and the profile:
opal say generate --text "Explicit voice wins every argument." \
  --persona duchess --voice en-us-ryan-high --out tier3-explicit.wav
```

**7. Disable a misbehaving synthesis engine without uninstalling it, then verify the remaining engines.**

```bash
opal say engine update espeak --disabled
opal say engine list
```

**8. Batch-tune runtime limits in one atomic `If-Match` patch using `config setting update`.**

```bash
opal say config setting update \
  --data '{"max_text_length": 8192, "default_sample_rate": 24000}'
opal say config setting list
```

**9. Point Say at OPAL Think as its authoritative persona owner so unknown personas are fetched on demand.**

```bash
opal say config setting set persona_owner_url '"http://127.0.0.1:8084"'
opal say config setting show persona_owner_url
```

**10. Export the entire voice, profile, and persona catalog, validate the bundle offline, and create a timestamped server snapshot.**

```bash
opal say backup export --out say-studio-bundle.json
opal say backup validate --file say-studio-bundle.json
opal say backup create
```

---

### `opal-listen`

**1. Enumerate every microphone attached to the host before blaming the STT engine for deafness.**

```bash
opal listen info audio-devices
```

**2. Register a custom wakeword with a strict confidence floor so the TV stops triggering the house.**

```bash
opal listen config wakeword add --name "brigadier" --confidence-threshold 0.88 --enabled
opal listen config wakeword list
```

**3. Create an espresso-barista intent with initial training phrases.**

```bash
opal listen config intent add \
  --name barista.brew \
  --description "Start pulling an espresso shot" \
  --confidence-threshold 0.75 \
  --phrase "pull a shot of [drink]" \
  --phrase "make me a [drink]" \
  --phrase "brew an [drink] please"
```

**4. Build a `drink` slot with canonical values and regional spoken aliases.**

```bash
opal listen config slot add --name drink --slot-type list --description "Coffee bar menu items"
opal listen config slot value add 1 --value americano
opal listen config slot value add 1 --value cortado
opal listen config slot alias add 1 1 --alias "long black"
opal listen config slot alias add 1 2 --alias "gibraltar"
```

**5. Use the unified `recognition test` command to dry-run text and assert the matched intent in one step.**

```bash
opal listen recognition test \
  --text "brigadier, make me a gibraltar" \
  --expect-intent barista.brew --no-save --verbose
```

**6. Dry-run a noisy kitchen WAV recording through wakeword + STT + NLU requiring the wakeword to be present.**

```bash
opal listen recognition test \
  --audio ./fixtures/noisy-kitchen-cortado.wav \
  --require-wakeword --expect-intent barista.brew
```

**7. Inspect the failed-utterance queue, annotate a misunderstood mumble, and promote it straight into both a training phrase and a regression test.**

```bash
opal listen data failed-utterance list --reviewed false --limit 10
opal listen data failed-utterance update 12 \
  --expected-intent barista.brew --notes "User had a croissant in their mouth" --reviewed true
opal listen data failed-utterance promote 12 \
  --intent-name barista.brew --create-regression true
```

**8. Add an explicit slot-checking regression case and run the full regression suite.**

```bash
opal listen regression add \
  --name "gibraltar alias resolves to cortado" \
  --phrase "make me a gibraltar" \
  --expected-intent barista.brew \
  --expected-slots '{"drink": "cortado"}'
opal listen regression run --enabled-only true
```

**9. Create a "Workshop Mode" recognition profile that only listens for safety-cutoff intents and activate it.**

```bash
opal listen config profile add \
  --name workshop-safety \
  --description "High noise floor; only emergency and tool intents active" \
  --wakeword-names '["brigadier"]' \
  --enabled-intents '["shop.emergency_stop", "shop.dust_collector_on"]'
opal listen config profile activate 3
```

**10. Audit recognition latency across the last 25 utterances to see whether VAD or STT is eating the budget.**

```bash
opal listen performance last
opal listen performance summary --limit 25
opal listen performance history --limit 25
```

---

### `opal-look`

**1. Query runtime capabilities to verify whether hardware-accelerated ONNX and annotated video export are supported on this host.**

```bash
opal look info capabilities
```

**2. Register a wildlife-detection model and an RTSP bird-feeder camera with credentials resolved from an environment secret ref.**

```bash
opal look config model add \
  --id yolov8-avian \
  --engine onnx \
  --resource-ref /opt/models/yolov8-birds.onnx \
  --tasks '["detect"]'
opal look source add \
  --id cam-feeder \
  --kind rtsp \
  --name "South Bird Feeder" \
  --locator rtsp://10.0.20.14:554/h264Preview_01_main \
  --secret-ref feeder-cam-auth
opal look source probe cam-feeder
```

**3. Validate a three-stage preprocess → inference → annotate DAG pipeline before saving it.**

```bash
opal look config pipeline validate \
  --id avian-tracker \
  --name "Feeder Species Tracker" \
  --stages '[
    {"id":"prep","kind":"preprocess","options":{"resize":[640,640]}},
    {"id":"detect","kind":"inference","model_id":"yolov8-avian","task":"detect","inputs":["prep"]},
    {"id":"overlay","kind":"annotate","inputs":["detect"]}
  ]'
opal look config pipeline add \
  --id avian-tracker \
  --name "Feeder Species Tracker" \
  --stages '[
    {"id":"prep","kind":"preprocess","options":{"resize":[640,640]}},
    {"id":"detect","kind":"inference","model_id":"yolov8-avian","task":"detect","inputs":["prep"]},
    {"id":"overlay","kind":"annotate","inputs":["detect"]}
  ]'
```

**4. Take an exact retained frame capture and fetch its JPEG bytes using the unified `output fetch` command.**

```bash
opal look source capture cam-feeder --retain --annotate
# Response includes: "output_ref": {"kind": "capture", "id": "cap-8f2d41a0", "content_url": "/api/v1/capture/cap-8f2d41a0/content"}
opal look output fetch /api/v1/capture/cap-8f2d41a0/content --out cardinal-annotated.jpg
```

**5. Draw a polygon zone around the suet cage and trigger a rule whenever a squirrel lingers for more than 4 seconds.**

```bash
opal look config zone add \
  --id zone-suet \
  --source cam-feeder \
  --name "Suet Cage Perimeter" \
  --kind polygon \
  --points '[[0.30,0.20],[0.70,0.20],[0.70,0.85],[0.30,0.85]]'
opal look config rule add \
  --id squirrel-heist \
  --name "Squirrel lingered on suet cage" \
  --source cam-feeder \
  --zone zone-suet \
  --kind dwell_time \
  --class-filters '["squirrel"]' \
  --minimum-duration-ms 4000 \
  --cooldown-ms 30000 \
  --capture-on-match --clip-on-match
```

**6. Launch a self-healing monitor so Look restarts the camera session automatically if the Wi-Fi hiccups.**

```bash
opal look config monitor add \
  --id mon-feeder \
  --name "24x7 Feeder Watch" \
  --source cam-feeder \
  --pipeline avian-tracker \
  --restart-policy always --enabled
opal look config monitor show mon-feeder
```

**7. Record a 60-second clip of the feeder, stop it early, and download the finalized artifact via its `artifact_ref`.**

```bash
opal look data recording start --source cam-feeder --max-duration-seconds 60
opal look data recording stop rec-51c2
# Response includes: "artifact_ref": {"kind": "artifact", "id": "art-rec-51c2", "content_url": "/api/v1/artifact/art-rec-51c2/content"}
opal look output fetch /api/v1/artifact/art-rec-51c2/content --out squirrel-evidence.mjpeg
```

**8. Upload a dashcam still, run an asynchronous clip-export job, and retrieve the exported artifact via `output_refs`.**

```bash
opal look data media upload ./dashcam/meteor-shower.jpg
opal look data job submit --kind clip_export --source cam-feeder
opal look data job show job-9a3f
# Response includes: "output_refs": [{"kind": "artifact", "id": "art-job-9a3f-clip", "content_url": "/api/v1/artifact/art-job-9a3f-clip/content"}]
opal look output fetch /api/v1/artifact/art-job-9a3f-clip/content --out meteor-export.mp4
```

**9. Query retained observations filtered by label and time window.**

```bash
opal look data observation list \
  --source cam-feeder \
  --label pileated_woodpecker \
  --after 2026-04-01T06:00:00Z \
  --before 2026-04-01T18:00:00Z \
  --limit 25
```

**10. Inspect pipeline frame-drop telemetry and ZeroMQ event-publisher health.**

```bash
opal look info metrics
opal look info events
```

---

### `opal-think`

**1. Discover which provider models support vision and tool calling before dispatching a task.**

```bash
opal think model list
opal think model show ollama:llava-llama3
```

**2. Author a suite-wide portable persona in Think (the authoritative registry, `origin: local`).**

```bash
opal think config persona add \
  --persona-id sherlock \
  --name "Consulting Detective" \
  --voice en-gb-alan-low \
  --description "Deductive, concise, mildly exasperated by obvious questions"
opal think config persona validate sherlock
```

**3. Ask a one-shot question using the `ask` shortcut (creates a task and streams the response to stdout).**

```bash
opal think ask "Why do mirrors flip left-to-right instead of top-to-bottom? Explain in two sentences."
```

**4. Submit a bounded asynchronous task with untrusted structured `--context` and an idempotency key.**

```bash
opal think task create \
  --prompt "Summarize the anomalous readings and rank their severity." \
  --model ollama:llama3.2 \
  --context '{"sensor":"kiln-thermocouple-2","readings_c":[1020,1024,1198,1245],"limit_c":1150}' \
  --max-steps 4 \
  --timeout-seconds 60 \
  --idempotency-key kiln-check-2026-04-19-01
```

**5. Follow a running task's token stream over SSE, then inspect its final persisted snapshot.**

```bash
opal think task watch task-7c91e0
opal think task show task-7c91e0
```

**6. Cancel a runaway philosophical task before it heats the garage.**

```bash
opal think task cancel task-7c91e0
opal think task list --status cancelled --limit 5
```

**7. Start a multi-turn architecture review session and run two sequential turns inside it.**

```bash
opal think session add --title "Greenhouse Irrigation Redesign"
opal think chat --session sess-402 \
  "We have 4 zones and a 12L/min pump. Each dripper line takes 5L/min. How many zones can run at once?"
opal think chat --session sess-402 \
  "If we add a rainwater barrel booster adding 4L/min, how does the schedule change?"
opal think session show sess-402
```

**8. Switch Think's default model and temperature via the standardized `config setting` commands.**

```bash
opal think config setting set models.default_id '"ollama:qwen2.5:14b"'
opal think config setting update --data '{"inference.default_temperature": 0.2}'
opal think config setting list
```

**9. Create and activate a "Strict JSON Grader" profile for deterministic evaluation workloads.**

```bash
opal think config profile add \
  --name strict-grader \
  --description "Low temperature, concise analytical defaults"
opal think config profile activate 1
```

**10. Prune finished brainstorming sessions and snapshot Think's configuration.**

```bash
opal think session list --limit 10
opal think session remove sess-402
opal think backup create
```

---

### `opal-event`

**1. Publish a custom smart-home telemetry event to the bus.**

```bash
opal event publish \
  --topic greenhouse.soil.moisture \
  --source esp32-bed-north \
  --data '{"bed":"tomatoes","moisture_pct":18.4,"temp_c":26.1}'
```

**2. Browse the stored event history and inspect observed topics without touching the publish path.**

```bash
opal event history list --topic greenhouse.soil.moisture --limit 10
opal event topic list
```

**3. Register an HTTP webhook action with templating and searchable discovery metadata.**

```bash
opal event config action add \
  --id open_irrigation_valve \
  --type http \
  --method POST \
  --url http://10.0.10.50:8080/valve/north/open \
  --body-mode template \
  --body '{"duration_sec": 300, "reason": "moisture={{data.moisture_pct}}"}' \
  --timeout-seconds 10 \
  --description "Open the north greenhouse solenoid valve for 5 minutes" \
  --keywords '["greenhouse","irrigation","valve"]'
```

**4. Lock down the action with a JSON Schema `input_schema` so malformed payloads are rejected before execution.**

```bash
opal event config action update open_irrigation_valve \
  --input-schema '{
    "type": "object",
    "required": ["bed", "moisture_pct"],
    "properties": {
      "bed": {"type": "string"},
      "moisture_pct": {"type": "number", "minimum": 0, "maximum": 100}
    }
  }'
```

**5. Register a direct `exec`-mode shell action (no shell interpolation) for local LED strip signalling.**

```bash
opal event config action add \
  --id flash_status_led \
  --type shell \
  --mode exec \
  --executable /usr/local/bin/ledctl \
  --args '["--color", "amber", "--pulses", "3"]' \
  --timeout-seconds 5 \
  --description "Pulse the hallway status LED amber three times"
```

**6. Register an in-process Python action for ledger logging.**

```bash
opal event config action add \
  --id log_watering_audit \
  --type python \
  --module greenhouse_ops.audit \
  --function record_irrigation_cycle \
  --timeout-seconds 15
```

**7. Wire a wildcard rule that triggers all three actions when soil moisture drops below 22%.**

```bash
opal event config rule add \
  --id dry_tomato_bed \
  --topic 'greenhouse.soil.*' \
  --conditions '[
    {"path": "data.bed", "operator": "eq", "value": "tomatoes"},
    {"path": "data.moisture_pct", "operator": "lt", "value": 22}
  ]' \
  --actions '["open_irrigation_valve", "flash_status_led", "log_watering_audit"]' \
  --enabled
```

**8. Dry-run the rule with `config rule test` to verify condition matching without opening a single water valve.**

```bash
opal event config rule test dry_tomato_bed \
  --event '{"topic":"greenhouse.soil.moisture","data":{"bed":"tomatoes","moisture_pct":17.9}}'
```

**9. Manually execute the action with both a valid payload (`202 Accepted`) and a schema-violating payload (`422` synchronous rejection), then check the execution log.**

```bash
opal event action execute open_irrigation_valve \
  --event '{"topic":"manual.drill","data":{"bed":"tomatoes","moisture_pct":19.0}}'
opal event data execution list --action-id open_irrigation_valve --limit 5
```

**10. Inspect bus throughput statistics and clear stale test events from history.**

```bash
opal event info stats
opal event history remove evt-0192a
```

---

## COMBINED: 50 Multi-Service Recipes

Fifty ways to wire `say`, `listen`, `look`, `think`, and `event` into an unreasonably capable organism.

---

### I. The Persona & Voice Testing Foundry (`think` + `say` + `listen`)

#### 1. Generate the Same Phrase Across Every Registered Persona to Stress-Test Intent Recognition
Author three distinct personas in `think` (the authoritative owner), let `say` synthesize the exact same command in each persona's bound voice, and feed every WAV into `listen` to prove your NLU handles all of them.

```bash
# 1. Define personas in Think (authoritative owner):
opal think config persona add --persona-id butler --name "Jeeves" --voice en-gb-alan-low
opal think config persona add --persona-id dispatcher --name "Dispatch" --voice en-us-lessac-medium
opal think config persona add --persona-id captain --name "Captain" --voice en-us-ryan-high

# 2. Generate the identical utterance in each persona's voice:
opal say generate --text "arm the perimeter floodlights" --persona butler --out test-butler.wav
opal say generate --text "arm the perimeter floodlights" --persona dispatcher --out test-dispatcher.wav
opal say generate --text "arm the perimeter floodlights" --persona captain --out test-captain.wav

# 3. Verify Listen matches the exact same intent for all three voices:
opal listen recognition test --audio test-butler.wav --expect-intent security.floodlights_on
opal listen recognition test --audio test-dispatcher.wav --expect-intent security.floodlights_on
opal listen recognition test --audio test-captain.wav --expect-intent security.floodlights_on
```

#### 2. Speed-Sweep Torture Test for Wakeword + STT
Synthesize a wakeword command at 0.75x, 1.0x, and 1.5x speed and verify where STT recognition starts to crack.

```bash
opal say generate --text "brigadier, make me a cortado" --speed 0.75 --out slow.wav
opal say generate --text "brigadier, make me a cortado" --speed 1.00 --out normal.wav
opal say generate --text "brigadier, make me a cortado" --speed 1.50 --out caffeinated.wav
opal listen recognition test --audio slow.wav --require-wakeword --expect-intent barista.brew
opal listen recognition test --audio normal.wav --require-wakeword --expect-intent barista.brew
opal listen recognition test --audio caffeinated.wav --require-wakeword --expect-intent barista.brew
```

#### 3. Homophone & Accent Trap Generator
Ask `think` to invent tricky homophone sentences for a target intent, synthesize them with `say`, and test them in `listen`.

```bash
opal think ask "Write one spoken command to turn on the 'flour mill' that sounds nearly identical to 'flower mill'."
opal say generate --text "brigadier, start the flour mill" --persona butler --out homophone.wav
opal listen recognition test --audio homophone.wav --verbose
```

#### 4. Automated Miss-to-Regression Promotion Loop
When a synthetic persona recording fails recognition, promote the logged failed utterance directly into the intent's training phrases and regression suite, then re-test.

```bash
opal listen data failed-utterance list --reviewed false --limit 5
opal listen data failed-utterance promote 19 --intent-name security.floodlights_on --create-regression true
opal listen regression run
opal listen recognition test --audio test-captain.wav --expect-intent security.floodlights_on
```

#### 5. Multilingual Voice & Intent Handshake
Register a Spanish intent in `listen`, synthesize a test phrase through a Spanish voice in `say`, and verify round-trip recognition.

```bash
opal listen config intent add --name luces.encender --phrase "enciende las luces del salón"
opal say generate --text "enciende las luces del salón" --voice es-es-carlfm-high --out salon.wav
opal listen recognition test --audio salon.wav --expect-intent luces.encender
```

---

### II. Perimeter & Property Guardians (`look` + `event` + `say` + `think`)

#### 6. Verbally Notify Me When Someone Is in My Front Yard
Define a polygon zone on the front-yard camera, arm an `enters_zone` rule in `look`, and wire an `event` rule that calls `say` to announce the visitor out loud.

```bash
# 1. Fence the front yard and arm the visual rule in Look:
opal look config zone add --id front-yard --source cam-front --name "Front Yard" \
  --kind polygon --points '[[0.10,0.40],[0.90,0.40],[0.95,0.98],[0.05,0.98]]'
opal look config rule add --id person-in-front-yard --name "Person in Front Yard" \
  --source cam-front --zone front-yard --kind enters_zone \
  --class-filters '["person"]' --cooldown-ms 45000 --capture-on-match --enabled

# 2. Register an HTTP action in Event that triggers OPAL Say:
opal event config action add --id speak_front_yard_alert --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Heads up: someone just stepped into the front yard.","persona":"butler","output_format":"wav"}'

# 3. Connect Look's rule-match event topic to the spoken alert:
opal event config rule add --id notify_front_yard_person \
  --topic 'opal.look.rule.matched' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"person-in-front-yard"}]' \
  --actions '["speak_front_yard_alert"]' --enabled
```

#### 7. Porch Pirate Deterrent with Live Recording & Polite British Warning
When a person lingers near a detected package on the porch, start a 90-second recording in `look` and have `say` broadcast a polite warning that the camera is recording.

```bash
opal look config rule add --id porch-linger --name "Lingering near porch" \
  --source cam-porch --zone zone-mat --kind dwell_time \
  --class-filters '["person"]' --minimum-duration-ms 8000 --capture-on-match
opal event config action add --id start_porch_recording --type http \
  --method POST --url http://127.0.0.1:8082/api/v1/recording/ \
  --body-mode template --body '{"source_id":"cam-porch","max_duration_seconds":90}'
opal event config action add --id polite_deterrent --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Good afternoon. The porch camera is recording in high definition. Do smile.","persona":"butler"}'
opal event config rule add --id porch_defense --topic 'opal.look.rule.matched' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"porch-linger"}]' \
  --actions '["start_porch_recording","polite_deterrent"]' --enabled
```

#### 8. Driveway Vehicle Arrival & License-Plate Frame Capture
Cross a driveway tripwire line with a `car` or `truck`, snap an exact retained capture, and fetch the image via `output fetch`.

```bash
opal look config zone add --id driveway-gate --source cam-driveway --name "Gate Line" \
  --kind line --points '[[0.15,0.65],[0.85,0.65]]'
opal look config rule add --id vehicle-arrived --name "Vehicle crossed gate" \
  --source cam-driveway --zone driveway-gate --kind line_crosses \
  --class-filters '["car","truck"]' --capture-on-match
opal look data capture list --limit 1
opal look output fetch /api/v1/capture/cap-0042a/content --out driveway-arrival.jpg
```

#### 9. Dog-on-the-Couch Scolder
Monitor the living room couch polygon for `dog` detections while nobody is home and have the owner's persona firmly tell Barnaby to get down.

```bash
opal look config zone add --id zone-sofa --source cam-living --name "Forbidden Sofa" \
  --kind polygon --points '[[0.22,0.50],[0.78,0.50],[0.78,0.88],[0.22,0.88]]'
opal look config rule add --id dog-on-sofa --name "Barnaby on the sofa" \
  --source cam-living --zone zone-sofa --kind enters_zone \
  --class-filters '["dog"]' --cooldown-ms 20000 --capture-on-match
opal event config action add --id scold_barnaby --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Barnaby. Off the couch immediately. We have photographic evidence.","volume":1.3}'
opal event config rule add --id sofa_enforcement --topic 'opal.look.rule.matched' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"dog-on-sofa"}]' \
  --actions '["scold_barnaby"]' --enabled
```

#### 10. End-of-Day Security Digest (Observations → Think Summary → Spoken Briefing)
Query today's perimeter observations from `look`, pass them as structured context to `think` for a two-sentence executive briefing, and render the audio with `say`.

```bash
opal look data observation list --source cam-front --after 2026-04-19T00:00:00Z --limit 50
opal think ask "Summarize today's front camera activity in two calm sentences for the homeowner." \
  --context '{"observations":[{"time":"08:14","label":"person","note":"mail carrier"},{"time":"14:02","label":"squirrel","count":3},{"time":"17:45","label":"car","note":"family return"}]}'
opal say generate \
  --text "All quiet on the front perimeter today: the mail carrier visited at 8:14 AM, three squirrels held a brief summit at 2:02 PM, and the family car returned at 5:45 PM." \
  --persona butler --out evening-security-brief.wav
```

---

### III. The Academy: Quizzes, Math, Facts & Storytelling (`think` + `say` + `listen` + `event`)

#### 11. Verbal Quizzes: Pub Trivia Host That Speaks Questions & Grades Spoken Answers
Start a trivia session in `think`, read the question out loud with `say`, capture the player's spoken answer in `listen`, and have `think` score the round.

```bash
# 1. Start a trivia session and generate Round 1:
opal think session add --title "Friday Night Pub Trivia"
opal think chat --session sess-trivia-1 \
  "You are a witty pub quizmaster. Ask Question 1 (science, medium difficulty) in one sentence. Do not reveal the answer yet."

# 2. Speak the question to the room:
opal say generate \
  --text "Question one: Which chemical element, named after the Greek word for 'stranger', is used in high-intensity arc lamps and ion thrusters?" \
  --persona butler --out trivia-q1.wav

# 3. Player answers into the microphone (or WAV test); Listen matches the answer intent:
opal listen recognition test --text "is it xenon" --verbose

# 4. Think grades the response inside the same session and Say announces the score:
opal think chat --session sess-trivia-1 "The contestant answered 'xenon'. Grade it and give the score (1/1)."
opal say generate \
  --text "Spot on! Xenon it is—one point on the board." \
  --persona butler --out trivia-verdict1.wav
```

#### 12. Mental Math Questions with Progressive Difficulty
Have `think` generate a timed arithmetic challenge, read it aloud via `say`, parse the spoken number in `listen`, and verify the calculation.

```bash
opal think ask "Give me one mental-math word problem involving two-digit multiplication, phrased for spoken delivery in one sentence."
opal say generate \
  --text "If a baker puts fourteen croissants on each of six trays, and eats three for quality control, how many croissants remain?" \
  --persona dispatcher --speed 0.95 --out math-q1.wav
opal listen recognition test --text "eighty one"
opal think ask "Problem: 14 * 6 - 3. User answered 'eighty one'. State whether they are right and show the quick mental shortcut."
opal say generate \
  --text "Correct! Six times ten is sixty, six times four is twenty-four for eighty-four, minus three leaves eighty-one." \
  --persona dispatcher --out math-a1.wav
```

#### 13. Random Facts Dispenser ("Tell Me Something Weird")
Voice trigger `"tell me a random fact"` fires a `think` prompt for an obscure, verifiable fact and streams the spoken audio via `say`.

```bash
opal listen config intent add --name curiosity.random_fact \
  --phrase "tell me a random fact" \
  --phrase "hit me with a weird fact" \
  --phrase "teach me something useless"
opal listen recognition test --text "tell me a random fact" --expect-intent curiosity.random_fact
opal think ask "Share one surprising, verifiable historical or scientific fact in under 35 words."
opal say stream \
  --text "Oxford University is older than the Aztec Empire: teaching started at Oxford around 1096, while Tenochtitlan was founded in 1325." \
  --persona butler --sample-rate 22050 --out weird-fact.pcm
```

#### 14. "Make Up a Story About..." Interactive Bedtime Storyteller
Capture a child's (or sleep-deprived engineer's) spoken topic via `listen`, spin a bespoke story in `think`, and narrate it softly using a slow-cadence `say` profile.

```bash
# 1. Match the spoken story request and extract slots:
opal listen config slot add --name protagonist --slot-type freeform
opal listen config intent add --name story.tell \
  --phrase "make up a story about [protagonist]" \
  --phrase "tell me a bedtime story about [protagonist]"
opal listen recognition test \
  --text "make up a story about a nearsighted lighthouse keeper and a polite kraken" \
  --expect-intent story.tell

# 2. Think writes the story:
opal think ask \
  "Make up a cozy 4-sentence bedtime story about a nearsighted lighthouse keeper and a polite kraken who returns lost rowboats."

# 3. Narrate at 0.85x speed with the midnight-whisper profile:
opal say generate \
  --text "Every fog-bound Tuesday, Barnaby polished his lighthouse lens with the wrong spectacles and mistook the kraken for a floating pier. The kraken, too well-mannered to correct him, simply handed up three lost oars and a lobster pot with a gentle bow. Barnaby brewed a kettle of kelp tea and lowered a mug on a rope. By midnight, both the bay and the monster were fast asleep." \
  --profile 2 --persona butler --out lighthouse-kraken.wav
```

#### 15. Socratic Flashcard Drill for Medical / Aviation Exams
Load a deck topic into a `think` session, quiz the student aloud, and keep drilling missed cards until they pass.

```bash
opal think session add --title "FAA Private Pilot Weather Flashcards"
opal think chat --session sess-faa "Ask me one flashcard question about METAR cloud ceiling abbreviations."
opal say generate --text "In a METAR report, which two cloud coverage codes constitute a ceiling?" --out faa-card1.wav
opal listen recognition test --text "broken and overcast"
opal think chat --session sess-faa "Student answered 'broken and overcast' (BKN and OVC). Confirm and ask the next card."
```

#### 16. "Explain Like I'm Five" vs. "Explain Like I'm a Principal Engineer" Dual-Persona Debate
Have `think` answer the same question twice—once simply, once rigorously—and voice them with two contrasting personas in `say`.

```bash
opal think ask "Explain how a differential gear works in one sentence for a seven-year-old."
opal say generate \
  --text "When a car turns a corner, the outside wheel has to travel a longer path than the inside wheel, and the differential is the clever gear box that lets them spin at different speeds without skidding." \
  --persona dispatcher --out diff-eli5.wav

opal think ask "Explain a bevel-gear open automotive differential in one technical sentence."
opal say generate \
  --text "An open planetary bevel-gear differential splits input torque equally across both half-shafts while permitting differential angular velocity proportional to turn radius." \
  --persona butler --out diff-technical.wav
```

#### 17. Foreign-Language Pronunciation Coach
`say` models a Japanese phrase, the learner repeats it into a WAV file, `listen` transcribes what it heard, and `think` gives gentle phonetic coaching.

```bash
opal say generate --text "木漏れ日" --voice ja-jp-kokoro-alpha --speed 0.85 --out teacher-komorebi.wav
opal listen recognition test --audio ./student-attempt.wav --verbose
opal think ask "Target word: 'komorebi' (sunlight filtering through trees). Student transcript: 'komorabi'. Give a one-sentence pronunciation tip."
opal say generate --text "Almost there—keep the third syllable a crisp 'reh' as in 'red' rather than 'rah'." --persona butler --out coaching.wav
```

#### 18. Historical Roleplay Interview ("Press Conference with Ada Lovelace")
Bind a `think` session to a historical persona and conduct a two-way spoken interview.

```bash
opal think config persona add --persona-id lovelace --name "Ada Lovelace" --voice en-gb-alan-low \
  --description "Mathematician and author of Note G on the Analytical Engine, 1843"
opal think session add --title "Interview with Lady Lovelace"
opal think chat --session sess-ada \
  "In character as Ada Lovelace, answer in two sentences: can Mr. Babbage's Analytical Engine originate anything of its own?"
opal say generate \
  --text "The Analytical Engine has no pretensions whatever to originate anything. It can do whatever we know how to order it to perform, and no more." \
  --persona lovelace --out ada-reply.wav
```

#### 19. Geography Capital-City Lightning Round
Fire rapid-fire capital questions and log each round's score onto the `event` bus for leaderboard tracking.

```bash
opal think ask "Ask a lightning-round question: capital of Kazakhstan, one short sentence."
opal say generate --text "Lightning round: what is the capital city of Kazakhstan?" --speed 1.15 --out geo-q.wav
opal listen recognition test --text "astana"
opal event publish --topic quiz.geography.score --source quiz-host \
  --data '{"player":"alice","country":"Kazakhstan","answer":"Astana","correct":true,"time_ms":1840}'
```

#### 20. Choose-Your-Own-Adventure Audio Book
A `think` session tracks inventory and story state; `say` narrates each room; `listen` maps `"go north"` or `"open the brass chest"` to the next turn.

```bash
opal listen config intent add --name adventure.choice \
  --phrase "open the [object]" --phrase "take the [object]" --phrase "go [direction]"
opal think session add --title "The Clockwork Observatory"
opal think chat --session sess-cyoa \
  "Start an interactive audio adventure in an abandoned brass observatory. End with two clear choices."
opal say generate \
  --text "Rain drums against the cracked dome above the telescope. Before you sit a ticking astrolabe and a locked mahogany trapdoor. Do you examine the astrolabe, or force the trapdoor?" \
  --persona butler --out cyoa-turn1.wav
opal listen recognition test --text "open the trapdoor" --expect-intent adventure.choice
```

---

### IV. Workshop, Kitchen & Lab Assistants (`look` + `listen` + `think` + `say` + `event`)

#### 21. Hands-Full Soldering Bench Assistant ("Read Me That Resistor")
When both hands are holding a soldering iron and PCB, speak `"inspect the bench"`, snap a high-res frame in `look`, pass it to a vision-capable model in `think`, and hear the colour bands read aloud by `say`.

```bash
opal listen config intent add --name bench.inspect --phrase "inspect the bench" --phrase "read this component"
opal look source capture cam-bench-macro --retain
opal think ask "Read the four colour bands on the resistor in the center of the bench capture and state its resistance." \
  --model ollama:llava-llama3 \
  --context '{"capture_url":"/api/v1/capture/cap-bench-09/content","bands_observed":["brown","black","red","gold"]}'
opal say generate --text "Brown, black, red, gold: that is a one-kilohm resistor with five percent tolerance." \
  --persona dispatcher --out resistor.wav
```

#### 22. 3D-Printer Spaghetti & Nozzle-Blob Watchdog
`look` watches the printer bed for `spaghetti_defect`, publishes a match event, and `event` simultaneously cuts power to the smart plug and pages the workshop speaker via `say`.

```bash
opal look config model add --id fdm-defect-net --engine onnx \
  --resource-ref /opt/models/fdm-spaghetti.onnx --tasks '["detect"]'
opal look config rule add --id print-spaghetti --name "FDM Spaghetti Detected" \
  --source cam-voron --kind object_appears --class-filters '["spaghetti_defect"]' \
  --threshold 0.82 --capture-on-match
opal event config action add --id pause_klipper --type http \
  --method POST --url http://10.0.30.12:7125/printer/print/pause --body-mode none
opal event config action add --id announce_spaghetti --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Warning: Voron printer nozzle spaghetti detected. Print paused automatically.","persona":"dispatcher"}'
opal event config rule add --id stop_bad_print --topic 'opal.look.rule.matched' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"print-spaghetti"}]' \
  --actions '["pause_klipper","announce_spaghetti"]' --enabled
```

#### 23. Flour-Covered Hands Sourdough Timer & Hydration Calculator
Voice-commanded baker's percentage math and step readbacks without smearing dough on a touchscreen.

```bash
opal listen recognition test --text "brigadier, how much water for eight hundred grams of flour at seventy-eight percent hydration"
opal think ask "Compute 78% hydration water weight and 2% salt weight for 800g flour. Reply in one short spoken sentence."
opal say generate \
  --text "For eight hundred grams of flour at seventy-eight percent hydration, weigh out six hundred twenty-four grams of water and sixteen grams of salt." \
  --persona butler --out hydration.wav
```

#### 24. Stove-Burner Left On After Kitchen Vacated
`look` detects `stove_flame` inside the cooktop zone while zero `person` detections appear for 10 minutes; `event` triggers a high-volume spoken alert.

```bash
opal look config zone add --id zone-cooktop --source cam-kitchen --name "Cooktop" \
  --kind polygon --points '[[0.40,0.45],[0.65,0.45],[0.65,0.62],[0.40,0.62]]'
opal look config rule add --id unattended-burner --name "Burner on unattended" \
  --source cam-kitchen --zone zone-cooktop --kind dwell_time \
  --class-filters '["flame_on"]' --minimum-duration-ms 600000 --capture-on-match
opal event config action add --id kitchen_burner_siren --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Kitchen safety alert! A stove burner has been left on for ten minutes.","volume":1.8}'
opal event config rule add --id burner_safety_rule --topic 'opal.look.rule.matched' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"unattended-burner"}]' \
  --actions '["kitchen_burner_siren"]' --enabled
```

#### 25. Chemical Fume-Hood Sash Height Monitor
If a lab fume-hood sash stays above the safe mark in `look`, log an audit event in `event` and remind the researcher aloud via `say`.

```bash
opal look config zone add --id sash-high-line --source cam-lab2 --name "Max Safe Sash Height" \
  --kind line --points '[[0.20,0.35],[0.80,0.35]]'
opal look config rule add --id sash-too-high --name "Fume hood sash above safe line" \
  --source cam-lab2 --zone sash-high-line --kind line_crosses \
  --class-filters '["sash_handle"]' --cooldown-ms 15000
opal say generate --text "Lab two reminder: please lower the fume hood sash below the thirty-centimeter mark." \
  --persona dispatcher --out sash-warning.wav
```

---

### V. Studio, Podcast & Accessibility Workflows (`say` + `listen` + `think` + `look`)

#### 26. Two-Host Synthetic Morning Show From Server Logs
Feed overnight `event` stats and `look` metrics into `think` to script a 30-second banter segment between two personas, then synthesize both tracks with `say`.

```bash
opal event info stats
opal look info metrics
opal think ask "Write a two-line morning radio exchange between hosts 'Jeeves' and 'Dispatch' summarizing 1,420 processed events, 0 failed actions, and 12 nocturnal raccoon sightings."
opal say generate --text "Good morning! One thousand four hundred and twenty events flew across the bus last night with zero failures—though the patio camera did clock twelve raccoons holding a committee meeting." \
  --persona dispatcher --out host1-intro.wav
opal say generate --text "Quite so, Dispatch. Their agenda remains classified, but the garbage cans held firm." \
  --persona butler --out host2-rejoinder.wav
```

#### 27. Live Visual Scene Narrator for Low-Vision Accessibility
A single spoken request captures the hallway camera in `look`, runs object detection, turns the bounding-box list into spatial prose in `think`, and speaks it immediately.

```bash
opal look analyze run --source cam-hallway --pipeline detect-objects
opal think ask "Convert these detections into clear spatial navigation advice for a blind resident: [{'label':'umbrella_stand','x':0.15,'y':0.7},{'label':'delivery_box','x':0.52,'y':0.85}]."
opal say stream \
  --text "The umbrella stand is tucked to your far left, but there is a cardboard delivery box directly in the center of the hallway about two paces ahead." \
  --persona butler --sample-rate 22050 --out hallway-nav.pcm
```

#### 28. Audiobook Chapter Proofreader (Catch Typos by Ear)
Synthesize a markdown draft chapter with `say`, run the generated WAV back through `listen` to verify no words collapse into unintelligible mush, and flag discrepancies.

```bash
opal say generate --text-file ./drafts/chapter-04.txt --persona butler --out ch04-proof.wav
opal listen recognition test --audio ch04-proof.wav --no-save --verbose
```

#### 29. Silent-Doorbell Visual & Spoken Relay for Hard-of-Hearing Workshop
When `listen` or an intercom sensor publishes a `doorbell.pressed` event, `look` snaps a frame of who is outside, and `event` flashes the workbench strobe while `say` announces the visitor on the bone-conduction headset.

```bash
opal event publish --topic home.doorbell.pressed --source front-chime --data '{"button":"main"}'
opal look source capture cam-front --retain --annotate
opal say generate --text "Front doorbell pressed. Capture saved to cap-9921." --persona dispatcher --out headset-chime.wav
```

#### 30. Automated Podcast Ad-Read Generator in Character
Let `think` draft a sponsor read for a fictional product in the `sherlock` persona's voice and render the WAV in `say`.

```bash
opal think ask "In character as Sherlock Holmes, write a two-sentence endorsement for a waterproof notebook."
opal say generate \
  --text "When pursuing a mudlark across the Thames embankment in a November squall, an ink-stained cuff is an amateur's blunder. I record my monographs exclusively on waxed storm-proof vellum." \
  --persona sherlock --out sponsor-holmes.wav
```

---

### VI. Wildlife, Garden & Observatory (`look` + `event` + `think` + `say`)

#### 31. Backyard Birding Life-List Logger & Spoken Spotter
When `look` spots a rare species at the feeder with high confidence, save an annotated capture, log the sighting on the `event` bus, and have `say` whisper the alert inside the study.

```bash
opal look config rule add --id rare-warbler --name "Cerulean Warbler Spotted" \
  --source cam-feeder --kind object_appears --class-filters '["cerulean_warbler"]' \
  --threshold 0.90 --capture-on-match
opal event publish --topic wildlife.bird.spotted --source look-feeder \
  --data '{"species":"Setophaga cerulea","confidence":0.94,"capture_id":"cap-warbler-1"}'
opal say generate \
  --text "Pardon the interruption: a Cerulean Warbler just landed on the south feeder." \
  --profile 2 --persona butler --out warbler-whisper.wav
```

#### 32. Chicken Coop Automatic Dusk Headcount
At sunset, run `look analyze run` on the roost camera, pass the detected hen count to `think`, and announce whether any hen is still AWOL in the yard.

```bash
opal look analyze run --source cam-coop-roost --pipeline count-hens
opal think ask "Coop roster is 8 hens. Camera detected 7 hens on the roost bar at dusk. Formulate a one-sentence alert."
opal say generate \
  --text "Coop headcount is seven of eight—one hen is still out in the run before the automatic door closes." \
  --persona dispatcher --out coop-check.wav
```

#### 33. All-Sky Cloud-Cover Check Before Opening the Telescope Roof
Snap a frame from the all-sky fisheye camera, evaluate cloud cover, and prevent `event` from opening the roll-off roof if rain clouds are present.

```bash
opal look source capture cam-allsky --retain
opal look analyze run --source cam-allsky --pipeline sky-classifier
opal event publish --topic observatory.sky.state --source cam-allsky \
  --data '{"cloud_pct":12,"precipitation":false,"safe_to_open":true}'
opal event config rule test open_roof_if_clear \
  --event '{"topic":"observatory.sky.state","data":{"cloud_pct":12,"precipitation":false,"safe_to_open":true}}'
```

#### 34. Deer-in-the-Hostas Ultrasonic & Verbal Shoo-Away
Detect `deer` entering the garden bed polygon at 4 AM, trigger a short clip recording for posterity, and fire an action.

```bash
opal look config zone add --id zone-hostas --source cam-garden --name "Hosta Bed" \
  --kind polygon --points '[[0.12,0.50],[0.88,0.50],[0.88,0.95],[0.12,0.95]]'
opal look config rule add --id deer-in-hostas --name "Deer eating the hostas" \
  --source cam-garden --zone zone-hostas --kind enters_zone \
  --class-filters '["deer"]' --capture-on-match --clip-on-match
opal look data artifact list --limit 5
```

#### 35. Beehive Entrance Traffic & Swarm Early-Warning
Compare bee-traffic density observations from `look` against normal afternoon baselines using `think`.

```bash
opal look data observation list --source cam-hive-1 --task detect --limit 20
opal think ask "Hive 1 entrance observations jumped from 45 bees/frame to 310 bees/frame at 13:15 on a warm May afternoon. Assess swarm likelihood in one sentence."
opal say generate \
  --text "Hive one entrance activity has spiked nearly sevenfold—classic bearding or imminent primary swarm; inspect queen cells immediately." \
  --persona butler --out hive-alert.wav
```

---

### VII. Smart Home & Office Choreography (`listen` + `event` + `look` + `think` + `say`)

#### 36. "I'm Heading Out" — One Spoken Phrase Arms Monitors, Switches Profiles & Confirms Aloud
Speak `"brigadier, I'm heading out"`, match `home.depart` in `listen`, publish `home.mode.away` in `event`, enable the indoor camera monitor in `look`, and confirm via `say`.

```bash
opal listen config intent add --name home.depart \
  --phrase "I'm heading out" --phrase "nobody is home" --phrase "arm away mode"
opal listen recognition test --text "brigadier, I'm heading out" --expect-intent home.depart
opal event publish --topic home.mode.changed --source listen \
  --data '{"mode":"away","triggered_by":"voice"}'
opal look config monitor update mon-front --enabled
opal say generate --text "Away mode armed. Perimeter monitors are active. Have a good trip." \
  --persona butler --out away-armed.wav
```

#### 37. "Where Did I Leave My Keys?" Visual Retro-Search
Query recent `look` observations for `key_ring` or `glasses` across indoor cameras and let `say` tell you which room won.

```bash
opal look data observation list --label keys --limit 5
opal think ask "Turn this observation into a helpful spoken answer: {'source_id':'cam-entryway','label':'keys','zone':'console-table','timestamp':'2026-04-19T16:42:10Z'}."
opal say generate --text "Your keys were last spotted on the entryway console table at 4:42 PM." \
  --persona butler --out keys-found.wav
```

#### 38. Focus-Mode Do-Not-Disturb Gatekeeper
Activate a quiet profile in `say`, set `think` to queue non-urgent summaries, and have `event` suppress chime actions unless an event carries `priority: critical`.

```bash
opal say config profile activate 2
opal event config rule add --id critical_only_chime --topic 'home.alert.*' \
  --conditions '[{"path":"data.priority","operator":"eq","value":"critical"}]' \
  --actions '["speak_front_yard_alert"]' --enabled
```

#### 39. Baby Crib Wake-Up Detector with Gentle Lullaby Response
When `look` sees movement in the crib zone and `listen` hears activity, play a pre-synthesized gentle story via `say` while notifying the parents' dashboard via `event`.

```bash
opal event publish --topic nursery.awake --source crib-monitor --data '{"movement":true,"audio_db":52}'
opal say generate \
  --text "Hush now, little astronaut, the stars are still on night watch." \
  --profile 2 --persona butler --speed 0.80 --out nursery-soothe.wav
```

#### 40. Garage Door Left Open After Dark Check
Combine a `look` single-frame classification (`garage_door_open`) with an `event` rule that warns the house at 10 PM.

```bash
opal look analyze run --source cam-garage --pipeline door-state-check
opal event publish --topic garage.door.state --source cam-garage --data '{"state":"open","hour":22}'
opal event config rule test warn_open_garage \
  --event '{"topic":"garage.door.state","data":{"state":"open","hour":22}}'
opal say generate --text "Notice: it is ten P.M. and the main garage door is still open." \
  --persona butler --out garage-open.wav
```

---

### VIII. Incident Forensics, DevOps & Fleet Reliability (All Five Services)

#### 41. Portable Persona Propagator: Author Once in Think, Validate Everywhere
Create a new persona in `think` (the authoritative writer), sync/register it across the suite, and run `persona validate` on every service.

```bash
opal think config persona add --persona-id quartermaster --name "Q" \
  --voice en-gb-alan-low --description "Gadgets, logistics, and dry warnings about returning equipment in one piece"
opal think config persona validate quartermaster
opal say config persona add --persona-id quartermaster --name "Q" --voice en-gb-alan-low
opal say config persona validate quartermaster
opal listen config persona add --persona-id quartermaster --name "Q" --voice en-gb-alan-low
opal look config persona add --persona-id quartermaster --name "Q" --voice en-gb-alan-low
opal event config persona add --persona-id quartermaster --name "Q" --voice en-gb-alan-low
```

#### 42. Unified `config setting` Parity Audit Across All Five Services
Verify that every service responds identically to the canonical `config setting list` and `config setting show` commands introduced in v1.7.1.

```bash
opal say config setting list
opal listen config setting list
opal look config setting list
opal think config setting list
opal event config setting list
```

#### 43. Dead-Action Forensic Postmortem (Dropped Execution → Think Root-Cause → Spoken Report)
When an `event` rule-triggered execution lands in `status: dropped` due to `input_validation_failed`, pull the execution record and offending event, let `think` explain the schema mismatch, and read the postmortem aloud.

```bash
opal event data execution list --status dropped --limit 5
opal event data execution show exec-4091b
opal event history show evt-8821a
opal think ask "Explain why this event payload failed the action's input_schema and how to fix the producer." \
  --context '{"error_code":"input_validation_failed","error_message":"moisture_pct is required","payload":{"bed":"tomatoes","moisture":18.4}}'
opal say generate \
  --text "Postmortem on execution 4091b: the sensor published 'moisture' instead of 'moisture_pct', so the valve action's input schema rightly dropped it." \
  --persona quartermaster --out postmortem.wav
```

#### 44. Zero-Downtime Fleet Configuration Export & Pre-Flight Validation
Export portable configuration bundles from all five services and run `backup validate` on each before upgrading a host.

```bash
opal say backup export --out backup-say.json
opal listen backup export --out backup-listen.json
opal look backup export --out backup-look.json
opal think backup export --out backup-think.json
opal event backup export --out backup-event.json

opal say backup validate --file backup-say.json
opal listen backup validate --file backup-listen.json
opal look backup validate --file backup-look.json
opal think backup validate --file backup-think.json
opal event backup validate --file backup-event.json
```

#### 45. Five-Service Liveness & Readiness Sweep
Check `/health/live`, `/health/ready`, and `/info/ping` across the entire OPAL stack before starting an integration test run.

```bash
opal say info ready
opal listen info ready
opal look info ready
opal think info ready
opal event info ready
opal say info ping
opal listen info ping
opal look info ping
opal think info ping
opal event info ping
```

#### 46. Look Output Retrieval Trifecta (Capture + Recording + Job Export via One Command)
Prove that `opal look output fetch` retrieves bytes uniformly across all three Look output lifecycles without branching on resource type.

```bash
# 1. Capture -> Capture.output_ref.content_url
opal look data capture show cap-8f2d41a0
opal look output fetch /api/v1/capture/cap-8f2d41a0/content --out out-capture.jpg

# 2. Finalized Recording -> Recording.artifact_ref.content_url
opal look data recording show rec-51c2
opal look output fetch /api/v1/artifact/art-rec-51c2/content --out out-recording.mjpeg

# 3. Completed Export Job -> Job.output_refs[0].content_url
opal look data job show job-9a3f
opal look output fetch /api/v1/artifact/art-job-9a3f-clip/content --out out-export.mp4
```

#### 47. Voice-Activated Incident Freeze ("Freeze Everything and Save Snapshots")
When an operator says `"brigadier, freeze state"`, `listen` matches the intent, and you immediately snapshot all five databases with `backup create` plus a camera capture.

```bash
opal listen config intent add --name ops.freeze_state \
  --phrase "freeze state" --phrase "snapshot everything right now"
opal listen recognition test --text "brigadier, freeze state" --expect-intent ops.freeze_state
opal look source capture cam-front --retain --annotate
opal say backup create
opal listen backup create
opal look backup create
opal think backup create
opal event backup create
```

#### 48. Synthetic Chaos Drill: Test Every Event Rule Without Firing Real Hardware
Use `opal event config rule test` across your vision, voice, and sensor rules to prove routing logic after a config import.

```bash
opal event config rule test notify_front_yard_person \
  --event '{"topic":"opal.look.rule.matched","data":{"rule_id":"person-in-front-yard","source_id":"cam-front"}}'
opal event config rule test dry_tomato_bed \
  --event '{"topic":"greenhouse.soil.moisture","data":{"bed":"tomatoes","moisture_pct":14.2}}'
opal event config rule test stop_bad_print \
  --event '{"topic":"opal.look.rule.matched","data":{"rule_id":"print-spaghetti","confidence":0.91}}'
```

#### 49. Live Latency & Bottleneck Triage (Listen Performance + Look Metrics + Think Task Inspection)
When the voice-to-vision-to-speech loop feels sluggish, pull the timing breakdown from each service's telemetry endpoint and let `think` finger the culprit.

```bash
opal listen performance summary --limit 20
opal look info metrics
opal think task list --status completed --limit 5
opal think ask "Given STT average 140ms, NLU 4ms, Look frame inference 38ms, and LLM task duration 2,900ms, tell me in one dry sentence where our latency budget went."
opal say generate \
  --text "Ninety-four percent of your latency budget is being spent waiting for the large language model to clear its throat." \
  --persona quartermaster --out latency-verdict.wav
```

#### 50. Graceful Fleet Shutdown with Final Spoken Sign-Off
Have `say` synthesize a sign-off message, log a shutdown marker on `event`, and cleanly stop all five background services via `service stop`.

```bash
opal say generate \
  --text "All OPAL subsystems standing down for maintenance. Goodnight." \
  --persona butler --out signoff.wav
opal event publish --topic ops.fleet.shutdown --source cli --data '{"reason":"scheduled_maintenance"}'
opal look service stop
opal listen service stop
opal think service stop
opal say service stop
opal event service stop
```
