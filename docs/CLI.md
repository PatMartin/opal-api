# `opal` — a Typer CLI over the OPAL suite

> **Status: hypothetical.** This document describes a CLI that could be
> generated from the five OpenAPI contracts in `openapi/`. Nothing here is
> implemented in this repository. Every command maps to an operation that
> exists in the contracts; where a contract carries `x-opal-cli` metadata
> (LOOK, THINK) the names below follow it exactly. Where it does not (EVENT,
> LISTEN, SAY) the names follow the same `<group> <verb>` convention.

OPAL is five independent services, each with its own contract, each usable
alone. The CLI mirrors that: one top-level `opal` binary with one sub-app per
service, plus a thin `opal` layer for cross-service flows.

```
opal
├── event    openapi/opal_event.yaml    event bus, rules, actions
├── listen   openapi/opal_listen.yaml   wakeword, STT, intents, slots
├── look     openapi/opal_look.yaml     cameras, vision pipelines, observations
├── say      openapi/opal_say.yaml      text-to-speech
├── think    openapi/opal_think.yaml    LLM tasks and sessions
└── (suite)  compound flows that chain the above
```

---

## Conventions shared by every sub-app

These come from the OPAL suite standard that all five contracts declare
(`x-opal-context-standard`, now centralised in
`openapi/shared/opal_kernel.yaml`).

### Global options

| Option | Purpose |
|---|---|
| `--url` / `OPAL_<SERVICE>_URL` | Base URL of the service (e.g. `http://127.0.0.1:8080`) |
| `--token` / `OPAL_TOKEN` | Bearer token. Optional on loopback; required otherwise (401 if missing, 403 if insufficient) |
| `--session-id`, `--transaction-id`, `--causation-id` | Set the `X-Opal-*` correlation headers. Auto-generated when omitted; always echoed in responses |
| `--json` | Emit raw response JSON instead of a table |
| `--if-match <etag>` | Strong ETag precondition for configuration mutations (see below) |

### Concurrency: `--if-match` is not optional

Every settings and configuration mutation across the suite requires a
strong `If-Match` ETag. Missing → **428**; stale → **412**. The CLI should
default to *read-then-write*: fetch the resource, capture `ETag`, send the
mutation with it. `--if-match '*'` is a deliberate override.

### Pagination

Every list operation that can grow is cursor-paginated: `--cursor`,
`--limit`, response carries `next_cursor` + `has_more`. Cursors are bound to
the filter set; a cursor reused with different filters is a **422**.

### Health, settings, backup — identical everywhere

Every service exposes the same kernel-defined operations, so these commands
behave identically under every sub-app:

```
opal <svc> health              # aggregate report (status: ok|degraded|...)
opal <svc> health live         # liveness probe
opal <svc> health ready        # readiness probe
opal <svc> settings list
opal <svc> settings show <key>
opal <svc> settings set <key> <json-value>      --if-match
opal <svc> settings remove <key>                --if-match
opal <svc> settings patch '<json-object>'       --if-match
```

Backup / configuration portability (EVENT, LISTEN, SAY use `backup`; LOOK
calls it `configuration`, same semantics):

```
opal <svc> backup export [-o file.json]     # portable logical config, secrets excluded
opal <svc> backup validate file.json        # non-mutating dry run
opal <svc> backup import file.json          --if-match   # atomic; failure leaves previous config intact
# LISTEN and SAY additionally manage server-side archives:
opal <svc> backup list
opal <svc> backup create
opal <svc> backup download <filename> [-o path]
opal <svc> backup restore <filename>        --if-match
opal <svc> backup delete <filename>
```

Secret material (tokens, provider keys) is never included in exports and
never returned by `settings show` — values are masked.

---

## `opal event` — OPAL Event

**What it is.** A small event bus plus an automation engine. Producers
publish `{topic, data}` events (REST or ZeroMQ, two-frame envelope:
topic + JSON). Rules match topics and conditions; matching rules fire
registered actions; executions are recorded.

### Commands

**Events**

```
opal event publish <topic> '<json-data>' [--source NAME] [--id UUID]
opal event list [--topic T] [--source S] [--from ISO] [--to ISO] [--cursor] [--limit]
opal event show <event_id>
opal event delete <event_id>
opal event clear                              # delete ALL stored events
opal event topics                             # observed topic names
```

