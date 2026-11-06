# `opal` — one Typer CLI for the whole OPAL suite

> **Hypothetical.** This CLI does not exist. Every command below maps to a
> real operation in `openapi/`. Where a contract declares `x-opal-cli`
> (LOOK, THINK) the names match it; elsewhere the same `<noun> <verb>`
> grammar applies. Every flag maps to a real parameter, request field, or
> response member. All five specs are version `1.5.0` and share the kernel
> contract in `openapi/shared/opal_kernel.yaml`.

```
opal
├── event    opal_event.yaml    publish/subscribe bus, rules, actions, execution ledger
├── listen   opal_listen.yaml   wakeword → STT → intent + slot extraction
├── look     opal_look.yaml     sources → pipelines → immutable observations
├── say      opal_say.yaml      engines → voices → profiles → generated speech
└── think    opal_think.yaml    prompt → durable task → streamed answer
```

## Install & global options

```bash
pip install opal-cli
export OPAL_TOKEN=…                    # BearerAuth: optional on loopback, 401/403 otherwise
export OPAL_EVENT_URL=http://127.0.0.1:8080
```

Options that work on **every** command, pinned by the kernel:

| Option | Meaning |
|---|---|
| `--session-id` / `--transaction-id` / `--request-id` / `--causation-id` | `X-Opal-*` correlation headers; auto-generated, echoed on every response |
| `--if-match <etag>` | strong ETag on settings/config mutations — **428** missing, **412** stale |
| `--cursor`, `--limit` | cursor pagination; `next_cursor` + `has_more` in the response |
| `--json` | raw output; every error is the `OpalError` envelope (`code`, `message`, `request_id`) |

Commands that exist identically under **every** service (kernel Path Items):

```bash
opal <svc> health | health live | health ready
opal <svc> settings list | settings show KEY | settings set KEY VALUE --if-match <e> \
         | settings remove KEY --if-match <e> | settings patch JSON --if-match <e>
opal <svc> backup export -o cfg.json | backup validate cfg.json | backup import cfg.json --if-match <e>
```

`profiles`, `engines`, and server-side `backup list/create/restore` exist
where their contract defines them, noted per service.

---

# `opal event` — the bus

Publish `{topic, data}` events, match them with rules (exact topic or
`prefix.*`, ANDed conditions, multiple actions), fire shell / HTTP / Python
actions, audit executions.

## Commands

```text
opal event publish <topic> '<json>' [--source S] [--id UUID]
opal event list [--topic T] [--source S] [--from ISO] [--to ISO] [--cursor C] [--limit N]
opal event show <event_id> | delete <event_id> | clear
opal event topics

opal event rules list | show <rule_id> | remove <rule_id>
opal event rules add --id R --topic T --action A_ID... [--condition "path op value"]... [--disabled]
    # operators: eq ne gt gte lt lte in not_in exists contains
opal event rules update <rule_id> [--enable|--disable] [--topic T]... --if-match <e>
opal event rules test <rule_id> --event '<json>'

opal event actions list | show <action_id> | remove <action_id>
opal event actions add shell  --id A --mode exec|sh|bash|cmd|powershell [--executable X|--script-path P]
opal event actions add http   --id A --method M --url U --body-mode M [--header K:V]...
opal event actions add python --id A --module M --function F [--timeout-seconds N]
    # all types accept self-description for THINK tool discovery:
    # --description --input-schema JSON --keyword K... --suggested-prompt P...
opal event actions update <action_id> ... --if-match <e>
opal event actions execute <action_id> ['<json-input>']

opal event executions list [--status S] [--rule-id R] [--action-id A] [--event-id E]
opal event executions show <execution_id>
opal event stats
```

## Alone — programmable pub/sub with an audit trail

