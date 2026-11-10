# OPAL Cookbook

*Recipes for the `opal` command line — because talking to five REST APIs by hand
is how you end up `curl`-ing into the void.*

This cookbook assumes a hypothetical Typer CLI (`opal`) generated from the
OpenAPI contracts in `openapi/`:

| Root command | Contract | What it does |
|---|---|---|
| `opal say` | `openapi/opal_say.yaml` | Text-to-speech: engines, voices, personas, profiles, generation |
| `opal listen` | `openapi/opal_listen.yaml` | Wakewords, STT, intents, slots, regression testing |
| `opal look` | `openapi/opal_look.yaml` | Vision: sources, pipelines, zones, rules, monitors, sessions, jobs |
| `opal think` | `openapi/opal_think.yaml` | LLM tasks, chat sessions, models |
| `opal event` | `openapi/opal_event.yaml` | Event bus: publish, topics, rules, actions, executions |

## Conventions

- **Canonical verbs**: resource management is `list | add | show | update | remove`.
  Operational verbs keep their names (`start`, `stop`, `stream`, `probe`,
  `capture`, `validate`, `execute`, `test`, `promote`, `run`, `watch`, `cancel`,
  `download`, `upload`, `preview`, `submit`, `activate`, `set`).
- **Parents**: `config` groups mutable configuration resources (voices, intents,
  pipelines, zones, rules, actions, profiles, personas, settings). `data` groups
  history and retained artifacts (events, executions, observations, captures,
  recordings, jobs, failed utterances). `info` groups health/metrics/discovery.
- **ETags**: mutable config requires `If-Match`. The CLI fetches the current
  ETag for you; pass `--if-match` only if you want to be stubborn about it.
- **JSON options**: anything that takes an object in the REST body takes inline
  JSON on the CLI (`--data '{...}'`, `--conditions '[...]'`). `@file.json` reads
  from a file.
- **Binary output**: commands that return audio/images/video take `--out`.
  Streaming commands (`stream`, `watch`, `preview`, `stream-results`) run until
  Ctrl+C or the server ends the stream.
- **`--json`**: every command accepts `--json` for machine-readable output.
  `generate`/`stream` accept `--text-file -` to read text from stdin.

---

## OVERVIEW

### Typer command tree

```
opal
├── say
│   ├── generate            speak text → completed WAV/PCM file
│   ├── stream              speak text → live raw PCM stream
│   ├── engine              list | show | update | validate
│   ├── config
│   │   ├── voice           list | add | show | update | remove | validate | test
│   │   ├── profile         list | add | show | update | remove | activate
│   │   ├── persona         list | add | show | update | remove | validate
│   │   └── setting         list | show | set | remove
│   ├── info                health | version | ping | live | ready
│   └── backup              list | create | download | restore | remove | export | import | validate
│
├── listen
│   ├── recognition         test-text | test-audio | start | stop | status | stream
│   ├── config
│   │   ├── wakeword        list | add | show | update | remove
│   │   ├── intent          list | add | show | update | remove
│   │   │   └── phrase      list | add | remove
│   │   ├── slot            list | add | show | update | remove
│   │   │   ├── value       list | add | remove
│   │   │   └── alias       list | add | remove
│   │   ├── profile         list | add | show | update | remove | activate
│   │   ├── persona         list | add | show | update | remove | validate
│   │   └── setting         list | show | set | remove
│   ├── data
│   │   └── failed-utterance  list | add | show | update | remove | promote
│   ├── regression          list | add | show | update | remove | run
│   ├── performance         last | summary | history
│   ├── info                health | audio-devices | version | ping | live | ready
│   └── backup              list | create | download | restore | remove | export | import | validate
│
├── look
│   ├── analyze             run | image
│   ├── session             start | list | show | stop | stream | preview
│   ├── source              list | add | show | update | remove | status | probe | frame | capture | stream
│   ├── engine              list | show | update
│   ├── config
│   │   ├── model           list | add | show | update | remove
│   │   ├── pipeline        list | add | show | update | remove | validate
│   │   ├── zone            list | add | show | update | remove
│   │   ├── rule            list | add | show | update | remove
│   │   ├── monitor         list | add | show | update | remove
│   │   ├── profile         list | add | show | update | remove | activate
│   │   ├── persona         list | add | show | update | remove | validate
│   │   └── setting         list | show | set | remove
│   ├── data
│   │   ├── job             submit | list | show | cancel
│   │   ├── observation     list | show
│   │   ├── media           upload | list | show | remove
│   │   ├── capture         list | show | remove | download
│   │   ├── artifact        list | show | remove | download
│   │   └── recording       start | list | show | stop
│   ├── info                capabilities | health | version | ping | live | ready | metrics | events
│   └── backup              list | create | download | restore | remove | export | import | validate
│
├── think
│   ├── ask                 create a task and print the answer
│   ├── chat                multi-turn chat bound to a session
│   ├── task                create | list | show | watch | cancel
│   ├── session             add | list | show | remove
│   ├── model               list | show
│   ├── config
│   │   ├── profile         list | add | show | update | remove | activate
│   │   ├── persona         list | add | show | update | remove | validate
│   │   └── setting         list | show | set | remove
│   ├── info                health | version | ping | live | ready
│   └── backup              list | create | download | restore | remove | export | import | validate
│
└── event
    ├── publish             publish one event (202 → PublishReceipt)
    ├── topic               list
    ├── action              execute
    ├── config
    │   ├── rule            list | add | show | update | remove | test
    │   ├── action          list | add | show | update | remove
    │   ├── profile         list | add | show | update | remove | activate
    │   ├── persona         list | add | show | update | remove | validate
    │   └── setting         list | show | set | remove
    ├── data
    │   ├── event           list | show | remove | clear
    │   └── execution       list | show
    ├── info                health | stats | version | ping | live | ready
    └── backup              list | create | download | restore | remove | export | import | validate
```