Topic grammar: `^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)*$`, e.g.
`intent.recognized`, `opal.look.condition.matched`. `data` is any JSON
value.

**Rules**

```
opal event rules list
opal event rules add  --id ID --topic T [--condition PATH OP VALUE]... --action ACTION_ID... [--disabled]
opal event rules show <rule_id>
opal event rules update <rule_id> [--enable|--disable] [--topic T] ...   --if-match
opal event rules remove <rule_id>
opal event rules test <rule_id> '<json-event>'   # evaluate without executing
```

- `--topic` is an exact topic or a suffix pattern `prefix.*`.
- Conditions are ANDed. Operators: `eq ne gt gte lt lte in not_in exists contains`;
  `PATH` is a dotted path into `data`.
- Multiple actions fire independently — one failing does not stop the others.

**Actions** (three types, discriminated by `type`)

```
opal event actions list
opal event actions show <action_id>
opal event actions add shell  --id ID --mode exec|sh|bash|cmd|powershell (--executable X | --script-path P) [--timeout S]
opal event actions add http   --id ID --method GET|POST|PUT|PATCH|DELETE --url U --body-mode MODE [--header K=V]...
opal event actions add python --id ID --module M --function F [--timeout S]
opal event actions update <action_id> ...     --if-match
opal event actions remove <action_id>         # only if no rule references it
opal event actions execute <action_id> ['<json-input>']   # manual run
```

Every action may carry self-description fields used by THINK for tool
discovery: `--description`, `--input-schema FILE.json`, `--keyword K`...,
`--suggested-prompt P`....

**Executions & stats**

```
opal event executions list [--status S] [--rule-id R] [--action-id A] [--event-id E] [--cursor] [--limit]
opal event executions show <execution_id>
opal event stats                              # event + execution counters
```

### What EVENT does alone

- A local pub/sub bus for any script or device that can POST JSON.
- Cron-free automation: "when topic X with data.y > 3, run this script / hit
  this webhook / call this Python function".
- An audit log of what fired and why (`executions`).
- Dry-run rule authoring (`rules test`) before anything executes.

---

## `opal listen` — OPAL Listen

**What it is.** Wakeword detection, speech-to-text, intent recognition and
slot extraction. Audio in (live microphone or uploaded file) → structured
`{intent, slots, confidence}` out. Optionally publishes intent matches to
EVENT.

### Commands

**Vocabulary: wakewords, intents, phrases, slots**

```
opal listen wakewords list|show|add|update|remove
    add --name NAME [--confidence-threshold F] [--disabled]

opal listen intents list|show|add|update|remove
    add --name NAME [--description D] [--confidence-threshold F] [--phrase P]...
opal listen intents phrases <intent_id> list|add|remove
    add  <intent_id> "turn on the {room} lights"

opal listen slots list|show|add|update|remove
    add --name room [--slot-type TYPE] [--description D]
opal listen slots values <slot_id> list|add|remove
    add <slot_id> "kitchen"
opal listen slots aliases <slot_id> <value_id> list|add|remove
    add <slot_id> <value_id> "the cooking room"
```

Slots are typed variables; values are the canonical fill; aliases are
alternative spoken forms that resolve to the value.

**Profiles** (bundle wakewords + thresholds + VAD + enabled intents/slots)

```
opal listen profiles list|show|add|update|remove
    add --name NAME [--wakeword W]... [--enabled-intent I]... [--enabled-slot S]...
        [--confidence-thresholds JSON] [--vad-settings JSON] [--activate]
opal listen profiles activate <profile_id>    # exactly one active at a time
```

**Recognition pipeline**

```
opal listen recognition start
opal listen recognition stop
opal listen recognition status                # metrics: mic_overflows, queue depths, latencies
opal listen recognition stream [--debug]      # SSE of live results
opal listen recognition test-text "turn on the kitchen lights" [--save-log]
opal listen recognition test-audio clip.wav [--save-log] [--require-wakeword]
opal listen health audio-devices              # enumerate capture devices
```