```bash
# "watch a sensor stream and page me when temperature crosses 30"
opal event actions add http --id page-me --method POST \
    --url https://hooks.example.com/page --body-mode json
opal event rules add --id hot-room --topic 'sensor.*' \
    --condition 'data.temp gt 30' --action page-me
opal event publish sensor.lab '{"temp": 33.2}' --source bench-pi
opal event rules test hot-room --event '{"topic":"sensor.lab","data":{"temp":33.2}}'
opal event executions list --rule-id hot-room      # the receipt
```

Also native ZeroMQ out-of-band: two frames, topic + JSON (kernel
`x-opal-event-envelope`).

---

# `opal listen` — the ears

Wakewords, STT, intents, slots — plus the quality loop that keeps
recognition improving: logs → failed utterances → promoted phrases →
regression suite.

## Commands

```text
opal listen wakewords list|show|add --name N [--confidence-threshold F] [--disabled]|update|remove
opal listen intents  list|show|add --name N [--phrase P]... [--confidence-threshold F]|update|remove
opal listen intents  phrases <intent_id> list|add --phrase "turn on the {room} lights"|remove <phrase_id>
opal listen slots    list|show|add --name room --slot-type TYPE|update|remove
opal listen slots    values  <slot_id> list|add --value kitchen|remove <value_id>
opal listen slots    aliases <slot_id> <value_id> list|add --alias "cooking room"|remove <alias_id>

opal listen profiles list|show|add|update|remove|activate
    # add: --name --wakeword-names --enabled-intents --enabled-slots
    #      --confidence-thresholds JSON --vad-settings JSON --activate

opal listen recognition start|stop|status          # status: mic_overflows, queue depth, latencies
opal listen recognition stream [--debug]           # SSE of live results
opal listen recognition test-text "phrase" [--save-log]
opal listen recognition test-audio clip.wav [--save-log] [--require-wakeword]
opal listen health audio-devices

opal listen logs list [--intent-name N] [--matched B]|show <log_id>|count
opal listen failed list [--reviewed B] [--promoted B]|show|update|remove <fu_id>
opal listen failed promote <fu_id> --intent-name N [--create-regression]
opal listen regression list|add --name N --phrase P --expected-intent I [--expected-slots JSON]|run [--enabled-only]
opal listen performance last|summary|history
opal listen backup list|create|download F|restore F --if-match <e>|delete F
```

Publication to EVENT is off by default and never includes diagnostic
results — enable with `settings set event_publication_enabled true`.

## Alone — a vocabulary-scoped voice command box

```bash
opal listen intents add --name lights.set --phrase "turn on the {room} lights"
opal listen slots add --name room --slot-type room_name
opal listen slots values room_values_placeholder >/dev/null 2>&1  # create values on the slot's id
opal listen slots add --name room --slot-type room_name >/dev/null # (id shown by slots list)
SID=$(opal listen slots list --json | jq -r '.[]|select(.name=="room")|.id')
opal listen slots values $SID add --value kitchen
opal listen slots values $SID add --value office
opal listen recognition test-text "turn on the kitchen lights"
# → {intent: "lights.set", slots: {room: "kitchen"}, confidence: 0.9x}
opal listen regression add --name lights-kitchen --phrase "turn on the kitchen lights" \
    --expected-intent lights.set --expected-slots '{"room":"kitchen"}'
opal listen regression run
```

---

# `opal look` — the eyes

Sources → pipelines (DAG stages) → observations. Sessions run live, jobs
run finite, monitors keep desired state alive, zones+rules convert
detections to events, captures/recordings/artifacts retain pixels.
Commands below are the contract's own `x-opal-cli` names.

## Commands

