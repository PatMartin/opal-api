# The OPAL Ecosystem Cookbook

*One CLI, six services: a registry that knows every microphone and camera, ears that listen, eyes that watch, a brain that reasons, a mouth that speaks, and a switchboard that makes them gossip.*

This cookbook describes the unified `opal` [Typer](https://typer.tiangolo.com/) CLI implied by the v1.7.1 OpenAPI contracts in [`openapi/`](../openapi), the shared kernel at [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml), and the devices base at [`openapi/shared/opal_device_kernel.yaml`](../openapi/shared/opal_device_kernel.yaml). Every command maps to exactly one REST operation in those contracts.

One honest caveat: this repository ships contracts, not an `opal` executable. Treat this as the menu for a restaurant whose kitchen is specified in great detail.

## Contents

- [Introduction](#introduction)
- [CLI Command Tree](#cli-command-tree)
  - [EVENT FLOW](#event-flow)
- [Recipes](#recipes)
  - [opal device](#opal-device)
  - [opal say](#opal-say)
  - [opal listen](#opal-listen)
  - [opal look](#opal-look)
  - [opal think](#opal-think)
  - [opal event](#opal-event)
  - [combined](#combined)

## Introduction

OPAL is a suite of small, single-responsibility HTTP services that cooperate over REST and an event bus instead of one monolithic assistant. Each service owns one sense or faculty; none reaches into another's internals.

| Service | Faculty | What it does |
| --- | --- | --- |
| **Devices** (`opal device`) | Proprioception | Optional registry of device identity, inventory, discovery, capabilities, preferred defaults, groups, labels, and federation peers. It *describes* hardware; it never operates it. |
| **Listen** (`opal listen`) | Hearing | Wakewords, speech-to-text, intent recognition, and slot extraction. Publishes live intent matches to Event. |
| **Look** (`opal look`) | Sight | Cameras, models, detection pipelines, live sessions, finite jobs, recordings, and monitor rules that emit events. |
| **Think** (`opal think`) | Reasoning | Bounded asynchronous tasks on configured models; can discover and invoke Event actions; owns the authoritative persona registry. |
| **Say** (`opal say`) | Voice | Text-to-speech over host-installed engines; voices and personas; returns audio bytes — it never plays them. |
| **Event** (`opal event`) | Nervous system | Event ingress and history, topic rules, registered shell/HTTP/Python actions, and execution records. |

The pieces compose: Devices tells consumers *which* camera or microphone exists and what it can do; Listen and Look observe the world and publish events; Event routes those events through rules to registered actions; an action can kick off a Think task; Think can invoke other actions — including a `speak` action wired to Say.

Cross-cutting conventions come from the shared kernel:

- **Routes** live under `/api/v1` with singular resource names and trailing-slash collections.
- **Correlation** travels in `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, and `X-Opal-Causation-Id`.
- **Configuration** mutations require `If-Match` against a strong ETag — missing is `428`, stale is `412`. The CLI fetches and attaches ETags for you.
- **Personas** resolve as *explicit request field > persona binding > profile > service default*, with Think as the authoritative persona registry.

## CLI Command Tree

```text
opal
├── devices               device registry: identity, inventory, discovery, federation
│   ├── info                  health | live | ready | version | ping
│   ├── catalog
│   ├── list | add | show | update | remove
│   ├── capabilities | status | test
│   ├── discover | watch
│   ├── event                 list
│   ├── default               list | set | remove
│   ├── label                 list | set | remove
│   ├── tag                   list | add | remove
│   ├── group                 list | add | show | update | remove
│   │   └── member            list | add | remove
│   ├── peer                  list | add | show | update | remove | status | sync | discover
│   ├── sharing               list | add | remove          (aliases: allow, deny)
│   ├── plugin                list | show | enable | disable | test | discover
│   ├── federation            inventory | registry
│   ├── config
│   │   ├── setting           list | update | show | set | remove
│   │   └── profile           list | add | show | update | remove | activate
│   ├── backup                list | create | download | restore | remove | export | import | validate
│   └── service               start | stop | log
├── listen                hearing: wakewords, STT, intents, slots
│   ├── config
│   │   ├── wakeword          list | add | show | update | remove
│   │   ├── intent            list | add | show | update | remove
│   │   ├── phrase            list | add | remove
│   │   ├── slot              list | add | show | update | remove
│   │   ├── slot-value        list | add | remove
│   │   ├── slot-alias        list | add | remove
│   │   ├── profile           list | add | show | update | remove | activate
│   │   ├── persona           list | add | validate | show | update | remove
│   │   └── setting           list | update | show | set | remove
│   ├── recognition           test-text | test-audio | start | stop | status | stream
│   ├── data
│   │   └── failed-utterance  list | add | show | update | remove | promote
│   ├── regression            list | add | run | show | update | remove
│   ├── performance           last | summary | history
│   ├── info                  health | audio-devices | version | ping | live | ready
│   ├── backup                list | create | download | restore | remove | export | import | validate
│   └── service               start | stop | log
├── look                  sight: sources, pipelines, sessions, monitors
│   ├── info                  capabilities | health | version | ping | live | ready | metrics | events
│   ├── engine                list | show | update
│   ├── config
│   │   ├── model             list | add | show | update | remove
│   │   ├── pipeline          list | add | show | update | remove | validate
│   │   ├── zone              list | add | show | update | remove
│   │   ├── rule              list | add | show | update | remove
│   │   ├── monitor           list | add | show | update | remove
│   │   ├── profile           list | add | show | update | remove | activate
│   │   ├── persona           list | add | validate | show | update | remove
│   │   └── setting           list | update | show | set | remove
│   ├── source                list | add | show | update | remove | status | probe | frame | capture | stream
│   ├── analyze               run | image
│   ├── session               list | start | show | stop | stream | preview
│   ├── data
│   │   ├── job               list | submit | show | cancel
│   │   ├── observation       list | show
│   │   ├── media             list | upload | show | remove
│   │   ├── capture           list | show | remove | download
│   │   ├── artifact          list | show | remove | download
│   │   └── recording         list | start | show | stop
│   ├── backup                list | create | download | restore | remove | export | import | validate
│   └── service               start | stop | log
├── think                 reasoning: tasks, sessions, models
│   ├── ask                   alias of `task create`
│   ├── chat                  alias of `task create`
│   ├── task                  list | create | show | watch | cancel
│   ├── session               list | add | show | remove
│   ├── model                 list | show
│   ├── config
│   │   ├── profile           list | add | show | update | remove | activate
│   │   ├── persona           list | add | validate | show | update | remove
│   │   └── setting           list | update | show | set | remove
│   ├── info                  health | version | ping | live | ready
│   ├── backup                list | create | download | restore | remove | export | import | validate
│   └── service               start | stop | log
├── say                   voice: TTS over host-installed engines
│   ├── generate | stream
│   ├── engine                list | show | update | validate
│   ├── config
│   │   ├── voice             list | add | show | update | remove | validate | test
│   │   ├── profile           list | add | show | update | remove | activate
│   │   ├── persona           list | add | validate | show | update | remove
│   │   └── setting           list | update | show | set | remove
│   ├── info                  health | version | ping | live | ready
│   ├── backup                list | create | download | restore | remove | export | import | validate
│   └── service               start | stop | log
└── event                 nervous system: publish, rules, actions, executions
    ├── publish
    ├── data
    │   ├── event             list | clear | show | remove
    │   ├── topic             list
    │   └── execution         list | show
    ├── config
    │   ├── rule              list | add | show | update | remove | test
    │   ├── action            list | add | show | update | remove | execute
    │   ├── profile           list | add | show | update | remove | activate
    │   ├── persona           list | add | validate | show | update | remove
    │   └── setting           list | update | show | set | remove
    ├── info                  health | stats | version | ping | live | ready
    ├── backup                list | create | download | restore | remove | export | import | validate
    └── service               start | stop | log
```

### EVENT FLOW

Events travel on topics over the event bus; actions are invoked over REST. Event publication is **best effort** and **disabled by default** on Listen, Look, and Devices — flip the corresponding setting to opt in.

```text
                     publishes (opt-in)                    routes
 LISTEN  ── opal.listen.intent.match ──────┐
                                           │
 LOOK    ── opal.look.observation ─────────┤            ┌──▶ shell/HTTP/Python ACTION
         ── opal.look.condition.matched ───┼──▶ EVENT ──┤       e.g. POST /api/v1/task/ ──▶ THINK
         ── opal.look.monitor.failed ──────┤   rules    │
                                           │            └──▶ shell action `speak` ──▶ opal say generate --play
 DEVICES ── opal.devices.* (opt-in,        │
            disabled by default) ──────────┘

 THINK   ── (no topics) ── discovers & invokes Event actions over REST:
             GET /api/v1/action/  →  POST /api/v1/action/{id}/execute

 DEVICES ── (peer federation over REST, not topics):
             GET /api/v1/federation/inventory ◀── trusted peer registries
```

Fixed by contract: the Listen and Look topic names above. Device event topics are implementation-chosen (`events.publish_enabled=false` until you opt in); `opal device catalog` reports the event names a registry uses.

## Recipes

Assumed ports in the examples: Event `8080`, Say `8081`, Look `8082`, Think `8083`, Devices `8084`, Listen `8000`. IDs like `dev-cam-front` or `tsk-42` are placeholders — use what your services return.

### opal device

**1. See every device this host knows about.**

```bash
opal device list
```

**2. Find an available camera.**

```bash
opal device list --type camera --status available
```

**3. Inventory across the whole federation.**

```bash
opal device federation inventory
```

**4. What is this registry, anyway?**

```bash
opal device federation registry
```

**5. Discover hardware without touching it.**

```bash
opal device discover
```

**6. Register the device the scanner missed.**

```bash
opal device add --name "lab/gpu-0" --type gpu --host-id workstation-2 --host-name "Workstation 2" --backend cuda --access local
```

**7. Read one device's full dossier.**

```bash
opal device show dev-cam-front
```

**8. What can it actually do?**

```bash
opal device capabilities dev-cam-front
```

**9. Is it alive right now?**

```bash
opal device status dev-cam-front
```

**10. Run a safe self-check.**

```bash
opal device test dev-cam-front
```

**11. Make the studio mic the default for everything.**

```bash
opal device default set --scope type --target microphone --values '{"device_id":"dev-3fa8-mic-array"}'
```

**12. Label it so humans can find it.**

```bash
opal device label set dev-cam-front location porch
```

**13. Tag it so filters can find it.**

```bash
opal device tag add dev-cam-front outdoor
```

**14. Group the cameras that matter.**

```bash
opal device group add --name porch-cams --mode static --description "Front and side porch cameras"
opal device group member add grp-porch dev-cam-front
opal device group member add grp-porch dev-cam-side
```

**15. Meet the garage registry.**

```bash
opal device peer add --name garage --base-url http://192.168.1.20:8084 --trusted
opal device peer sync garage
```

**16. Hide the lab GPU from peers.**

```bash
opal device sharing deny --device-id dev-lab-gpu
```

**17. See which discovery backends are installed.**

```bash
opal device plugin list
```

**18. Watch the registry breathe in real time.**

```bash
opal device watch
```

**19. Catch up on what changed while you were out.**

```bash
opal device event list --limit 20
```

**20. Snapshot the registry before a reorg.**

```bash
opal device backup create
```

### opal say

**1. Say it out loud, right now.**

```bash
opal say generate "The build is green. I repeat, the build is green." --play
```

**2. Save a greeting as a WAV file.**

```bash
opal say generate "Welcome to the museum. Please do not lick the exhibits." --out welcome.wav
```

**3. Pick a specific voice.**

```bash
opal say generate "Tea is served in the library." --voice-id en-gb-alan-low --play
```

**4. Speak as a persona and let its bound voice follow.**

```bash
opal say generate "Good evening. I will be your narrator." --persona vox --play
```

**5. Slow down for the people in the back.**

```bash
opal say generate "Your verification code is four, seven, one, nine." --speed 0.8 --play
```

**6. Use an indoor voice.**

```bash
opal say generate "The baby is finally asleep. Nobody move." --volume 0.3 --play
```

**7. Produce raw 16 kHz PCM for a telephony system.**

```bash
opal say generate "Please hold while we connect you." --format pcm --sample-rate 16000 --out hold.pcm
```

**8. Stream speech as it is synthesized.**

```bash
opal say stream "This sentence is being generated as you hear it." --play
```

**9. See which TTS engines are installed.**

```bash
opal say engine list
```

**10. Inspect one engine's details.**

```bash
opal say engine show piper
```

**11. Register a new voice.**

```bash
opal say config voice add --id en-gb-alan-low --engine piper --model en_GB-alan-low --description "Calm British baritone"
```

**12. Prove a voice works before trusting it.**

```bash
opal say config voice validate en-gb-alan-low
```

**13. Audition it.**

```bash
opal say config voice test en-gb-alan-low --text "The rain in Spain stays mainly in the plain." --play
```

**14. Retire a voice you no longer need.**

```bash
opal say config voice remove en-gb-alan-low
```

**15. Switch the active voice profile for quiet hours.**

```bash
opal say config profile add --id night --name "Night" --settings '{"default_volume":0.3}'
opal say config profile activate night
```

**16. Check Say's health.**

```bash
opal say info health
```

**17. Find the service version before filing a bug.**

```bash
opal say info version
```

**18. Back up voice configuration before re-tuning.**

```bash
opal say backup create
```

**19. Validate a staged configuration without applying it.**

```bash
opal say backup validate
```

**20. Read the last few log lines when speech goes silent.**

```bash
opal say service log
```

### opal listen

**1. Start listening for wakeword and intents.**

```bash
opal listen recognition start
```

**2. Is it listening?**

```bash
opal listen recognition status
```

**3. Type what you would have said.**

```bash
opal listen recognition test-text "turn on the porch light"
```

**4. Feed it a WAV instead of a microphone.**

```bash
opal listen recognition test-audio samples/hello.wav
```

**5. Register a wakeword.**

```bash
opal listen config wakeword add --id porcupine-home --phrase "hey house" --sensitivity 0.7
```

**6. Teach it an intent.**

```bash
opal listen config intent add --id lights-on --description "Turn lights on" 
```

**7. Give the intent a phrase.**

```bash
opal listen config phrase add --intent lights-on --text "turn on the {room} light"
```

**8. Declare the {room} slot.**

```bash
opal listen config slot add --intent lights-on --name room --description "Which room"
```

**9. Fill the slot with real rooms.**

```bash
opal listen config slot-value add --slot room --value porch
opal listen config slot-alias add --slot room --value porch --alias front-porch
```

**10. Hear it live.**

```bash
opal listen recognition stream
```

**11. Stop listening.**

```bash
opal listen recognition stop
```

**12. Review what it failed to understand.**

```bash
opal listen data failed-utterance list
```

**13. Promote a misheard phrase into training data.**

```bash
opal listen data failed-utterance promote fu-1024
```

**14. Run the regression suite after retuning.**

```bash
opal listen regression run reg-suite-1
```

**15. How did the last run go?**

```bash
opal listen performance last
```

**16. Weekly accuracy trend.**

```bash
opal listen performance summary
```

**17. History for the graph you'll never draw.**

```bash
opal listen performance history --limit 30
```

**18. Which microphones does it see?**

```bash
opal listen info audio-devices
```

**19. Quiet-hours config.**

```bash
opal listen config profile add --id night --name "Night" --settings '{"wakeword_sensitivity":0.9}'
opal listen config profile activate night
```

**20. Snapshot the intent library before a big edit.**

```bash
opal listen backup create
```

### opal look

**1. List every camera source it knows.**

```bash
opal look source list
```

**2. Register a new camera.**

```bash
opal look source add --id cam-front --uri rtsp://192.168.1.30:554/stream --kind rtsp
```

**3. Is the camera actually reachable?**

```bash
opal look source probe cam-front
```

**4. Grab a single frame.**

```bash
opal look source frame cam-front --out porch.jpg
```

**5. Take a snapshot capture.**

```bash
opal look source capture cam-front
```

**6. What models are installed?**

```bash
opal look config model list
```

**7. Register the person detector.**

```bash
opal look config model add --id yolov8n-person --kind detector --path /models/yolov8n.onnx --labels person
```

**8. Build a detection pipeline.**

```bash
opal look config pipeline add --id porch-people --source cam-front --model yolov8n-person --interval 500
```

**9. Sanity-check the pipeline before enabling it.**

```bash
opal look config pipeline validate porch-people
```

**10. Define the porch zone polygon.**

```bash
opal look config zone add --id zone-porch --source cam-front --polygon "[[0.1,0.3],[0.9,0.3],[0.9,0.9],[0.1,0.9]]"
```

**11. Alert when a person enters the zone.**

```bash
opal look config rule add --id person-on-porch --pipeline porch-people --zone zone-porch --label person --event opal.look.condition.matched
```

**12. Monitor camera uptime.**

```bash
opal look config monitor add --id cam-front-health --source cam-front --type offline --event opal.look.monitor.failed
```

**13. Start a live session.**

```bash
opal look session start --source cam-front --pipeline porch-people
```

**14. Watch the session's event stream.**

```bash
opal look session stream ses-42
```

**15. Peek at the live preview.**

```bash
opal look session preview ses-42 --out preview.jpg
```

**16. Submit a finite batch job over yesterday's captures.**

```bash
opal look data job submit --pipeline porch-people --media-set overnight --notify
```

**17. What did it see?**

```bash
opal look data observation list --source cam-front --label person --limit 10
```

**18. Download the capture that triggered the alert.**

```bash
opal look data capture download cap-808 --out alert.jpg
```

**19. Which optional features does this build have?**

```bash
opal look info capabilities
```

**20. Event wiring check — is Look publishing?**

```bash
opal look info events
```

### opal think

**1. Ask it a question, fire and forget.**

```bash
opal think task create --prompt "Summarize today's commits in one sentence."
```

**2. Or just ask.**

```bash
opal think ask "Explain the difference between a task and a session."
```

**3. Keep the conversation going in a session.**

```bash
opal think session add --id ses-standup
opal think task create --session-id ses-standup --prompt "What did we decide about the release?"
```

**4. See what models it can use.**

```bash
opal think model list
```

**5. Pin the task to a specific model.**

```bash
opal think task create --model ollama:llama3.2 --prompt "Write a haiku about firmware."
```

**6. Give it a leash.**

```bash
opal think task create --prompt "Triage the failing tests." --max-steps 5 --timeout 120
```

**7. Speak as a persona.**

```bash
opal think task create --persona critic --prompt "Review this changelog like a skeptic."
```

**8. Watch the task unfold.**

```bash
opal think task watch tsk-42
```

**9. Check the verdict.**

```bash
opal think task show tsk-42
```

**10. Cancel a runaway.**

```bash
opal think task cancel tsk-42
```

**11. List recent tasks.**

```bash
opal think task list --limit 10
```

**12. Who is 'critic' anyway?**

```bash
opal think config persona show critic
```

**13. Register a new persona.**

```bash
opal think config persona add --id vox --name "Vox" --description "Evening announcer" --voice-id en-gb-alan-low
```

**14. Does a persona resolve cleanly?**

```bash
opal think config persona validate vox
```

**15. Swap to the reasoning-heavy profile.**

```bash
opal think config profile activate deep-thought
```

**16. Point Think at the event bus.**

```bash
opal think config setting set event.base_url '"http://127.0.0.1:8080"'
```

**17. Health check before the demo.**

```bash
opal think info health
```

**18. Export the brain's configuration.**

```bash
opal think backup export --out think-config.yaml
```

**19. Validate a staged config without applying.**

```bash
opal think backup validate
```

**20. Tail the log when answers go quiet.**

```bash
opal think service log
```

### opal event

**1. See the topic firehose.**

```bash
opal event data event list --limit 20
```

**2. Only intent matches.**

```bash
opal event data event list --topic opal.listen.intent.match
```

**3. Which topics have traffic?**

```bash
opal event data topic list
```

**4. Publish a synthetic event.**

```bash
opal event publish --topic opal.test.ping --data '{"text":"hello bus"}'
```

**5. Register a shell action that speaks.**

```bash
opal event config action add --id speak --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","{{data.text}}","--play"]' --stdin none --input-schema '{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}'
```

**6. Register an HTTP action that submits a Think task.**

```bash
opal event config action add --id think-it --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"{{data.prompt}}","max_steps":4}' --description "Hand data.prompt to Think"
```

**7. Wire intent matches to the speaker.**

```bash
opal event config rule add --id announce-intents --topic opal.listen.intent.match --action speak --condition 'data.intent_name == "announce"'
```

**8. Test the rule against a fake event first.**

```bash
opal event config rule test announce-intents --data '{"intent_name":"announce","text":"Dinner is ready"}'
```

**9. Invoke an action by hand.**

```bash
opal event config action execute speak --data '{"text":"Testing, one two three"}'
```

**10. What did it actually run?**

```bash
opal event data execution list --limit 10
```

**11. Read one execution's result.**

```bash
opal event data execution show exec-99
```

**12. Look at the failure record.**

```bash
opal event data execution list --status template_error
```

**13. Clear the event history after debugging.**

```bash
opal event data event clear --before 2025-01-01T00:00:00Z
```

**14. Bus statistics.**

```bash
opal event info stats
```

**15. Health probe.**

```bash
opal event info ready
```

**16. Update a rule's condition.**

```bash
opal event config rule update announce-intents --condition 'data.intent_name == "announce" and data.confidence > 0.8'
```

**17. Remove a retired action.**

```bash
opal event config action remove think-it
```

**18. Back up the routing table.**

```bash
opal event backup create
```

**19. Validate a staged configuration.**

```bash
opal event backup validate
```

**20. Tail the switchboard log.**

```bash
opal event service log
```

### combined

*Fifty recipes that use two or more services. Plumbing assumed: Think's `event.base_url` is set, Listen/Look event publication is enabled, and the `speak` action from recipe 5 above is registered.*

**1. Voice-announce every person on the porch.**

```bash
opal event config rule add --id porch-announce --topic opal.look.condition.matched --action speak --condition 'data.label == "person"'
```

**2. Ask Think to narrate what the camera sees.**

```bash
opal event config action add --id describe-scene --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A look event fired: {{event}}. Describe what likely happened and use speak to report it.","max_steps":4}'
opal event config rule add --id narrate-porch --topic opal.look.condition.matched --action describe-scene
```

**3. Spoken doorbell: wakeword "front door" triggers a capture, then a task summarizes it.**

```bash
opal event config action add --id snap-front --type shell --mode exec --executable /usr/local/bin/opal --args '["look","source","capture","cam-front"]'
opal event config rule add --id doorbell-snap --topic opal.listen.intent.match --action snap-front --condition 'data.intent_name == "doorbell"'
```

**4. Have Think answer spoken questions out loud.**

```bash
opal event config action add --id qa-loop --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"The user asked: {{data.transcript}}. Answer briefly, then call the speak action with your answer.","max_steps":4}'
opal event config rule add --id voice-qa --topic opal.listen.intent.match --action qa-loop --condition 'data.intent_name == "ask-question"'
```

**5. Resolve the front door camera through the registry, then point Look at it.**

```bash
opal device list --type camera --label location=front-door --status available
opal look source show cam-front
```

**6. Say a warning only when the porch camera is healthy.**

```bash
opal device status dev-cam-front
opal say generate "Someone is on the porch." --play
```

**7. Log monitor failures as Think-reviewable tasks.**

```bash
opal event config action add --id triage-camera --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Camera monitor failed: {{event}}. Suggest one remediation step.","max_steps":2}'
opal event config rule add --id camera-triage --topic opal.look.monitor.failed --action triage-camera
```

**8. Announce a device's arrival over the speakers.**

```bash
opal event config rule add --id new-device-hello --topic 'opal.devices.*' --action speak
opal device config setting set events.publish_enabled true
```

**9. Morning briefing: read the night's observations aloud.**

```bash
opal look data observation list --label person --limit 5
opal say generate "Three visitors last night, all before midnight." --play
```

**10. Verify the whole chain end-to-end with a synthetic event.**

```bash
opal event publish --topic opal.look.condition.matched --data '{"label":"person","zone_id":"zone-porch","rule_id":"person-on-porch"}'
opal event data execution list --limit 3
```

**11. Teach Listen a new intent, then confirm the event lands.**

```bash
opal listen recognition test-text "who is at the door"
opal event data event list --topic opal.listen.intent.match --limit 1
```

**12. Quiz night: Listen hears the answer, Think grades it, Say announces the score.**

```bash
opal event config action add --id grade-answer --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"session_id":"ses-quiz","prompt":"The student answered: {{data.transcript}}. Grade it, speak the verdict, ask the next question.","max_steps":4}'
opal event config rule add --id quiz-grader --topic opal.listen.intent.match --action grade-answer --condition 'data.intent_name == "quiz-answer"'
```

**13. Backup all six services in one pass.**

```bash
for s in devices listen look think say event; do opal $s backup create; done
```

**14. Health-check the fleet in one pass.**

```bash
for s in devices listen look think say event; do opal $s info health; done
```

**15. Give every service the same quiet-hours profile.**

```bash
for s in listen look think say devices; do opal $s config profile add --id night --name "Night" --settings '{"quiet":true}'; done
```

**16. Persona flows from Think's registry to Say's voice.**

```bash
opal think config persona add --id vox --name "Vox" --voice-id en-gb-alan-low
opal say generate "Persona binding check." --persona vox --play
```

**17. Correlate an event to the task it spawned.**

```bash
opal event data execution show exec-99
opal think task show tsk-42
```

**18. The registry remembers what Look forgot.**

```bash
opal device show dev-cam-front
opal look source update cam-front --uri rtsp://192.168.1.31:554/stream
```

**19. Speak every failed utterance so you can hear what went wrong.**

```bash
opal listen data failed-utterance list --limit 3
opal say generate "I did not understand: lights please." --play
```

**20. Stop the world politely.**

```bash
for s in say think look listen devices; do opal $s service stop; done
opal event service stop
```

**21. Start it again in dependency order.**

```bash
opal event service start; opal device service start; opal look service start; opal listen service start; opal think service start; opal say service start
```

**22. Find which peer advertises a GPU, then schedule a Look job on it.**

```bash
opal device federation inventory --type gpu
opal look data job submit --pipeline heavy-detector
```

**23. Guard the group, not the device.**

```bash
opal device group member list grp-porch
opal look config rule update person-on-porch --source cam-front
```

**24. Silence the speaker when nobody's home.**

```bash
opal look config rule show occupancy-rule
opal say config profile activate night
```

**25. Regression-test ears, then warn the mouth.**

```bash
opal listen regression run reg-suite-1
opal say generate "Accuracy dropped two points. Check the regression report." --play
```

**26. Peer down, stop trusting it.**

```bash
opal device peer status garage
opal device peer update garage --no-trusted
```

**27. Route stale-device events to cleanup.**

```bash
opal event config rule add --id stale-cleaner --topic 'opal.devices.*' --action triage-camera --condition 'data.availability == "stale"'
```

**28. Confirm a peer sees only what policy allows.**

```bash
opal device sharing list
opal device federation inventory --peer garage
```

**29. Voice-check every registered voice, spoken in its own voice.**

```bash
opal say config voice list
opal say config voice test en-gb-alan-low --play
```

**30. The camera died mid-demo: announce it gracefully.**

```bash
opal event config rule add --id dead-cam-say --topic opal.look.monitor.failed --action speak
```

**31. Snapshot everything before the big rewiring.**

```bash
for s in devices listen look think say event; do opal $s backup export --out $s-config.yaml; done
```

**32. Prove the snapshot is loadable everywhere.**

```bash
for s in devices listen look think say event; do opal $s backup validate; done
```

**33. Spoken audit of the bus.**

```bash
opal event info stats
opal say generate "Two thousand four hundred events today. Mostly squirrels." --play
```

**34. Discover hardware, then register it with Look in one breath.**

```bash
opal device discover
opal look source add --id cam-new --uri rtsp://192.168.1.40:554/main --kind rtsp
```

**35. Route observations to the notebook.**

```bash
opal event config action add --id log-obs --type python --code 'print("seen:", data)'
opal event config rule add --id obs-notebook --topic opal.look.observation --action log-obs
```

**36. Ask Think which devices it thinks are underused.**

```bash
opal think task create --prompt "Fetch the devices inventory via the Event action and suggest which registered devices are underused." --max-steps 6
```

**37. Announce when the garage peer comes back online.**

```bash
opal device peer status garage
opal say generate "The garage registry is back." --play
```

**38. Test the whole intent pipeline without speaking.**

```bash
opal listen recognition test-text "turn on the kitchen light"
opal event data execution list --limit 1
```

**39. Session-scoped butler: hold context across requests.**

```bash
opal think session add --id ses-butler
opal think task create --session-id ses-butler --prompt "Remember: the user prefers early warnings about porch visitors."
```

**40. Nightly report job, spoken edition.**

```bash
opal look data job submit --pipeline porch-people --media-set today --notify
opal event config rule add --id nightly-summary --topic 'opal.look.job.finished' --action describe-scene
```

**41. Verify event topics before writing rules.**

```bash
opal event data topic list
opal listen config setting show event_transport
```

**42. A device goes stale; Think decides what to say about it.**

```bash
opal event config rule add --id stale-commentary --topic 'opal.devices.*' --action describe-scene --condition 'data.availability == "stale"'
```

**43. Cross-check capabilities before promising a demo.**

```bash
opal device capabilities dev-cam-front
opal look info capabilities
```

**44. Mute the mic, warn via camera flash detection instead.**

```bash
opal listen recognition stop
opal look session start --source cam-front --pipeline porch-people
```

**45. The persona swap drill: same announcement, three voices.**

```bash
opal think config persona list
opal say generate "Shift change. Vox is off duty." --persona vox --play
```

**46. Confirm peer inventory hides the denied GPU.**

```bash
opal device sharing deny --device-id dev-lab-gpu
opal device federation inventory
```

**47. Watch the registry while Look's scanner runs.**

```bash
opal device watch &
opal look source probe cam-new
```

**48. Rebuild the intent library from backup, then re-test.**

```bash
opal listen backup restore listen-backup-2025-01-01.tar.gz
opal listen regression run reg-suite-1
```

**49. Spoken regression report.**

```bash
opal listen performance summary
opal say generate "Ninety-seven percent accuracy this week. Acceptable." --play
```

**50. The full-stack goodnight.**

```bash
opal event config rule list
opal device list --status available
opal look session list
opal say generate "All systems nominal. Goodnight." --play
for s in say think look listen devices event; do opal $s service stop; done
```

---

*Every recipe maps to an operation in the v1.7.1 contracts. Where a command name is marked proposed elsewhere, it names the operation a conforming CLI should expose — check `docs/COOKBOOK.md` for per-operation REST mappings and `docs/OPAL_DEVICES_CLI.md` for the devices matrix.*