Diagnostic results (`test-text`, `test-audio`) are always evaluated, logged
and streamed locally but **never published externally** — only live
microphone matches are actionable. Event publication is off by default
(`settings set event_publication_enabled true`); `event_transport` is
`http` or `zmq` (never `both`).

**Quality loop: logs, failed utterances, regression**

```
opal listen logs list [--intent-name N] [--matched true|false] [--cursor] [--limit]
opal listen logs show <log_id>
opal listen logs count

opal listen failed list [--reviewed B] [--promoted B] [--limit] [--offset]
opal listen failed show|update|remove <fu_id>
opal listen failed promote <fu_id> --intent-name N [--create-regression]

opal listen regression list|show|add|update|remove
    add --name N --phrase P --expected-intent I [--expected-slots JSON]
opal listen regression run [--enabled-only]
opal listen performance last|summary [--limit]|history [--cursor] [--limit]
```

### What LISTEN does alone

- An offline voice command recogniser with a custom vocabulary — no cloud.
- An intent classifier for text (`test-text`) usable from any shell script.
- A tuning workflow: see what failed, promote the phrase to an intent, pin
  it as a regression test, re-run after every vocabulary change.

---

## `opal look` — OPAL Look

**What it is.** Visual perception. *Sources* provide frames; *pipelines*
are DAGs of inference/processing stages; stages emit immutable
*observations*; *sessions* run live, *jobs* run finite work, *monitors*
express durable desired state (restart on failure). *Zones* and *rules*
turn observations into condition events; *captures*, *recordings* and
*artifacts* retain pixels.

`x-opal-cli` names below are the ones the contract itself declares.

### Commands

**Discovery**

```
opal look capabilities show       # which tasks/formats/filters this runtime supports
opal look engines list|show
opal look engines update <engine_id> [--enable|--disable] [--options JSON]   --if-match
opal look models list|show|remove
opal look models add --id ID --engine-id E --resource-ref REF --task detect [--task T]... [--options JSON]
opal look models update <model_id> ...        --if-match
```

**Sources** (cameras and files)

```
opal look sources list|show|remove
opal look sources add --id camera-1 --kind usb|rtsp|http_mjpeg|file|media|adapter --name N --locator URI
                      [--secret-ref REF] [--options JSON] [--disabled]
opal look sources update <source_id> ...      --if-match
opal look sources status <source_id>          # connectivity + last-frame state
opal look sources frame  <source_id> [-o frame.jpg] [--pipeline-id P] [--presentation-filter JSON]
                                      [--width W] [--height H] [--quality Q] [--target-fps F]
opal look sources stream <source_id> [--annotations] [--pipeline-id P] [--classes c,...] [--min-confidence F]
                                      [--show-labels] [--show-boxes] [--show-confidence] ...
opal look sources capture <source_id> [--retain]   # one-shot JPEG, optionally kept
```

Credentials for RTSP go through `--secret-ref` (a service-side secret
name), never inline in the locator.

**Pipelines, profiles, zones, rules, monitors**

```
opal look pipelines list|show|remove
opal look pipelines add --id ID --name N --stages stages.json [--description D]
opal look pipelines validate stages.json       # topology + task compatibility + capability check
opal look pipelines update <id> ...           --if-match

opal look profiles list|show|add|update|remove|activate

opal look zones list|show|remove
opal look zones add --id ID --source-id S --name N --kind polygon|line --points '[[x,y],...]'
opal look zones update <id> ...               --if-match

opal look rules list|show|remove
opal look rules add --id ID --name N --source-id S
     --kind object_appears|object_disappears|enters_zone|exits_zone|line_crosses|count_threshold|dwell_time
     [--zone-id Z] [--class-filter person]... [--threshold F] [--minimum-duration-ms MS] [--cooldown-ms MS]
     [--capture-on-match] [--clip-on-match]
opal look rules update <id> ...               --if-match

opal look monitors list|show|remove
opal look monitors add --id ID --name N --source-id S [--pipeline-id P] [--profile-id PR]
     [--restart-policy on_failure|always|never] [--disabled]
opal look monitors update <id> ...            --if-match
```

**Running work**