```text
opal look capabilities show
opal look engines list|show|update <id> [--enable|--disable] [--options JSON] --if-match <e>
opal look models   list|show|add --id M --engine-id E --resource-ref REF --task T...|update|remove

opal look sources  list|show|add --id cam-1 --kind usb|rtsp|http_mjpeg|file|media|adapter \
       --name N --locator URI [--secret-ref S]|update|remove
opal look sources  status <source_id>
opal look sources  frame <source_id> [-o frame.jpg] [--pipeline-id P] [--width W] [--height H] \
       [--quality 1-100] [--target-fps F] [--presentation-filter JSON]
opal look sources  stream <source_id> [--annotations] [--classes a,b] [--min-confidence F] \
       [--show-labels|--show-boxes|--show-confidence] [--pipeline-id P]
opal look sources  capture <source_id>          # JPEG, optional retain

opal look pipelines list|show|add --id P --name N --stages stages.json|update|remove
opal look pipelines validate stages.json        # non-mutating topology/capability check

opal look zones    list|show|add --id Z --source-id S --name N --kind polygon|line --points JSON|update|remove
opal look rules    list|show|add --id R --name N --source-id S \
       --kind object_appears|object_disappears|enters_zone|exits_zone|line_crosses|count_threshold|dwell_time \
       [--zone-id Z] [--class-filters JSON] [--threshold F] [--minimum-duration-ms MS] [--cooldown-ms MS] \
       [--capture-on-match] [--clip-on-match]|update|remove
opal look monitors list|show|add --id M --name N --source-id S [--pipeline-id P] \
       [--restart-policy on_failure|always|never]|update|remove

opal look analyze run (--source-id S | --media-id M) [--pipeline-id P]
opal look analyze image photo.jpg

opal look sessions start --source-id S [--pipeline-id P] [--profile-id PR] [--auto-start]
opal look sessions list|show|stop <session_id>
opal look sessions observations <session_id>
opal look sessions stream  <session_id>        # SSE, Last-Event-ID resume; expired cursor = 409
opal look sessions preview <session_id>        # annotated MJPEG

opal look jobs submit --kind analyze_video|export_annotated_video|extract_clip \
       (--source-id S | --media-id M) [--pipeline-id P] [--range JSON] [--output JSON]
opal look jobs list|show|cancel <job_id>

opal look observations list [--source-id|--session-id|--job-id|--task|--label|--after|--before]|show <id>
opal look media      list|show|upload file.mp4|remove <media_id>
opal look captures   list|show|download <capture_id> [-o out.jpg]|remove
opal look recordings list|show|start --source-id S|stop <recording_id>
opal look artifacts  list|show|download <artifact_id> [-o f] [--range bytes]|remove

opal look metrics show | events status
opal look configuration export|validate|import   # look's name for backup/*
```

Optional tasks (segmentation, pose, OCR, caption, VQA, depth, embeddings,
anomaly) exist only if `capabilities` advertises them. No identity
recognition, model download, or arbitrary shell exec — by contract.

## Alone — camera → queryable observations, one camera, zero other services

```bash
opal look sources add --id porch --kind rtsp --name "Porch cam" \
    --locator rtsp://192.168.1.10/stream --secret-ref porch-cred
opal look sources status porch                         # connectivity + last frame
opal look pipelines validate porch-pipe.json
opal look pipelines add --id porch-pipe --name "porch detect" --stages porch-pipe.json
opal look sessions start --source-id porch --pipeline-id porch-pipe
opal look sessions stream sess_abc                     # live observations over SSE
opal look observations list --source-id porch --task detect --label person
```

---

# `opal say` — the voice

TTS over host-installed engines (contract examples: Piper, Kokoro).
Engines are *installed and discovered by the implementation — never
created through the API.*

## Commands

```text
opal say engines list                     # engine_id, enabled, available,
                                          # state ready|unavailable|error|disabled
opal say engines show <engine_id>         # options_schema, device_types, version
opal say engines update <id> [--enable|--disable] [--options JSON] --if-match <e>
opal say engines validate <engine_id>

opal say voices list [--engine-id E] [--enabled B]
opal say voices add --voice-id V --name N --engine-id E --engine-voice-ref REF \
       [--language L] [--engine-options JSON]
opal say voices show|update|remove <voice_id>
opal say voices validate <voice_id>
opal say voices test <voice_id> ["sample"] [-o out.wav]

opal say profiles list|show|add|update|remove|activate
    # add: --name --voice-id --speed --volume --output-format wav|pcm --sample-rate HZ

opal say speak "text" [-o out.wav] [--profile-id P] [--voice-id V] [--engine-id E] \
       [--speed F] [--volume F] [--output-format F] [--sample-rate HZ]
opal say stream "text"            # headerless s16le mono PCM to stdout
```