### REST tree (contract paths)

Every service mounts the shared kernel routes (`opal_kernel.yaml`):
`GET /api/v1/health/ | /health/live | /health/ready`, `GET|PATCH /api/v1/setting/`,
`GET|PUT|DELETE /api/v1/setting/{key}`, `GET /api/v1/info/`, `GET /api/v1/info/ping`,
`POST /api/v1/backup/create`, `GET /api/v1/backup/list`,
`GET /api/v1/backup/download/{filename}`, `POST /api/v1/backup/restore/{filename}`,
`DELETE /api/v1/backup/{filename}`, `GET /api/v1/backup/export`,
`POST /api/v1/backup/import`, `POST|GET /api/v1/backup/validate`,
`GET|POST /api/v1/profile/`, `GET|PATCH|DELETE /api/v1/profile/{id}`,
`POST /api/v1/profile/{id}/activate`, plus `GET|POST /api/v1/persona/`,
`GET|PATCH|DELETE /api/v1/persona/{id}`, `POST /api/v1/persona/{id}/validate`.

**opal-say** (`http://127.0.0.1:8080` illustrative)

```
POST /api/v1/generate                          completed WAV/PCM
POST /api/v1/generate/stream                   progressive raw PCM (s16le mono)
GET  /api/v1/engine/                           list engines
GET|PATCH /api/v1/engine/{engine_id}           show/configure engine
POST /api/v1/engine/{engine_id}/validate       engine health check
GET|POST /api/v1/voice/                        list/register voices
GET|PATCH|DELETE /api/v1/voice/{voice_id}      voice lifecycle
POST /api/v1/voice/{voice_id}/validate         voice check
POST /api/v1/voice/{voice_id}/test             short audition clip
```

**opal-listen**

```
GET|POST /api/v1/wakeword/                     wakeword catalog
GET|PATCH|DELETE /api/v1/wakeword/{id}
GET|POST /api/v1/intent/                       intents (+phrases on read)
GET|PATCH|DELETE /api/v1/intent/{id}
GET|POST /api/v1/intent/{id}/phrase            phrase training data
DELETE /api/v1/intent/{id}/phrase/{phrase_id}
GET|POST /api/v1/slot/                         slots
GET|PATCH|DELETE /api/v1/slot/{id}
GET|POST /api/v1/slot/{id}/value               slot values
DELETE /api/v1/slot/{id}/value/{value_id}
GET|POST /api/v1/slot/{id}/value/{vid}/alias   spoken aliases
DELETE /api/v1/slot/{id}/value/{vid}/alias/{aid}
POST /api/v1/recognition/test_text             dry-run text through NLU
POST /api/v1/recognition/test_audio            dry-run .wav through STT+NLU
POST /api/v1/recognition/start|stop            live mic pipeline
GET  /api/v1/recognition/status                metrics snapshot
GET  /api/v1/recognition/stream                SSE live results
GET|POST /api/v1/failed_utterance/             miss review queue
GET|PATCH|DELETE /api/v1/failed_utterance/{id}
POST /api/v1/failed_utterance/{id}/promote     promote miss → phrase (+regression)
GET|POST /api/v1/regression/                   regression cases
POST /api/v1/regression/run                    run the suite
GET|PATCH|DELETE /api/v1/regression/{id}
GET  /api/v1/performance/last|summary|history
GET  /api/v1/health/audio_devices
```

**opal-look**

```
GET  /api/v1/capabilities/                     runtime feature catalog
GET  /api/v1/engine/ | /api/v1/engine/{id}     inference engines
GET|POST /api/v1/model/                        model registry
GET|PATCH|DELETE /api/v1/model/{id}
GET|POST /api/v1/source/                       cameras/files/streams
GET|PATCH|DELETE /api/v1/source/{id}
GET  /api/v1/source/{id}/status|frame|stream   connectivity / JPEG / MJPEG
POST /api/v1/source/{id}/probe|capture/
GET|POST /api/v1/pipeline/                     stage DAGs (preprocess→inference→annotate)
POST /api/v1/pipeline/validate                 dry-run topology check
GET|PATCH|DELETE /api/v1/pipeline/{id}
GET|POST /api/v1/zone/ | /api/v1/zone/{id}     polygons & tripwires
GET|POST /api/v1/rule/  | /api/v1/rule/{id}    observation rules
GET|POST /api/v1/monitor/ | /api/v1/monitor/{id}  always-on desired state
POST /api/v1/analyze/                          synchronous single-frame
POST /api/v1/analyze/image                     multipart still
POST /api/v1/session/                          admit live analysis
GET|POST /api/v1/session/{id}/stop|stream|preview
GET|POST /api/v1/job/                          finite jobs (video analyze/export/clip)
POST /api/v1/job/{id}/cancel
GET  /api/v1/observation/ | /{id}              immutable results
POST|GET /api/v1/media/ | /{id}                uploaded inputs
GET|POST /api/v1/capture/ | /{id} | /{id}/content   retained snapshots
GET /api/v1/artifact/ | /{id} | /{id}/content  derived videos/clips
POST|GET /api/v1/recording/ | /{id} | /{id}/stop
GET  /api/v1/metrics/ | /api/v1/events/status
```