```
opal look analyze run   --source-id S | --media-id M  [--pipeline-id P] [--profile-id PR]   # one frame, synchronous
opal look analyze image photo.jpg [--pipeline-id P]                                        # upload + analyze

opal look sessions start --source-id S [--pipeline-id P] [--profile-id PR] [--auto-start]
opal look sessions list [--state S] [--source-id S] [--cursor] [--limit]
opal look sessions show|stop <session_id>
opal look sessions observations <session_id> [--cursor] [--limit]
opal look sessions stream  <session_id>                 # SSE: observation|heartbeat|session-state|error; Last-Event-ID resume
opal look sessions preview <session_id> [--classes ...] [--show-boxes] ... # annotated MJPEG

opal look jobs submit --kind analyze_video|export_annotated_video|extract_clip
     (--source-id S | --media-id M) [--pipeline-id P] [--range JSON] [--output JSON]
opal look jobs list [--state S] [--kind K] | show <job_id> | cancel <job_id>
```

**Observations and retained bytes**

```
opal look observations list [--source-id] [--session-id] [--job-id] [--task] [--label] [--after ISO] [--before ISO]
opal look observations show <observation_id>

opal look media list|show|remove  ;  opal look media upload video.mp4
opal look captures list|show|remove|download <capture_id> [-o file]
opal look recordings list|show ; recordings start --source-id S ... ; recordings stop <id>
opal look artifacts list|show|remove|download <artifact_id> [-o file] [--range bytes=0-1023]
```

**Operations**

```
opal look metrics show
opal look events status           # publication queue depth + drops (events off by default, allowlisted)
```

### What LOOK does alone

- Turn any USB/RTSP/MJPEG camera or video file into typed, queryable
  observations (detections, and optionally segmentation, pose, OCR,
  caption, VQA, depth, embeddings, anomaly — whatever `capabilities`
  advertises).
- Zone/line analytics: "a person entered the driveway polygon and dwelt
  10 s" without any other service.
- Batch video analysis and clip extraction as jobs.
- A live annotated preview you can open in a browser.

---

## `opal say` — OPAL Say

**What it is.** Implementation-neutral text-to-speech over host-installed
engines (the contract names Piper and Kokoro as examples). Engines →
voices → profiles → generation.

### Commands

**Engines** — discovered, not installed

```
opal say engines list                       # engine_id, enabled, available, state: ready|unavailable|error|disabled
opal say engines show <engine_id>           # includes options_schema, device_types, version
opal say engines update <engine_id> [--enable|--disable] [--options JSON]   --if-match
opal say engines validate <engine_id>       # can the engine actually run right now?
```

`enabled` is administrative intent; `available` is live reality. A fresh
host typically shows the engine *known, enabled, unavailable* until its
runtime is present.

**Voices**

```
opal say voices list [--engine-id E] [--enabled true|false]
opal say voices add  --voice-id ID --name N --engine-id E --engine-voice-ref REF [--language L] [--engine-options JSON]
opal say voices show|update|remove <voice_id>
opal say voices validate <voice_id>        # resolves engine_voice_ref against the engine
opal say voices test <voice_id> ["sample text"] [-o out.wav]
```

`engine_voice_ref` is the engine's own identifier for the voice (a model
path for Piper, a voice name for Kokoro).

**Profiles**

```
opal say profiles list|show|add|update|remove|activate
    add --name N [--voice-id V] [--speed F] [--volume F] [--output-format wav|pcm] [--sample-rate HZ]
        [--engine-options JSON] [--activate]
```

**Generation**

```
opal say speak "text to speak" [-o out.wav] [--profile-id P] [--voice-id V] [--engine-id E]
                               [--speed F] [--volume F] [--output-format F] [--sample-rate HZ]
opal say stream "text to speak" | aplay -f S16_LE -r 22050 -c 1
```

Setting precedence, lowest → highest: service defaults → active profile →
explicit `--profile-id` → per-request flags. `stream` always emits
headerless signed 16-bit LE mono PCM (no WAV; nothing is buffered).

### Installing an engine (host-level, outside the API)

The contract is explicit: *"Engines are installed and discovered by the
implementation; they are not created or deleted through this API."* So
install is a host step and the CLI only verifies it:

