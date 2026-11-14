# The OPAL Ecosystem Cookbook

*One CLI, five services: ears that listen, eyes that watch, a brain that reasons, a mouth that speaks, and a switchboard that makes them gossip.*

This cookbook describes the unified `opal` [Typer](https://typer.tiangolo.com/) CLI implied by the v1.7.1 OpenAPI contracts in [`openapi/`](../openapi), the shared kernel at [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml). Every command maps to exactly one REST operation in those contracts.

One honest caveat: this repository ships contracts, not an `opal` executable. Treat this as the menu for a restaurant whose kitchen is specified in great detail.

## Contents

- [Introduction](#introduction)
- [CLI Command Tree](#cli-command-tree)
  - [EVENT FLOW](#event-flow)
- [Recipes](#recipes)
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
| **Listen** (`opal listen`) | Hearing | Wakewords, speech-to-text, intent recognition, and slot extraction. Publishes live intent matches to Event. |
| **Look** (`opal look`) | Sight | Optional detection engines and engine-owned models, single-image prediction, and ephemeral RTSP streams with SSE metadata, MJPEG video, snapshots, and metrics. |
| **Think** (`opal think`) | Reasoning | Bounded asynchronous tasks on configured models; can discover and invoke Event actions; owns the authoritative persona registry. |
| **Say** (`opal say`) | Voice | Text-to-speech over host-installed engines; voices and personas; returns audio bytes — it never plays them. |
| **Event** (`opal event`) | Nervous system | Event ingress and history, topic rules, registered shell/HTTP/Python actions, and execution records. |

The pieces compose: Listen observes the world and publishes events; Look watches cameras through ephemeral streams and answers on demand; Event routes published events through rules to registered actions; an action can kick off a Think task; Think can invoke other actions — including a `speak` action wired to Say.

Cross-cutting conventions come from the shared kernel:

- **Routes** live under `/api/v1` with singular resource names and trailing-slash collections.
- **Correlation** travels in `X-Opal-Session-Id`, `X-Opal-Transaction-Id`, `X-Opal-Request-Id`, and `X-Opal-Causation-Id`.
- **Configuration** mutations require `If-Match` against a strong ETag — missing is `428`, stale is `412`. The CLI fetches and attaches ETags for you.
- **Personas** resolve as *explicit request field > persona binding > profile > service default*, with Think as the authoritative persona registry.

## CLI Command Tree

```text
opal
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
├── look                  sight: engines, models, predict, RTSP streams
│   ├── info                  health | version | ping | live | ready
│   ├── engine                list | show | discover | capabilities
│   ├── model                 list | show | load | unload
│   ├── predict               image
│   ├── hardware              list | show
│   ├── stream                start | list | show | stop | watch | watch-video | snapshot | metrics
│   ├── config
│   │   ├── engine            update
│   │   ├── profile           list | add | show | update | remove | activate
│   │   └── setting           list | update | show | set | remove
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

Events travel on topics over the event bus; actions are invoked over REST. Event publication is **best effort** and **disabled by default** on Listen — flip the corresponding setting to opt in. Look publishes no bus events in this contract: its stream events are per-stream SSE (`GET /api/v1/stream/{id}/events`), which a CLI can republish to Event if wanted.

```text
                     publishes (opt-in)                    routes
 LISTEN  ── opal.listen.intent.match ─────────▶ EVENT ──┬──▶ shell/HTTP/Python ACTION
                                                rules   │       e.g. POST /api/v1/task/ ──▶ THINK
                                                        └──▶ shell action `speak` ──▶ opal say generate --play

 LOOK    ── (no bus topics) ── per-stream SSE: GET /api/v1/stream/{stream_id}/events
         ── republish if wanted: opal look stream watch <id> | opal event publish --topic <t> --data -

 THINK   ── (no topics) ── discovers & invokes Event actions over REST:
             GET /api/v1/action/  →  POST /api/v1/action/{id}/execute
```

Fixed by contract: the Listen topic name above. Look's SSE event shapes are contract-fixed, but any republished bus topic is yours to choose.

## Recipes

Assumed ports in the examples: Event `8080`, Say `8081`, Look `8082`, Think `8083`, Listen `8000`. IDs like `str-42` or `tsk-42` are placeholders — use what your services return.

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

**1. Which inference engines are installed?**

```bash
opal look engine list
```

**2. Nudge the host to re-scan for engines.**

```bash
opal look engine discover
```

**3. What options does this engine accept?**

```bash
opal look engine capabilities yolo
```

**4. What models does it offer?**

```bash
opal look model list --engine-id yolo
```

**5. Read one model's card.**

```bash
opal look model show yolo11n
```

**6. Load the model for inference.**

```bash
opal look model load yolo11n
```

**7. Unload it when the GPU is needed elsewhere.**

```bash
opal look model unload yolo11n
```

**8. Detect objects in a single photo.**

```bash
opal look predict image --engine-id yolo --model-id yolo11n --source porch.jpg
```

**9. What compute is available?**

```bash
opal look hardware list
```

**10. Start a plain video stream — zero engines required.**

```bash
opal look stream start --source rtsp://192.168.1.30:554/stream
```

**11. Start a detection stream on the same camera.**

```bash
opal look stream start --source rtsp://192.168.1.30:554/stream --engine-id yolo --model-id yolo11n --annotate
```

**12. What is running right now?**

```bash
opal look stream list
```

**13. Check a stream — credentials stay redacted.**

```bash
opal look stream show str-42
```

**14. Follow its metadata and detection events.**

```bash
opal look stream watch str-42
```

**15. Watch the live feed, annotations included.**

```bash
opal look stream watch-video str-42 --annotated --out porch.mjpeg
```

**16. Grab the current frame.**

```bash
opal look stream snapshot str-42 --out porch.jpg
```

**17. Is it keeping up?**

```bash
opal look stream metrics str-42
```

**18. Stop the stream and release the camera.**

```bash
opal look stream stop str-42
```

**19. Health check before the demo.**

```bash
opal look info health
```

**20. Snapshot the configuration before retuning.**

```bash
opal look backup create
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

*Fifty recipes that use two or more services. Plumbing assumed: Think's `event.base_url` is set, Listen's event publication is enabled, Look's detection streams are republished with `opal look stream watch <id> | opal event publish --topic <t> --source opal-look --data -`, and the `speak` action from recipe 5 above is registered.*

**1. Voice-announce every person on the porch.**

```bash
opal event config rule add --id porch-announce --topic porch.detection --action speak --condition 'data.detections[0].class_name == "person"'
```

**2. Ask Think to narrate what the camera sees.**

```bash
opal event config action add --id describe-scene --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A look event fired: {{event}}. Describe what likely happened and use speak to report it.","max_steps":4}'
opal event config rule add --id narrate-porch --topic porch.detection --action describe-scene
```

**3. Spoken doorbell: wakeword "front door" snapshots the stream, then a task summarizes it.**

```bash
opal event config action add --id snap-front --type shell --mode exec --executable /usr/local/bin/opal --args '["look","stream","snapshot","str-front","--out","/tmp/door.jpg"]'
opal event config rule add --id doorbell-snap --topic opal.listen.intent.match --action snap-front --condition 'data.intent_name == "doorbell"'
```

**4. Have Think answer spoken questions out loud.**

```bash
opal event config action add --id qa-loop --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"The user asked: {{data.transcript}}. Answer briefly, then call the speak action with your answer.","max_steps":4}'
opal event config rule add --id voice-qa --topic opal.listen.intent.match --action qa-loop --condition 'data.intent_name == "ask-question"'
```

**5. Check the front-door stream before promising it works.**

```bash
opal look stream show str-front
opal look stream metrics str-front
```

**6. Say a warning only when the porch stream is running.**

```bash
opal look stream show str-porch
opal say generate "Someone is on the porch." --play
```

**7. Log stream failures as Think-reviewable tasks.**

```bash
opal event config action add --id triage-camera --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A camera stream reported a failure: {{event}}. Suggest one remediation step.","max_steps":2}'
opal event config rule add --id camera-triage --topic front.stream --action triage-camera --condition 'data.status == "failed"'
```

**8. Announce a stream's first detection over the speakers.**

```bash
opal look stream watch str-front | opal event publish --topic front.stream --source opal-look --data -
opal event config rule add --id first-detection-hello --topic front.stream --action speak --condition 'data.type == "detection"'
```

**9. Morning briefing: read the night's republished detections aloud.**

```bash
opal event data event list --topic front.stream --limit 5
opal say generate "Three visitors last night, all before midnight." --play
```

**10. Verify the whole chain end-to-end with a synthetic event.**

```bash
opal event publish --topic porch.detection --data '{"type":"detection","detections":[{"class_name":"person","confidence":0.87}]}'
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

**13. Back up all five services in one pass.**

```bash
for s in listen look think say event; do opal $s backup create; done
```

**14. Health-check the fleet in one pass.**

```bash
for s in listen look think say event; do opal $s info health; done
```

**15. Give every service the same quiet-hours profile.**

```bash
for s in listen look think say; do opal $s config profile add --id night --name "Night" --settings '{"quiet":true}'; done
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

**18. Repoint a stream at the camera's new address.**

```bash
opal look stream stop str-front
opal look stream start --source rtsp://192.168.1.31:554/stream --engine-id yolo --model-id yolo11n
```

**19. Speak every failed utterance so you can hear what went wrong.**

```bash
opal listen data failed-utterance list --limit 3
opal say generate "I did not understand: lights please." --play
```

**20. Stop the world politely.**

```bash
for s in say think look listen; do opal $s service stop; done
opal event service stop
```

**21. Start it again in dependency order.**

```bash
opal event service start; opal look service start; opal listen service start; opal think service start; opal say service start
```

**22. Find a GPU, then pin a detection to it.**

```bash
opal look hardware list
opal look predict image --engine-id yolo --model-id yolo11n --device-id cuda:0 --source crowd.jpg
```

**23. Confirm the stream's buffer policy before trusting the announce rule.**

```bash
opal look stream show str-porch
opal event config rule show porch-announce
```

**24. Silence the speaker when nobody's home.**

```bash
opal look stream show str-front
opal say config profile activate night
```

**25. Regression-test ears, then warn the mouth.**

```bash
opal listen regression run reg-suite-1
opal say generate "Accuracy dropped two points. Check the regression report." --play
```

**26. Engine misbehaving? Fall back to video-only.**

```bash
opal look engine show yolo
opal look stream start --source rtsp://192.168.1.40:554/stream1
```

**27. Route stream failures to cleanup.**

```bash
opal event config rule add --id stale-cleaner --topic front.stream --action triage-camera --condition 'data.status == "failed"'
```

**28. Confirm a stream keeps its credentials out of view.**

```bash
opal look stream show str-front
opal look stream metrics str-front
```

**29. Voice-check every registered voice, spoken in its own voice.**

```bash
opal say config voice list
opal say config voice test en-gb-alan-low --play
```

**30. The camera died mid-demo: announce it gracefully.**

*Assumes the republisher from recipe 8 is running on `str-front`.*

```bash
opal event config rule add --id dead-cam-say --topic front.stream --action speak --condition 'data.status == "failed"'
```

**31. Snapshot everything before the big rewiring.**

```bash
for s in listen look think say event; do opal $s backup export --out $s-config.yaml; done
```

**32. Prove the snapshot is loadable everywhere.**

```bash
for s in listen look think say event; do opal $s backup validate; done
```

**33. Spoken audit of the bus.**

```bash
opal event info stats
opal say generate "Two thousand four hundred events today. Mostly squirrels." --play
```

**34. Discover engines, then put one to work on a new camera.**

```bash
opal look engine discover
opal look stream start --source rtsp://192.168.1.40:554/main --engine-id yolo --model-id yolo11n
```

**35. Route republished detections to the notebook.**

```bash
opal event config action add --id log-obs --type python --code 'print("seen:", data)'
opal event config rule add --id obs-notebook --topic front.stream --action log-obs --condition 'data.type == "detection"'
```

**36. Ask Think which of Look's engines suits the task.**

```bash
opal look engine list
opal think task create --prompt "Between yolo, rfdetr, rtdetr, and dfine, which engine should run person detection on a 10 fps porch stream, and why? One paragraph." --max-steps 3
```

**37. Announce when a failed stream recovers.**

```bash
opal event config rule add --id stream-back --topic front.stream --action speak --condition 'data.status == "running"'
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

**40. Nightly report, spoken edition.**

```bash
opal event config action add --id nightly-summary --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Summarize today's porch detections from the context and speak a one-paragraph report.","context":"{{event}}","max_steps":4}'
opal event publish --topic house.nightly.report --data '{"trigger":"cron"}'
opal event config rule add --id nightly-report --topic house.nightly.report --action nightly-summary
```

**41. Verify event topics before writing rules.**

```bash
opal event data topic list
opal listen config setting show event_transport
```

**42. A stream goes quiet; Think decides what to say about it.**

```bash
opal event config rule add --id stream-commentary --topic front.stream --action describe-scene --condition 'data.status == "failed"'
```

**43. Cross-check engine capabilities before promising a demo.**

```bash
opal look engine capabilities yolo
opal look model list --engine-id yolo
```

**44. Mute the mic, warn via camera detection instead.**

```bash
opal listen recognition stop
opal look stream start --source rtsp://192.168.1.40:554/stream1 --engine-id yolo --model-id yolo11n
```

**45. The persona swap drill: same announcement, three voices.**

```bash
opal think config persona list
opal say generate "Shift change. Vox is off duty." --persona vox --play
```

**46. Confirm the frame queue stays bounded under load.**

```bash
opal look stream metrics str-front
opal look stream show str-front
```

**47. Discover engines, then list what turned up.**

```bash
opal look engine discover
opal look engine list
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
opal look stream list
opal say generate "All systems nominal. Goodnight." --play
for s in say think look listen event; do opal $s service stop; done
```

---

*Every recipe maps to an operation in the v1.7.1 contracts. Where a command name is marked proposed elsewhere, it names the operation a conforming CLI should expose — check `docs/COOKBOOK.md` for per-operation REST mappings.*