**opal-think**

```
POST /api/v1/task/                             create task (prompt, model, context)
GET  /api/v1/task/ | /{id}                     retained tasks (bounded list)
GET  /api/v1/task/{id}/stream                  SSE task.watch
POST /api/v1/task/{id}/cancel
POST|GET /api/v1/session/ | /{id}              conversation containers
GET  /api/v1/model/ | /{id}                    provider-discovered models
```

**opal-event**

```
POST /api/v1/event/                            publish (202 accepted)
GET|DELETE /api/v1/event/ | /{id}              stored event log
GET  /api/v1/topic/                            observed topics
GET|POST /api/v1/rule/ | /{id}                 topic + conditions → actions
POST /api/v1/rule/{id}/test                    dry-run match
GET|POST /api/v1/action/ | /{id}               shell | http | python actions
POST /api/v1/action/{id}/execute               manual fire
GET  /api/v1/execution/ | /{id}                execution records
GET  /api/v1/stats/                            counters
```

---

## USECASES

### opal say — give your apps a larynx

**1. Say hello (literally).**

```bash
opal say generate --text "Hello from OPAL Say." --out hello.wav
```

**2. Speak as fast as your deadlines move.**

```bash
opal say generate --text "This meeting could have been an event." \
  --voice en-us-lessac-medium --speed 1.6 --volume 1.2 --output-format wav \
  --out standup.wav
```

**3. Stream speech as it is synthesized** (raw s16le PCM, sample rate comes back
in `X-Opal-Sample-Rate`).

```bash
opal say stream --text "Streaming begins before the sentence is finished." \
  --sample-rate 22050 --out hello.pcm
```

**4. See which TTS engines are installed and healthy.**

```bash
opal say engine list
opal say engine validate piper
```

**5. Register a host voice file as an OPAL voice.**

```bash
opal say config voice add \
  --voice-id en-us-lessac-medium \
  --name "Lessac Medium" \
  --engine piper \
  --engine-voice-ref /opt/opal/voice/en_US-lessac-medium.onnx \
  --language en-US
opal say config voice list --language en
```

**6. Audition a voice before committing to it.**

```bash
opal say config voice test en-us-lessac-medium \
  --text "Do I sound like a person who reads documentation?" --out audition.wav
```

**7. Give Amy an identity.**

```bash
opal say config persona add --persona-id amy --name Amy \
  --voice en-gb-alan-low --description "Calm British narrator"
opal say generate --text "Amy has entered the chat." --persona amy --out amy.wav
```

**8. Build a quiet-evening generation profile and make it the default.**

```bash
opal say config profile add --name evening \
  --voice en-gb-alan-low --speed 0.85 --volume 0.7 --output-format wav
opal say config profile activate <profile_id>
opal say generate --text "Defaults applied." --out evening.wav
```

**9. Flip a runtime setting, check whether it needs a restart.**

```bash
opal say config setting show max_text_length
opal say config setting set max_text_length 4096
opal say info health          # pending_restart fields appear here
```

**10. Snapshot the whole voice configuration for the new box.**

```bash
opal say backup create
opal say backup export --out say-config.json
# ... on the new host:
opal say backup validate say-config.json
opal say backup import say-config.json
```

### opal listen — teach the machine to take orders

**1. Register the wakeword.**

```bash
opal listen config wakeword add --name opal --confidence-threshold 0.8
opal listen config wakeword list
```

**2. Teach it what "lights on" means.**

```bash
opal listen config intent add --name lights.turn_on \
  --description "Turn on a room's lights" \
  --confidence-threshold 0.7 \
  --phrase "turn on the lights" \
  --phrase "lights on" \
  --phrase "let there be light"
```

**3. Add the stragglers later.**

```bash
opal listen config intent phrase add 1 --phrase "hit the lights"
opal listen config intent phrase list 1
```

**4. Build a `room` slot with values and spoken aliases.**

```bash
opal listen config slot add --name room --slot-type list
opal listen config slot value add 1 --value kitchen
opal listen config slot value add 1 --value living_room
opal listen config slot alias add 1 2 --alias "the lounge"
opal listen config slot alias add 1 2 --alias "front room"
```

**5. Dry-run a sentence through the NLU (no mic required).**

```bash
opal listen recognition test-text --text "turn on the kitchen lights"
```

**6. Dry-run a recorded .wav through the full STT + intent pipeline.**

```bash
opal listen recognition test-audio ./samples/lights_on.wav
```

**7. Go live and watch matches arrive over SSE.**

```bash
opal listen recognition start
opal listen recognition status
opal listen recognition stream      # Ctrl+C to stop watching (pipeline keeps running)
opal listen recognition stop
```

**8. Triage what it didn't understand.**

```bash
opal listen data failed-utterance list
opal listen data failed-utterance show 7
opal listen data failed-utterance update 7 --expected-intent lights.turn_on --reviewed
```