Generation precedence: defaults → active profile → `--profile-id` →
per-request flags.

## "Installing" an engine — host step, CLI-verified

```bash
# host side: install runtime + model files yourself, e.g. a Piper .onnx voice
opal say engines list                          # see it appear (maybe unavailable)
opal say engines validate piper                # proves it can actually run
opal say voices add --voice-id amy --name Amy --engine-id piper \
    --engine-voice-ref /opt/piper/en_US-amy-medium.onnx --language en-US
opal say voices validate amy && opal say voices test amy -o test.wav
opal say profiles add --name calm --voice-id amy --speed 0.9 --activate
opal say speak "Installation verified" -o ok.wav
```

## Alone — stable TTS façade

```bash
echo "Dinner is ready" | opal say speak - -o dinner.wav
opal say stream "Starting up" | aplay -f S16_LE -r 22050 -c 1   # live PCM pipe
```

---

# `opal think` — the brain

Durable LLM tasks over discovered providers: `POST /tasks/` = **202** +
task id. Sessions serialise work; models are a read-only catalog (keys
live in settings).

## Commands (contract's own `x-opal-cli`)

```text
opal think ask "prompt"                     # task create + task watch
opal think chat [--session-id S]            # session add + a task per turn

opal think task create "prompt" [--session-id S] [--model-id M] \
       [--context JSON] [--max-steps N] [--timeout-seconds S]
opal think task list [--status S] [--session-id S]
opal think task show|watch|cancel <task_id>   # watch = SSE output+progress

opal think session add [--title T]|list|show|remove <session_id>
opal think model list                        # providers + models, available=false allowed
opal think model show <model_id>
opal think settings set providers.acme.api_key sk-… --if-match <e>   # masked on read
```

## Alone — a queue-backed LLM door

```bash
opal think model list                              # pick a model_id
T=$(opal think task create "Summarise /var/log/syslog" --context '{"file":"/var/log/syslog"}' --json | jq -r .id)
opal think task watch $T                           # stream the answer
SID=$(opal think session add --title "ops chat" --json | jq -r .id)
opal think ask "follow-up question" --session-id $SID   # serialised turns
```

---

# The ecosystem — compound flows

One `--transaction-id` minted at the edge rides every hop: LISTEN logs,
EVENT executions, LOOK observations, THINK tasks, SAY responses. `opal
event executions list --event-id <E>` is the distributed trace viewer.

Meta-commands (client-side orchestration only):

```text
opal ask "question"                    listen STT → think task → say speak
opal drop-in <source>                  look sources stream --annotations (browser)
opal describe <source>                 look frame → analyze image(caption|VQA) → say speak
opal watch <source>                    look sessions start + stream
opal status                            all five healths
opal backup-all -o dir/                export+validate per service
```

## 20 use cases — with the command sequences

### Home automation

**1. Package alert with spoken announcement**
```bash
opal look rules add --id pkg --name "package at door" --source-id porch \
    --kind object_appears --class-filters '["package"]' --capture-on-match
opal event actions add http --id speak-pkg --method POST \
    --url http://say.local/api/v1/generate --body-mode json
opal event rules add --id pkg-alert --topic 'opal.look.*' \
    --condition 'data.class eq "package"' --action speak-pkg
```