```
# 1. install the engine runtime on the host (implementation-specific)
#    e.g. pip install piper-tts  /  download a Piper .onnx voice model
# 2. confirm the service now sees it
opal say engines list
opal say engines validate piper
# 3. register a voice that points at the installed model
opal say voices add --voice-id en-amy --name "Amy" --engine-id piper \
    --engine-voice-ref /opt/piper/en_US-amy-medium.onnx --language en-US
opal say voices validate en-amy
opal say voices test en-amy -o test.wav
```

### What SAY does alone

- `echo "Dinner is ready" | opal say speak -` — TTS from any script.
- Multiple voices/engines behind one stable interface; swap Piper for
  Kokoro by changing a profile, not the caller.
- Low-latency streaming PCM for voice assistants that start playing before
  synthesis finishes.

---

## `opal think` — OPAL Think

**What it is.** LLM task runner. A *task* is one unit of intelligent work
(`POST /tasks/` returns **202** with a durable task ID — not an answer);
*sessions* serialise tasks and keep context; *models* are discovered from
configured providers. THINK is also the endpoint EVENT HTTP actions call
when a rule needs intelligence.

`x-opal-cli` names below are the ones the contract itself declares.

### Commands

```
opal think ask "question"  [--model-id M] [--session-id S] [--context JSON] [--max-steps N] [--timeout-seconds S]
    # = task create + task watch; prints the streamed answer
opal think chat [--session-id S] [--title T]
    # = session add (if needed) + one task per turn, interactive loop

opal think task create "prompt" [...same flags...]   # returns the task_id immediately
opal think task list [--status S] [--session-id S] [--cursor] [--limit]
opal think task show  <task_id>
opal think task watch <task_id>                 # SSE: output + progress until terminal
opal think task cancel <task_id>

opal think session add [--title T]
opal think session list|show|remove

opal think model list                           # providers + models; available=false allowed
opal think model show <model_id>
```

Models are a bounded catalog: *"no model installation or deletion is
exposed."* Provider endpoints and API keys are service **settings**
(`opal think settings set ...`), masked on read.

### What THINK does alone

- A scriptable LLM front door with durable tasks: fire, go away, `watch`
  or `show` later.
- Serialised multi-turn sessions (409 if a session is busy).
- Provider-agnostic: swap a local model for a hosted one via settings.

---

## The ecosystem: compound `opal` commands

Alone, each service is a tool. Together they are an assistant. The glue
is EVENT (the bus) plus the correlation headers: an `X-Opal-Transaction-Id`
minted by the entry service rides every hop, so `opal event executions list`
can later show the whole chain.

Suggested compound commands (pure client-side orchestration — no new
server API):

```
opal ask "question"                    # think ask → say speak (spoken answer)
opal listen-and-act                    # listen stream → publish intent events → event rules decide
opal watch <source_id>                 # look sessions start + stream, pretty-printed
opal drop-in <source_id>               # look sources stream --annotations, opened in the browser
opal describe <source_id>              # look sources frame → look analyze image (caption/VQA task) → say speak
opal status                            # all five: health, with correlation header echo
opal backup-all [-o dir/]              # export every service's config; validate; archive
```

### 20 use cases

**Home automation**

1. **"Lights on when I'm home after dark."** LOOK rule `enters_zone`
   (driveway polygon, class `person`) → publishes `opal.look.condition.matched`
   → EVENT rule with condition `data.zone eq driveway` → HTTP action to
   the light controller. No LLM, no voice; three config commands.
2. **Package detection with spoken alert.** LOOK `object_appears` rule
   (`class_filter package`, `--capture-on-match`) → EVENT → HTTP action to
   THINK (`"Describe this delivery in one sentence"` with the capture URL
   in `context`) → SAY `speak` on the kitchen speaker.
3. **Voice-controlled scenes.** LISTEN intent `scene.set` with slot `scene`
   (values `movie`, `dinner`, `bedtime` + aliases) → event
   `intent.recognized` → one EVENT rule per scene value → shell actions.
4. **Leak/anomaly watch.** LOOK monitor with an `anomaly` task pipeline
   (if `capabilities` advertises it) on the utility-room camera; EVENT
   rule `count_threshold gt 0` → SMS webhook + `extract_clip` job for
   evidence.