**9. Turn a miss into training data and a guardrail.**

```bash
opal listen data failed-utterance promote 7 \
  --intent-name lights.turn_on --create-regression
```

**10. Prove the fix sticks, then brag with numbers.**

```bash
opal listen regression run
opal listen performance last
opal listen performance summary
opal listen performance history --limit 20
```

### opal look — eyes on everything

**1. Ask the box what it can actually do.**

```bash
opal look info capabilities
opal look engine list
```

**2. Register a detection model.**

```bash
opal look config model add --id yolo-people --engine onnx \
  --resource-ref /models/yolov8n.onnx --task detect
opal look config model list
```

**3. Register the front-door camera and probe it.**

```bash
opal look source add --id cam-front --kind rtsp \
  --name "Front Door" \
  --locator rtsp://192.168.1.50:554/stream1 --secret-ref cam-front-creds
opal look source probe cam-front
opal look source status cam-front
```

**4. Sneak a JPEG without starting any inference.**

```bash
opal look source frame cam-front --out front.jpg
opal look source capture cam-front --retain --out porch-shot.json
```

**5. Assemble a detect→track→annotate pipeline — dry-run the topology first,
then commit it.**

```bash
opal look config pipeline validate --id detect-people --name "Person pipeline" \
  --stages '[
    {"id":"infer","kind":"inference","model_id":"yolo-people","task":"detect"},
    {"id":"track","kind":"tracker","inputs":["infer"]},
    {"id":"draw","kind":"annotate","inputs":["track"]}
  ]'
opal look config pipeline add --id detect-people --name "Person pipeline" \
  --stages '[
    {"id":"infer","kind":"inference","model_id":"yolo-people","task":"detect"},
    {"id":"track","kind":"tracker","inputs":["infer"]},
    {"id":"draw","kind":"annotate","inputs":["track"]}
  ]'
```

**6. Run one frame through it, synchronously.**

```bash
opal look analyze run --source cam-front --pipeline detect-people
```

**7. Analyze a still image you already have.**

```bash
opal look analyze image ./evidence/suspect_squirrel.jpg --pipeline detect-people
```

**8. Fence off the front yard and arm a rule.**

```bash
opal look config zone add --id zone-yard --source cam-front \
  --name "Front Yard" --kind polygon \
  --points '[[0.05,0.55],[0.95,0.55],[0.95,1.0],[0.05,1.0]]'
opal look config rule add --id person-in-yard --name "Person in yard" \
  --source cam-front --zone zone-yard --kind enters_zone \
  --class-filters '["person"]' --cooldown-ms 30000 --capture-on-match
```

**9. Put it on permanent duty with a self-healing monitor.**

```bash
opal look config monitor add --id mon-front --name "Front watch" \
  --source cam-front --pipeline detect-people --restart-policy always
opal look config monitor show mon-front        # note current_session_id
opal look session stream <session_id>          # live observations over SSE
```

**10. Record evidence and pull the clip.**

```bash
opal look data recording start --source cam-front --max-duration-seconds 120
opal look data recording list
opal look data recording stop <recording_id>   # finalizes an artifact
opal look data artifact list
opal look data artifact download <artifact_id> --out evidence.mp4
```

### opal think — a brain in a jar, with a REST API

**1. Ask a question, get an answer.**

```bash
opal think ask "What is the airspeed velocity of an unladen swallow?"
```

**2. Bound the brainstorming.**

```bash
opal think task create --prompt "Summarize this log" \
  --model ollama:llama3.2 --max-steps 5 --timeout-seconds 120
opal think task watch <task_id>      # SSE: progress + streamed output
```

**3. See what it's been thinking about.**

```bash
opal think task list --status completed --limit 10
opal think task show <task_id>
```

**4. Abort before it achieves sentience.**

```bash
opal think task cancel <task_id>
opal think task show <task_id>       # status: cancelled
```

**5. Hold an actual conversation.**

```bash
opal think session add --title "Weekend project planning"
opal think task create --session <session_id> \
  --prompt "I want to build a robot butler. Step one?"
opal think task create --session <session_id> \
  --prompt "Make step one cheaper."
opal think session show <session_id>
```

**6. Check which brains are on the shelf.**

```bash
opal think model list
opal think model show ollama:llama3.2   # streaming? tool_calling? vision?
```

**7. Register the suite persona so Think knows who's talking.**

```bash
opal think config persona add --persona-id amy --name Amy \
  --voice en-gb-alan-low --description "Calm British narrator"
opal think config persona list
```

**8. Retarget the default model fleet-wide.**

```bash
opal think config setting show default_model
opal think config setting set default_model '"ollama:llama3.2"'
```

**9. Ship context with the prompt** (untrusted data, not instructions).

```bash
opal think task create --prompt "Classify this alert" \
  --context '{"topic":"vision.person","camera":"cam-front","confidence":0.93}'
```

**10. Snapshot the config before the experiment.**

```bash
opal think backup create
opal think info health
```

### opal event — the office gossip network, but reliable

**1. Publish your first rumor.**

```bash
opal event publish --topic home.test \
  --data '{"message":"the event bus works"}' --source cli
```

**2. Read the news feed.**

```bash
opal event data event list --topic home.test --limit 10
opal event topic list
```