**2. "Did I leave the stove on?"**
```bash
opal listen intents add --name appliance.check --phrase "is the {appliance} on"
SID=$(opal listen slots add --name appliance --slot-type device --json | jq -r .id)
opal listen slots values $SID add --value stove
opal look sources frame stove-cam -o /tmp/stove.jpg
opal look analyze image /tmp/stove.jpg --pipeline-id stove-check
opal think task create "Is the stove on? Answer yes/no from this analysis" \
    --context "$(opal look observations list --source-id stove-cam --json | jq '.[0]')"
```

**3. Person-at-door doorbell (no cloud)**
```bash
opal look zones add --id door-zone --source-id porch --name entry --kind polygon --points '[[.4,.6],[.6,.6],[.6,1],[.4,1]]'
opal look rules add --id doorbell --name doorbell --source-id porch \
    --kind enters_zone --zone-id door-zone --class-filters '["person"]' \
    --minimum-duration-ms 500 --cooldown-ms 60000
opal event rules add --id chime --topic 'opal.look.condition.matched' \
    --condition 'data.rule_id eq "doorbell"' --action speak-pkg   # reuse an HTTP action → say
```

**4. Leak/anomaly watcher**
```bash
opal look capabilities show --json | jq '.tasks'                  # confirm "anomaly" exists
opal look monitors add --id utility --name "utility room" --source-id utility-cam \
    --pipeline-id anomaly-pipe --restart-policy always
opal event rules add --id leak --topic 'opal.look.*' \
    --condition 'data.score gt 0.9' --action page-me
```

**5. Scene control by voice**
```bash
opal listen intents add --name scene.set --phrase "set {scene} scene"
opal event actions add shell --id lights-movie --mode exec --executable /usr/local/bin/lights-movie.sh
opal event rules add --id scene-movie --topic intent.recognized \
    --condition 'data.slots.scene eq "movie"' --action lights-movie
```

### Education

**6. Reading coach**
```bash
opal listen recognition test-audio reading-take1.wav --save-log
T=$(opal think task create "Compare this transcript to the passage and give gentle corrections" \
      --context "$(opal listen logs list --json | jq '.[0]')" --json | jq -r .id)
opal think task watch $T --json | jq -r .result | opal say speak - -o corrections.wav
```

**7. Language-drill accuracy tracking**
```bash
opal listen regression add --name fr-q1 --phrase "où est la bibliothèque" \
    --expected-intent location.query --expected-slots '{"place":"library"}'
opal listen regression run --enabled-only
opal listen performance history --limit 20        # accuracy trend across lessons
```

**8. Classroom object tutor**
```bash
opal look analyze run --source-id benchcam --pipeline-id detect+caption
opal look observations list --source-id benchcam --task caption --limit 1 --json | \
    jq -r '.items[0].caption' | \
    xargs -I{} opal think ask "Explain what a '{}' is to a 10-year-old" | \
    opal say speak -
```

**9. Head-count analytics (privacy-preserving)**
```bash
opal look rules add --id occupancy --name "class occupancy" --source-id room-cam \
    --kind count_threshold --class-filters '["person"]' --threshold 25
# counts only — no identity recognition exists in the contract
opal look observations list --task detect --label person --after 2026-11-06T08:00Z
```

**10. Spoken flashcards**
```bash
opal think ask "Generate 10 Q/A flashcards about photosynthesis as JSON" --json > cards.json
Q=$(jq -r '.[0].q' cards.json); opal say speak "$Q" | aplay
opal listen recognition test-audio answer.wav --save-log
opal think ask "Was this answer correct for '$Q'? Context: $(opal listen logs list --json | jq '.[0].transcript')"
```

### Voice assistant

**11. "Ask OPAL a question"**
```bash
opal ask "What's the capital of Norway?"        # = mic → STT → task → PCM playback
# manually:  opal listen recognition start; opal listen recognition stream | \
#   jq -r .transcript | xargs -I{} opal think ask "{}" | opal say speak -
```

**12. Hands-free timers**
```bash
opal listen intents add --name timer.set --phrase "set a timer for {minutes} minutes"
opal event actions add shell --id timer-fire --mode bash --script-path /opt/timer.sh
opal event rules add --id timer --topic intent.recognized \
    --condition 'data.intent eq "timer.set"' --action timer-fire
opal event executions list --action-id timer-fire   # why it fired, every time
```