5. **"Did I close the garage?"** LISTEN intent → EVENT → THINK task whose
   context includes a fresh `opal look sources frame garage` → SAY answers
   "Yes, the door is closed."

**Education**

6. **Reading coach.** Child reads aloud into LISTEN (`test-audio` or live);
   THINK compares the transcript with the target passage and returns
   gentle corrections; SAY reads them back in a friendly voice profile.
7. **Lab-bench object tutor.** Point the webcam at circuit components;
   LOOK `detect` + `caption`; THINK explains what each part does; SAY
   narrates. Works offline in a classroom.
8. **Language drill with slot filling.** LISTEN intents in the target
   language with slots for nouns/verbs; `regression run` after each lesson
   shows the recogniser's accuracy curve via `performance history`.
9. **Attendance and attention (privacy-preserving).** LOOK `count_threshold`
   on a classroom zone — *counts*, never identities (the contract forbids
   identity recognition) — logged to EVENT for the teacher's dashboard.
10. **Spoken flashcards.** THINK generates Q/A pairs from notes → SAY
    speaks the question → LISTEN captures the answer → THINK grades.

**Voice assistant**

11. **"Ask OPAL a question."** `opal ask` = wakeword → LISTEN STT → THINK
    task → SAY streamed PCM, with one transaction ID through all four hops.
12. **Hands-free timers and reminders.** LISTEN intent `timer.set` with a
    `duration` slot → EVENT shell action schedules → later EVENT publishes
    `timer.fired` → SAY announces. EVENT's `executions` is the audit trail.
13. **Kitchen helper.** "What can I make with eggs and spinach?" → THINK
    session keeps the conversation; follow-ups ("make it vegan") reuse the
    `session_id`; SAY speaks each step on request.
14. **Accessibility narrator.** `opal describe camera-1` on demand or on a
    LOOK rule; LOOK `caption`/`OCR` task → SAY. Reads signs, labels,
    screens to a visually impaired user.
15. **Multi-voice household.** SAY profiles per family member (voice,
    speed, volume); LISTEN profiles per wakeword; EVENT rule maps the
    matched wakeword to the SAY profile used in the reply.

**Custom / developer**

16. **CI "talking build."** Any pipeline can `opal event publish
    build.finished '{"status":"failed","repo":"..."}'`; an EVENT rule
    routes failures to THINK ("summarise this log") and SAY on the office
    speaker.
17. **Wildlife camera.** LOOK monitor (`restart_policy always`) on an RTSP
    feed; `object_appears` rules per species class with `--clip-on-match`;
    nightly job `export_annotated_video`; EVENT counts via `stats`.
18. **Retail shelf monitor.** LOOK `object_disappears` + `dwell_time` zones
    on shelf cameras → EVENT → HTTP action to an inventory API; THINK
    writes the daily restock summary.
19. **Elder-care check-in.** LOOK `dwell_time` (no motion in the living
    room for N minutes during waking hours) → EVENT → SAY asks "Are you
    okay?" → LISTEN waits for `yes`/`help` intents → escalate via HTTP
    action if `help` or no answer.
20. **Self-documenting automations.** EVENT actions carry `description`,
    `input_schema`, `keywords`, `suggested_prompts`; THINK reads
    `GET /actions/` as its tool catalog and can be asked "what can you do
    around here?" — the answer is generated from the live configuration,
    not a hand-written list.

---

## Why a generated CLI fits these contracts

- **Every mutation is `If-Match`-guarded**, so a CLI can be safe by
  default (read → mutate) with no server cooperation beyond the contract.
- **Every response echoes correlation headers**, so `--transaction-id` gives
  you end-to-end tracing for free across all five services.
- **LOOK and THINK already declare `x-opal-cli`** per operation; a
  generator can derive the command tree with zero mapping tables, and the
  repository's `tests/test_look_cli.py` already enforces that every public
  LOOK operation has an unambiguous CLI name.
- **Shared kernel routes** (health, settings, backup, profiles, engines) are
  defined once in `openapi/shared/opal_kernel.yaml`, so the shared
  sub-commands are literally the same code under every service.