**3. Register an HTTP action that calls your notifier.**

```bash
opal event config action add --id send_notification --type http \
  --method POST --url http://127.0.0.1:9000/notify \
  --body-mode event_json --timeout-seconds 15 \
  --description "Forward matched events to the notification bridge"
```

**4. Register a shell action that runs a local script.**

```bash
opal event config action add --id announce_person --type shell \
  --mode bash --script-path /opt/opal/scripts/announce.sh \
  --args '["{{data.camera}}"]' --stdin event_json --timeout-seconds 30
```

**5. Register a Python action.**

```bash
opal event config action add --id process_detection --type python \
  --module opal_plugins.detection --function handle_event \
  --timeout-seconds 30
```

**6. Guard an action with an input contract.**

```bash
opal event config action update announce_person \
  --input-schema '{
    "type":"object",
    "properties":{"camera":{"type":"string"}},
    "required":["camera"]
  }'
```

**7. Wire a rule: person seen on any vision topic → announce + notify.**

```bash
opal event config rule add --id front_door_alert --topic 'vision.*' \
  --conditions '[{"path":"data.object","operator":"eq","value":"person"}]' \
  --actions '["announce_person","send_notification"]'
```

**8. Prove the match before arming it.**

```bash
opal event config rule test front_door_alert \
  --event '{"topic":"vision.cam-front","data":{"object":"person"}}'
# → matched: true, action_ids: [announce_person, send_notification]
```

**9. Fire an action by hand for rehearsal.**

```bash
opal event action execute announce_person \
  --event '{"topic":"test.drill","data":{"camera":"cam-front"}}'
opal event data execution list --limit 5
opal event data execution show <execution_id>
```

**10. Read the scoreboard.**

```bash
opal event info stats
opal event data execution list --limit 20
```

---

## COMBINED

Fifty recipes that make the suite worth more than the sum of its ports.
Grouped by what you get out of them, not by which services they abuse.

### A. The Voice Lab (say + listen + think)

**1. The persona lineup test.** Generate the same trigger phrase in every
registered persona's voice, then verify the NLU still recognizes the intent
regardless of who's speaking.

```bash
opal say config persona list --json > personas.json
# for each persona_id:
opal say generate --text "turn on the kitchen lights" --persona amy --out amy.wav
opal say generate --text "turn on the kitchen lights" --persona bob --out bob.wav
opal say generate --text "turn on the kitchen lights" --persona carl --out carl.wav
opal listen recognition test-audio amy.wav
opal listen recognition test-audio bob.wav
opal listen recognition test-audio carl.wav
# all three should report intent = lights.turn_on
```

**2. Accent-proof the regression suite.** Bake the synthetic misses straight
into the guardrails.

```bash
opal listen regression add --name "amy says lights on" \
  --phrase "turn on the kitchen lights" --expected-intent lights.turn_on
opal listen regression add --name "bob says lights on" \
  --phrase "turn on the kitchen lights" --expected-intent lights.turn_on
opal listen regression run
```

**3. Ask the suite out loud.** Think's answer comes back as text; Say reads it
into a file you can actually hear.

```bash
opal think ask "Explain entanglement in one sentence" --json > answer.json
opal say generate --text-file answer.json --persona amy --out physics.wav
```

**4. The Socratic intercom.** Speak a question at the mic, get a spoken answer.

```bash
opal listen recognition start
# you say: "opal, ask the thinker what the weather means"
# (a small event rule forwards question text; see #9 for the glue)
opal think task create --prompt "Answer in one short spoken-style sentence: what does 'scattered showers' mean?"
opal say stream --text-file - --persona amy --out answer.pcm
```

**5. Verbal quiz night.** Think writes the questions, Say reads them, Listen
scores the answers.

```bash
opal think task create --prompt "Write 5 pub-trivia questions with short answers" --json > quiz.json
opal say generate --text-file quiz.json --persona amy --out quiz-round1.wav
opal listen recognition test-audio contestant_answer.wav   # grade the reply
```

**6. Math drill sergeant.**

```bash
opal think task create --prompt "Give me one mental-math question, difficulty: medium" --json > q.json
opal say generate --text-file q.json --out question.wav
opal listen recognition test-text --text "forty two"
opal think task create --prompt "The question was '17 plus 25'. The answer given was 'forty two'. Reply 'correct' or 'wrong, it is 42'."
opal say generate --text-file - --out verdict.wav
```

**7. Random fact dispenser.**

```bash
opal think task create --prompt "Tell me one surprising true fact, one sentence" --json > fact.json
opal say generate --text-file fact.json --persona carl --out fact-of-the-hour.wav
```

**8. Story time.** "Make up a story about a robot who discovers jazz."

```bash
opal think task create \
  --prompt "Make up a 60-second bedtime story about a robot who discovers jazz" \
  --json > story.json
opal say generate --text-file story.json --persona amy --speed 0.9 --out storytime.wav
```

**9. Teach Listen to catch "ask the thinker" intent and route it.**

```bash
opal listen config intent add --name think.ask \
  --phrase "ask the thinker" --phrase "hey thinker" --phrase "ask the brain"
opal event config action add --id think_dispatch --type http \
  --method POST --url http://127.0.0.1:8084/api/v1/task/ --body-mode event_json
opal event config rule add --id ask_the_thinker --topic 'opal.listen.intent.match' \
  --conditions '[{"path":"data.intent","operator":"eq","value":"think.ask"}]' \
  --actions '["think_dispatch"]'
```