**13. Multi-turn kitchen helper**
```bash
SID=$(opal think session add --title "cooking" --json | jq -r .id)
opal think ask "What can I make with eggs and spinach?" --session-id $SID
opal think ask "Make it vegan instead" --session-id $SID   # context carries over
```

**14. Accessibility narrator on demand**
```bash
opal describe mailbox-cam
# = opal look sources frame mailbox-cam -o /tmp/m.jpg && \
#   opal look analyze image /tmp/m.jpg --pipeline-id caption && \
#   opal look observations list --source-id mailbox-cam --task caption --json | \
#   jq -r '.items[0].caption' | opal say speak -
```

**15. Per-room voices**
```bash
opal say voices add --voice-id kokoro-m --name "Mellow" --engine-id kokoro --engine-voice-ref am_michael
opal say profiles add --name bedroom --voice-id kokoro-m --volume 0.6 --activate
opal say profiles add --name kitchen --voice-id amy --volume 1.0
opal say profiles activate kitchen        # switch = one command, no rewiring
```

### Custom / developer

**16. Talking CI**
```bash
# in the pipeline:
opal event publish build.finished '{"repo":"opal-api","status":"failed","log":"..."}'
opal event rules add --id ci --topic build.finished \
    --condition 'data.status eq "failed"' --action think-summary
# think-summary = HTTP action POST /tasks/ {"prompt":"summarise this build failure", "context":"{{event.data}}"}
```

**17. Wildlife camera log**
```bash
opal look monitors add --id trail --name trail --source-id trail-cam \
    --pipeline-id detect-pipe --restart-policy always
opal look rules add --id deer --name deer --source-id trail-cam \
    --kind object_appears --class-filters '["deer","fox"]' --clip-on-match
opal look artifacts list --json | jq '.items | length'      # the season's clips
opal look jobs submit --kind export_annotated_video --media-id trail-week.mp4
```

**18. Shop-door counter**
```bash
opal look zones add --id door-line --source-id shop-cam --name threshold --kind line --points '[[0,.5],[1,.5]]'
opal look rules add --id footfall --name footfall --source-id shop-cam \
    --kind line_crosses --zone-id door-line --class-filters '["person"]'
opal event stats --json | jq '.topics["opal.look.condition.matched"]'   # daily count
```

**19. Elder-care check-in**
```bash
opal look rules add --id still --name "no movement 4h" --source-id living \
    --kind dwell_time --minimum-duration-ms 14400000 --cooldown-ms 43200000
opal event rules add --id checkin --topic 'opal.look.condition.matched' \
    --condition 'data.rule_id eq "still"' --action ask-ok
# ask-ok: http → say generate "Are you okay?"; a second rule listens for
# intent.recognized help/no-answer and escalates via HTTP action.
```

**20. "What can you do?" — live tool catalog**
```bash
opal event actions list --json | jq '.[] | {id, description, keywords, suggested_prompts}'
opal think ask "Using these tools, build me a morning routine" \
    --context "$(opal event actions list --json)"
# THINK reads the same self-described catalog EVENT uses for its own actions.
```

---

## Build notes

- **Typer layout**: `App → service → tag-group → command`; options come
  from parameters + request-body fields; kernel-mounted ops need one
  implementation serving all five services.
- **Safety default**: every mutating command does read → `If-Match` →
  write; `--if-match '*'` is the escape hatch.
- **Streams**: `listen recognition stream`, `look sessions stream` /
  `sessions preview`, `think task watch`, `say stream` — SSE and raw-PCM
  pipes are half the value.
- **Coverage is testable**: `tests/test_look_cli.py` already enforces an
  unambiguous `x-opal-cli` on every public LOOK op; the same table-driven
  check can validate a generated tree.