**10. Pronunciation QA.** Generate tongue twisters, round-trip them through STT.

```bash
opal say generate --text "She sells seashells by the seashore" \
  --voice en-us-lessac-medium --speed 1.0 --out twister.wav
opal listen recognition test-audio twister.wav
```

### B. The Watchtower (look + event + say)

**11. "Someone's in the front yard" — the original request.** Zone rule fires,
Event announces, Say says so.

```bash
opal look config rule add --id yard-person --name "Person in front yard" \
  --source cam-front --zone zone-yard --kind enters_zone \
  --class-filters '["person"]' --capture-on-match --cooldown-ms 60000

opal event config action add --id say_yard_alert --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body-mode template \
  --body '{"text":"Attention. A person is in the front yard.","output_format":"wav"}'

opal event config rule add --id verbal_yard_alert --topic 'opal.look.rule.*' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"yard-person"}]' \
  --actions '["say_yard_alert"]'
```

**12. Package delivery announcement.**

```bash
opal look config rule add --id package-seen --name "Package on porch" \
  --source cam-front --kind object_appears --class-filters '["package"]' \
  --capture-on-match
opal event config action add --id say_package --type http \
  --method POST --url http://127.0.0.1:8081/api/v1/generate \
  --body '{"text":"A package has arrived at the door.","output_format":"wav"}' \
  --body-mode template
opal event config rule add --id package_rule --topic 'opal.look.rule.*' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"package-seen"}]' \
  --actions '["say_package","send_notification"]'
```

**13. Pet vs. person discrimination.** Only announce humans; the cat is on her own.

```bash
opal event config rule add --id people_only --topic 'vision.*' \
  --conditions '[
    {"path":"data.label","operator":"eq","value":"person"},
    {"path":"data.confidence","operator":"gte","value":0.8}
  ]' \
  --actions '["say_yard_alert"]'
```

**14. Loitering alarm.** Dwell time, not just presence.

```bash
opal look config rule add --id loiter --name "Loitering" \
  --source cam-front --zone zone-yard --kind dwell_time \
  --class-filters '["person"]' --threshold 120000 --capture-on-match
```

**15. Gate tripwire counter.** Line-cross events become statistics.

```bash
opal look config zone add --id gate-line --source cam-front \
  --name "Gate line" --kind line --points '[[0.4,0.0],[0.4,1.0]]'
opal look config rule add --id gate-cross --name "Gate crossed" \
  --source cam-front --zone gate-line --kind line_crosses \
  --class-filters '["person"]'
opal event data event list --topic opal.look.rule.gate-cross
```

**16. Evidence reel.** On trigger, record two minutes and keep the clip.

```bash
opal event config action add --id start_recording --type http \
  --method POST --url http://127.0.0.1:8082/api/v1/recording/ \
  --body '{"source_id":"cam-front","max_duration_seconds":120}' --body-mode template
opal event config rule add --id record_on_person --topic 'vision.*' \
  --conditions '[{"path":"data.label","operator":"eq","value":"person"}]' \
  --actions '["start_recording"]'
opal look data artifact list        # the mp4 lands here when the recording stops
```

**17. Camera-down watchdog.** Source health becomes a spoken alert.

```bash
opal look source status cam-front
opal event config rule add --id cam_down --topic 'opal.look.source.*' \
  --conditions '[{"path":"data.state","operator":"eq","value":"disconnected"}]' \
  --actions '["say_yard_alert","send_notification"]'
```

**18. Nightly capture audit.** Pull retained captures triggered by rules.

```bash
opal look data capture list --limit 50
opal look data capture download <capture_id> --out captures/nightly.jpg
```

**19. Ask the house what it saw.** Observations → Think → spoken summary.

```bash
opal look data observation list --source cam-front --label person \
  --after 2026-11-09T00:00:00Z --json > today.json
opal think task create --prompt "Summarize these camera observations in one spoken sentence" \
  --context @today.json --json > summary.json
opal say generate --text-file summary.json --persona amy --out daily-brief.wav
```

**20. Front-door concierge.** Person at door → snap frame → announce with name
guess attempt. (The guess is aspirational. The announcement is real.)

```bash
opal event config action add --id snap_and_say --type python \
  --module opal_plugins.door --function greet_visitor --timeout-seconds 30
opal event config rule add --id door_concierge --topic 'opal.look.rule.*' \
  --conditions '[{"path":"data.rule_id","operator":"eq","value":"yard-person"}]' \
  --actions '["snap_and_say"]'
```

### C. The Concierge (listen + think + say + event)

**21. "Opal, what's on my cameras?"** Wakeword → intent → Look query → spoken answer.

```bash
opal listen config intent add --name look.describe \
  --phrase "what do you see" --phrase "what's on the camera" --phrase "describe the camera"
opal think task create \
  --prompt "Describe this scene in one spoken sentence" \
  --context '{"camera":"cam-front"}'
opal say stream --text-file - --persona amy --out scene.pcm
```

**22. Voice-controlled profile switch.** "Opal, use your quiet voice."

```bash
opal listen config intent add --name say.profile \
  --phrase "use your quiet voice" --phrase "switch to evening mode"
opal event config rule add --id quiet_voice --topic 'opal.listen.intent.match' \
  --conditions '[{"path":"data.intent","operator":"eq","value":"say.profile"}]' \
  --actions '["activate_evening_profile"]'
opal say config profile activate <evening_profile_id>
```

**23. Spoken uptime report.**

```bash
opal say info health --json > say-health.json
opal look info metrics --json > look-metrics.json
opal think task create --prompt "One sentence: are all services healthy?" \
  --context @say-health.json --json > verdict.json
opal say generate --text-file verdict.json --out status.wav
```

**24. Dictation capture.** Speak, Listen transcribes, Think cleans it up, file it.

```bash
opal listen recognition test-audio dictation.wav --json > raw.json
opal think task create --prompt "Clean this transcript into a polished paragraph" \
  --context @raw.json --json > polished.json
```

**25. The dinner bell.** Scheduled intent → broadcast on every persona.

```bash
opal event publish --topic home.dinner --data '{"msg":"Dinner is served"}'
opal event config rule add --id dinner_bell --topic 'home.dinner' \
  --conditions '[]' --actions '["say_dinner_all_personas"]'
```

**26. Alarm acknowledgment.** Say it hears you, then stand down.

```bash
opal listen config intent add --name alarm.ack \
  --phrase "I heard the alarm" --phrase "acknowledged"
opal event config rule add --id ack_alarm --topic 'opal.listen.intent.match' \
  --conditions '[{"path":"data.intent","operator":"eq","value":"alarm.ack"}]' \
  --actions '["stop_siren","say_acknowledged"]'
```

**27. Voice notes → task queue.** Spoken todo becomes a Think task for triage.

```bash
opal listen config intent add --name todo.add --phrase "remind me to" --phrase "add a note"
opal think task create --prompt "Extract the action item from this transcript" \
  --context '{"transcript":"remind me to water the ferns"}'
```

**28. Multi-room announcement.** One event, many mouths.

```bash
opal event publish --topic home.announce --data '{"text":"Meeting in five"}'
opal event config rule add --id announce_everywhere --topic 'home.announce' \
  --conditions '[]' \
  --actions '["say_kitchen","say_office","say_garage"]'
```

**29. The "did I lock the door" routine.**

```bash
opal listen config intent add --name home.status --phrase "is the house secure"
opal think task create --prompt "Answer based on context: is the house secure?" \
  --context '{"locks":{"front":"locked","back":"unlocked"},"cameras":"ok"}'
opal say generate --text-file - --persona amy --out security-report.wav
```

**30. Language lesson.** Think quizzes, Say speaks, Listen listens, repeat.

```bash
opal think task create --prompt "Give me a French phrase to practice, then its English" --json > lesson.json
opal say generate --text-file lesson.json --persona amy --out french.wav
opal listen recognition test-audio attempt.wav   # did they nail "écureuil"?
```

### D. The Game Room (think + say + listen)

**31. Twenty questions, spoken.**

```bash
opal think session add --title "Twenty Questions"
opal think task create --session <sid> --prompt "I am thinking of something. Ask me yes/no question one."
opal say stream --text-file - --out q1.pcm
opal listen recognition test-text --text "is it bigger than a breadbox? yes"
opal think task create --session <sid> --prompt "Answer was yes. Ask question two."
```

**32. Spelling bee.**

```bash
opal think task create --prompt "Pick a hard spelling-bee word, give just the word" --json > word.json
opal say generate --text-file word.json --speed 0.8 --out spell-me.wav
opal listen recognition test-text --text "o n o m a t o p o e i a"
opal think task create --prompt "The word was onomatopoeia. Spelling given: o n o m a t o p o e i a. Reply correct or wrong."
```

**33. Riddle me this.**

```bash
opal think task create --prompt "Tell me a riddle" --json > riddle.json
opal say generate --text-file riddle.json --persona carl --out riddle.wav
# ... later:
opal think task create --prompt "Riddle answer attempt: 'a shadow'. Was that right?"
```

**34. Mad libs generator.**

```bash
opal think task create --prompt "Give me a mad lib: ask for a noun, verb, adjective" --json > blanks.json
opal say generate --text-file blanks.json --out prompt.wav
opal listen recognition test-text --text "penguin, exploded, moist"
opal think task create --prompt "Write a two-sentence story using penguin, exploded, moist" --json > story.json
opal say generate --text-file story.json --out madlib.wav
```

**35. Chess commentary for your webcam match.**

```bash
opal look source capture cam-board --retain
opal think task create --prompt "Describe this chess position dramatically in one line" \
  --context '{"capture_id":"<id>"}'
opal say generate --text-file - --persona carl --out commentary.wav
```

**36. Guess-the-sound game.** Say makes a described sound; you guess.

```bash
opal think task create --prompt "Describe a sound effect for me to imitate vocally, don't say what it is"
opal say generate --text-file - --out mystery-sound.wav
opal listen recognition test-text --text "a cow"
```

**37. Hangman with an audience.**

```bash
opal think session add --title "Hangman"
opal think task create --session <sid> --prompt "Start hangman. Pick a word, show only blanks."
opal listen recognition test-text --text "letter e"
opal think task create --session <sid> --prompt "Guess: e"
```

**38. Trivia league with persistent scoring.**

```bash
opal think task create --prompt "Category: geography. Ask question 3 of 10." --json > q3.json
opal say generate --text-file q3.json --out q3.wav
opal event publish --topic game.trivia --data '{"player":"pat","answer":"oslo","correct":true}'
```

**39. Dungeon master on a budget.**

```bash
opal think session add --title "Campaign: The Basement of Doom"
opal think task create --session <sid> --prompt "You are a DM. Set the opening scene in one spoken paragraph."
opal say stream --text-file - --persona amy --out scene1.pcm
opal listen recognition test-text --text "I check the door for traps"
opal think task create --session <sid> --prompt "Player checks the door for traps. Narrate the result."
```

**40. Karaoke judge.** Sing it, Listen transcribes, Think is Simon Cowell.

```bash
opal listen recognition test-audio ./karaoke/take1.wav --json > vocals.json
opal think task create --prompt "These were the lyrics sung: [context]. Rate the performance in one witty sentence." \
  --context @vocals.json
opal say generate --text-file - --persona carl --out judges-verdict.wav
```

### E. The Janitor's Closet (everything)

**41. Whole-suite morning health check.**

```bash
opal say info health
opal listen info health
opal look info health
opal think info health
opal event info stats
```

**42. Fleet-wide backup Friday.**

```bash
opal say backup create
opal listen backup create
opal look backup create
opal think backup create
opal event backup create
opal say backup list && opal look backup list
```

**43. Migrate the suite to the new host.**

```bash
# old host
opal say backup export --out export/say.json
opal listen backup export --out export/listen.json
opal look backup export --out export/look.json
opal event backup export --out export/event.json
# new host — validate before you commit
opal say backup validate export/say.json
opal say backup import export/say.json
opal look backup validate export/look.json
opal look backup import export/look.json
```

**44. One persona to rule them all.** Register `amy` consistently across the
suite so voice, prompts and events all agree.

```bash
opal say config persona add --persona-id amy --name Amy --voice en-gb-alan-low
opal think config persona add --persona-id amy --name Amy --voice en-gb-alan-low
opal listen config persona add --persona-id amy --name Amy --voice en-gb-alan-low
opal look config persona add --persona-id amy --name Amy --voice en-gb-alan-low
opal event config persona add --persona-id amy --name Amy --voice en-gb-alan-low
opal say config persona validate amy
```

**45. End-to-end wake-to-answer smoke test.**

```bash
opal listen recognition test-text --text "ask the thinker what time it is"
opal event data event list --topic opal.listen.intent.match --limit 1
opal think task list --status completed --limit 1
opal say generate --text "Smoke test complete" --out smoke.wav
```

**46. Event-plumbing sanity check.** Publish a synthetic vision event and watch
the whole rule→action→execution chain light up.

```bash
opal event publish --topic vision.cam-front \
  --data '{"object":"person","camera":"cam-front","confidence":0.99}'
opal event data execution list --limit 5
opal event info stats
```

**47. The audit trail.** When something announced at 3 AM, find out why.

```bash
opal event data execution list --limit 50
opal event data execution show <execution_id>     # which event, which rule
opal event data event show <event_id>             # the event itself
opal look data observation list --job-id <job_id> # what the camera saw
```

**48. Performance day.** Gather every service's numbers before the meeting.

```bash
opal listen performance summary
opal look info metrics
opal event info stats
opal listen recognition status
opal think task list --status timed_out
```

**49. Safe config change with rollback.** ETag-protected edit, backup first.

```bash
opal listen backup create
opal listen config setting show dedup_window_ms
opal listen config setting set dedup_window_ms 5000   # auto If-Match
# something feels off?
opal listen backup restore <filename>
```

**50. The demo.** The whole circus in one act: camera sees a person → event
fires → Think narrates → Say announces.

```bash
# setup (once)
opal look config rule add --id demo-person --name "Demo" --source cam-front \
  --kind object_appears --class-filters '["person"]' --capture-on-match
opal event config action add --id demo_announce --type python \
  --module opal_plugins.demo --function narrate --timeout-seconds 60
opal event config rule add --id demo_rule --topic 'vision.*' \
  --conditions '[{"path":"data.object","operator":"eq","value":"person"}]' \
  --actions '["demo_announce"]'
# showtime — walk into frame, or cheat:
opal event publish --topic vision.cam-front \
  --data '{"object":"person","camera":"cam-front","confidence":0.97}'
opal event data execution list --limit 1
```

---

## Appendix: cheat sheet

| Task | One-liner |
|---|---|
| Speak text | `opal say generate --text "hi" --out hi.wav` |
| Live PCM | `opal say stream --text "hi" --out hi.pcm` |
| Test a phrase | `opal listen recognition test-text --text "lights on"` |
| Test a wav | `opal listen recognition test-audio clip.wav` |
| Snap a frame | `opal look source frame cam-front --out f.jpg` |
| Analyze once | `opal look analyze run --source cam-front --pipeline p1` |
| Ask the brain | `opal think ask "question"` |
| Fire an event | `opal event publish --topic t.x --data '{"k":1}'` |
| Test a rule | `opal event config rule test <id> --event '{...}'` |
| Backup a service | `opal <svc> backup create` |

*No cameras were harmed in the making of this cookbook. The ferns, however,
remain unwatered.*
