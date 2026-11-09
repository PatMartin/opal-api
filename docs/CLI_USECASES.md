# OPAL CLI Use Cases

Reference recipes for every OPAL interface. **Part I** covers each service
in isolation — every command in a section calls only that interface.
**Part II** combines interfaces into richer cross-service workflows.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, `INTENT_ID`, `RULE_ID`, `TASK_ID`, ...) with values from
your deployment. Use `--url URL --token TOKEN` when the CLI is not
preconfigured.

Configuration mutations require a current, quoted strong ETag:
`--if-match '"CURRENT_CONFIG_ETAG"'`. Never use `*`.

## Contents

### Part I — Single-Interface Use Cases

- [OPAL Listen](#opal-listen)
  - [L1 — Check service health](#l1--check-service-health)
  - [L2 — List audio devices](#l2--list-audio-devices)
  - [L3 — Test text recognition](#l3--test-text-recognition)
  - [L4 — Test audio recognition](#l4--test-audio-recognition)
  - [L5 — Add an intent with phrases](#l5--add-an-intent-with-phrases)
  - [L6 — Run regression tests](#l6--run-regression-tests)
- [OPAL Say](#opal-say)
  - [S1 — List voices](#s1--list-voices)
  - [S2 — Validate a voice](#s2--validate-a-voice)
  - [S3 — Generate a WAV file](#s3--generate-a-wav-file)
  - [S4 — Test voice settings](#s4--test-voice-settings)
  - [S5 — Stream PCM to a player](#s5--stream-pcm-to-a-player)
  - [S6 — List speech engines](#s6--list-speech-engines)
- [OPAL Event](#opal-event)
  - [E1 — Publish an event](#e1--publish-an-event)
  - [E2 — List events by topic](#e2--list-events-by-topic)
  - [E3 — List automation rules](#e3--list-automation-rules)
  - [E4 — Test a rule](#e4--test-a-rule)
  - [E5 — Execute an action](#e5--execute-an-action)
  - [E6 — Inspect executions](#e6--inspect-executions)
- [OPAL Look](#opal-look)
  - [V1 — List sources](#v1--list-sources)
  - [V2 — Probe a source](#v2--probe-a-source)
  - [V3 — Capture a frame](#v3--capture-a-frame)
  - [V4 — Analyze an image](#v4--analyze-an-image)
  - [V5 — List observations](#v5--list-observations)
  - [V6 — Run a live session](#v6--run-a-live-session)
- [OPAL Think](#opal-think)
  - [T1 — List models](#t1--list-models)
  - [T2 — Create a task](#t2--create-a-task)
  - [T3 — Watch a task](#t3--watch-a-task)
  - [T4 — Retrieve a result](#t4--retrieve-a-result)
  - [T5 — Create a session](#t5--create-a-session)
  - [T6 — Cancel a task](#t6--cancel-a-task)

### Part II — Cross-Interface Use Cases

- [Home Automation](#home-automation)
  - [H1 — Voice-controlled light](#h1--voice-controlled-light)
  - [H2 — Is the garage door open?](#h2--is-the-garage-door-open)
  - [H3 — Delivery alert](#h3--delivery-alert)
  - [H4 — Morning briefing](#h4--morning-briefing)
  - [H5 — Water leak warning](#h5--water-leak-warning)
- [Computer Monitoring](#computer-monitoring)
  - [C1 — Read an error screen aloud](#c1--read-an-error-screen-aloud)
  - [C2 — Voice incident report](#c2--voice-incident-report)
  - [C3 — Rack LED check](#c3--rack-led-check)
  - [C4 — Stack trace triage](#c4--stack-trace-triage)
  - [C5 — Weekly helpdesk digest](#c5--weekly-helpdesk-digest)
- [Voice Assistant](#voice-assistant)
  - [A1 — Spoken Q&A](#a1--spoken-qa)
  - [A2 — Spoken reminder log](#a2--spoken-reminder-log)
  - [A3 — Multi-turn chat](#a3--multi-turn-chat)
  - [A4 — Quick translation](#a4--quick-translation)
  - [A5 — Document summary](#a5--document-summary)
- [Education](#education)
  - [D1 — Read a printed page aloud](#d1--read-a-printed-page-aloud)
  - [D2 — Reading practice feedback](#d2--reading-practice-feedback)
  - [D3 — Flashcard definition](#d3--flashcard-definition)
  - [D4 — Language phrase rehearsal](#d4--language-phrase-rehearsal)
  - [D5 — Whiteboard notes](#d5--whiteboard-notes)
- [Accessibility](#accessibility)
  - [X1 — Scene description](#x1--scene-description)
  - [X2 — Sign reader](#x2--sign-reader)
  - [X3 — Speech-to-text notes](#x3--speech-to-text-notes)
  - [X4 — No-touch control](#x4--no-touch-control)
  - [X5 — Orientation helper](#x5--orientation-helper)
- [Pet Care](#pet-care)
  - [P1 — Did the pet eat?](#p1--did-the-pet-eat)
  - [P2 — Bark alert](#p2--bark-alert)
  - [P3 — Crate escape check](#p3--crate-escape-check)
  - [P4 — Vet visit prep](#p4--vet-visit-prep)
  - [P5 — Alone-time report](#p5--alone-time-report)
- [Property Monitoring](#property-monitoring)
  - [M1 — Vacancy verification](#m1--vacancy-verification)
  - [M2 — Leak photo triage](#m2--leak-photo-triage)
  - [M3 — Parking count](#m3--parking-count)
  - [M4 — Hallway patrol](#m4--hallway-patrol)
  - [M5 — Landlord digest](#m5--landlord-digest)
- [Shopping and Pantry](#shopping-and-pantry)
  - [G1 — Spoken grocery item](#g1--spoken-grocery-item)
  - [G2 — Pantry inventory](#g2--pantry-inventory)
  - [G3 — Label read-aloud](#g3--label-read-aloud)
  - [G4 — Receipt log](#g4--receipt-log)
  - [G5 — Dinner suggestion](#g5--dinner-suggestion)
- [Stargazing](#stargazing)
  - [N1 — Sky condition check](#n1--sky-condition-check)
  - [N2 — Spoken sighting log](#n2--spoken-sighting-log)
  - [N3 — Aurora alert](#n3--aurora-alert)
  - [N4 — Meteor count](#n4--meteor-count)
  - [N5 — Session recap](#n5--session-recap)
- [Office Work](#office-work)
  - [O1 — Meeting note dictation](#o1--meeting-note-dictation)
  - [O2 — Spoken memo to file](#o2--spoken-memo-to-file)
  - [O3 — Voice task triage](#o3--voice-task-triage)
  - [O4 — Status rollup](#o4--status-rollup)
  - [O5 — Report read-aloud](#o5--report-read-aloud)

---

## OPAL Listen

Speech recognition, vocabulary, and quality control. These recipes use
`opal listen` only.

### L1 — Check service health

```bash
opal listen info health --json
opal listen info ready --json
```

### L2 — List audio devices

```bash
opal listen info audio-devices --json
```

### L3 — Test text recognition

```bash
opal listen recognition test-text --text 'hello opal' --save-log true --json
```

### L4 — Test audio recognition

```bash
opal listen recognition test-audio --file question.wav --save-log true --json
```

### L5 — Add an intent with phrases

```bash
opal listen intent add --name greeting \
  --phrases '["hello opal","good morning"]' \
  --enabled true --if-match '"CURRENT_CONFIG_ETAG"' --json
```

### L6 — Run regression tests

```bash
opal listen regression run --enabled-only true --json
```

## OPAL Say

Speech synthesis and voice management. These recipes use `opal say` only.

### S1 — List voices

```bash
opal say voice list --json
```

### S2 — Validate a voice

```bash
opal say voice validate VOICE_ID --json
```

### S3 — Generate a WAV file

```bash
opal say generate --voice-id VOICE_ID \
  --text 'Your OPAL services are ready.' \
  --output-format wav --output-file announcement.wav
```

### S4 — Test voice settings

```bash
opal say voice test VOICE_ID \
  --text 'Testing a comfortable pace.' \
  --speed 0.9 --volume 0.8 \
  --output-format wav --output-file voice-test.wav
```

### S5 — Stream PCM to a player

```bash
opal say stream --voice-id VOICE_ID \
  --text 'Live audio.' --sample-rate 22050 \
  | aplay -f S16_LE -r 22050 -c 1
```

### S6 — List speech engines

```bash
opal say engine list --json
```

## OPAL Event

Event history, rules, and actions. These recipes use `opal event` only.

### E1 — Publish an event

```bash
opal event event publish --topic sensor.greenhouse \
  --source greenhouse-1 \
  --data '{"temperature_c":31.4}' --json
```

### E2 — List events by topic

```bash
opal event event list --topic sensor.greenhouse --limit 20 --json
```

### E3 — List automation rules

```bash
opal event rule list --json
```

### E4 — Test a rule

```bash
opal event rule test RULE_ID \
  --event '{"topic":"sensor.greenhouse","data":{"temperature_c":31.4}}' --json
```

### E5 — Execute an action

```bash
opal event action execute ACTION_ID \
  --event '{"topic":"home.command","data":{"intent":"lights_on"}}' --json
```

### E6 — Inspect executions

```bash
opal event execution list --action-id ACTION_ID --limit 20 --json
```

## OPAL Look

Cameras, pipelines, and analysis. These recipes use `opal look` only.

### V1 — List sources

```bash
opal look source list --json
```

### V2 — Probe a source

```bash
opal look source probe CAMERA_ID --json
```

### V3 — Capture a frame

```bash
opal look source frame CAMERA_ID --output-file frame.jpg
```

### V4 — Analyze an image

```bash
opal look analyze image --image photo.jpg \
  --pipeline-id PIPELINE_ID --persist-results true --json
```

### V5 — List observations

```bash
opal look data observation list --source-id CAMERA_ID --limit 25 --json
```

### V6 — Run a live session

```bash
SID=$(opal look session start --source-id CAMERA_ID \
  --pipeline-id PIPELINE_ID --auto-start true --json | jq -er '.id')
opal look data observation list --session-id "$SID" --limit 25 --json
opal look session stop "$SID" --json
```

## OPAL Think

Durable AI tasks and conversation sessions. These recipes use
`opal think` only.

### T1 — List models

```bash
opal think model list --json
```

### T2 — Create a task

```bash
opal think task create \
  --prompt 'Summarize the incident and suggest two checks.' \
  --context '{"report":"Sensor stopped reporting after a power cut."}' \
  --timeout-seconds 120 --json
```

### T3 — Watch a task

```bash
opal think task watch TASK_ID
```

### T4 — Retrieve a result

```bash
opal think task show TASK_ID --json | jq -er '.answer'
```

### T5 — Create a session

```bash
opal think session add --title 'Planning session' --json
```

### T6 — Cancel a task

```bash
opal think task cancel TASK_ID --json
```

---

# Part II — Cross-Interface Use Cases

Fifty workflows that combine two or more interfaces. Set these once per
shell:

```bash
VOICE_ID=narrator       # opal say voice list --json
CAMERA_ID=front-door    # opal look source list --json
PIPELINE_ID=detector    # opal look info capabilities --json
OCR_PIPELINE=text-ocr   # opal look info capabilities --json
```

## Home Automation

### H1 — Voice-controlled light

Spoken intent resolved by Listen, executed by an Event action.

```bash
opal listen recognition test-text --text 'turn on the kitchen light' --json > cmd.json
opal event action execute kitchen-light-on \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name}}' cmd.json)" --json
```

### H2 — Is the garage door open?

Frame the garage and get a spoken verdict.

```bash
opal look source frame garage-1 --output-file garage.jpg
opal look analyze image --image garage.jpg --pipeline-id <pipeline_id> --json > g.json
opal think task watch <tid>
```

### H3 — Delivery alert

Package observation triggers a household event and a spoken notice.

```bash
COUNT=$(opal look data observation list --source-id "$CAMERA_ID" --label package --limit 5 --json | jq '.items | length')
if [ "$COUNT" -gt 0 ]; then
  opal event event publish --topic home.delivery --source front-door \
    --data "{\"packages\":$COUNT}" --json
  opal say generate --voice-id "$VOICE_ID" --text 'A package was spotted.' \
    --output-format wav --output-file delivery.wav
fi
```

### H4 — Morning briefing

Status from three services narrated as one briefing.

```bash
opal look source status <camera_id> --json | jq -c '{state:.state}'
opal listen recognition status --json | jq -c '{running:.running}'
opal event stats show --json | jq -c '{observed:.observed_events}'
```

### H5 — Water leak warning

Sensor event becomes a triaged spoken alert.

```bash
opal event event publish --topic home.sensor.water \
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Computer Monitoring

### C1 — Read an error screen aloud

OCR an error dialog and hear the fix.

```bash
opal look analyze image --image error.png --pipeline-id <ocr_pipeline> --json > e.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

### C2 — Voice incident report

Spoken problem report becomes a ticket event.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file report.wav --save-log true --json | jq -r '.transcript')
opal event event publish --topic it.incident \
  --source helpdesk --data "{\"report\":\"$TRANSCRIPT\"}" --json
```

### C3 — Rack LED check

Frame the rack; warning LEDs publish a hardware alert.

```bash
opal look source frame rack-1 --output-file rack.jpg
opal look analyze image --image rack.jpg --pipeline-id "$PIPELINE_ID" --json > rack.json
ALERT=$(jq '[.observations[] | select(.label=="led_red")] | length' rack.json)
if [ "$ALERT" -gt 0 ]; then
  opal event event publish --topic it.hardware.alert \
    --source rack-cam --data "{\"warning_leds\":$ALERT}" --json
fi
```

### C4 — Stack trace triage

OCR a stack trace; THINK summarizes cause and fix.

```bash
opal look analyze image --image trace.png --pipeline-id "$OCR_PIPELINE" --json > t.json
TID=$(opal think task create \
  --prompt 'Summarize this trace: probable cause and first fix to try.' \
  --context "{\"trace\":\"$(jq -r '.observations[0].text // empty' t.json)\"}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > triage.txt
```

### C5 — Weekly helpdesk digest

Week of incident events narrated for the team.

```bash
opal event event list --topic it.incident --limit 20 --json > week.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Voice Assistant

### A1 — Spoken Q&A

Question in, answer out.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file q.wav --json | jq -r '.transcript')
TID=$(opal think task create --prompt "Answer briefly: $TRANSCRIPT" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file answer.wav
```

### A2 — Spoken reminder log

Dictate a reminder; store it as a dated event.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file reminder.wav --save-log true --json | jq -r '.transcript')
opal event event publish --topic assistant.reminder \
  --source voice-memo --data "{\"note\":\"$TRANSCRIPT\"}" --json
```

### A3 — Multi-turn chat

THINK session keeps context across spoken turns.

```bash
CSID=$(opal think session add --title 'Voice chat' --json | jq -er '.id')
T1=$(opal listen recognition test-audio --file turn1.wav --json | jq -r '.transcript')
TID=$(opal think task create --prompt "$T1" --session-id "$CSID" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file reply.wav
```

### A4 — Quick translation

Ask for a phrase aloud; hear it translated.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'how do I say thank you in Japanese?' --json | jq -r '.transcript')
TID=$(opal think task create --prompt "Translate as asked; reply with the phrase only: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file translation.wav
```

### A5 — Document summary

OCR a page; hear a two-sentence summary.

```bash
opal look analyze image --image doc.jpg --pipeline-id <ocr_pipeline> --json > d.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Education

### D1 — Read a printed page aloud

```bash
opal look analyze image --image page.jpg --pipeline-id "$OCR_PIPELINE" --json > p.json
opal say generate --voice-id "$VOICE_ID" \
  --text "$(jq -r '.observations[0].text // empty' p.json)" \
  --output-format wav --output-file page.wav
```

### D2 — Reading practice feedback

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file reading.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Compare to the expected text; give two kind improvement tips.' \
  --context "{\"expected\":\"The cat sat on the mat.\",\"heard\":\"$TRANSCRIPT\"}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### D3 — Flashcard definition

```bash
opal look analyze image --image card.jpg --pipeline-id "$OCR_PIPELINE" --json > c.json
WORD=$(jq -r '.observations[0].text // .observations[0].label' c.json)
TID=$(opal think task create --prompt "Define '$WORD' in one student-friendly sentence." \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file card.wav
```

### D4 — Language phrase rehearsal

```bash
opal say generate --voice-id "$VOICE_ID" --text 'Bonjour, comment allez-vous?' \
  --output-format wav --output-file target.wav
TRANSCRIPT=$(opal listen recognition test-audio --file attempt.wav --json | jq -r '.transcript')
opal event event publish --topic language.practice \
  --source drill --data "{\"target\":\"Bonjour\",\"heard\":\"$TRANSCRIPT\"}" --json
```

### D5 — Whiteboard notes

```bash
opal look analyze image --image board.jpg --pipeline-id "$OCR_PIPELINE" --json > b.json
TID=$(opal think task create \
  --prompt 'Turn this whiteboard capture into concise lecture notes.' \
  --context "{\"text\":\"$(jq -r '.observations[0].text // empty' b.json)\"}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > notes.txt
```

## Accessibility

### X1 — Scene description

```bash
opal look source frame <camera_id> --output-file scene.jpg
opal look analyze image --image scene.jpg --pipeline-id <pipeline_id> --json > s.json
opal think task watch <tid>
```

### X2 — Sign reader

```bash
opal look analyze image --image sign.jpg --pipeline-id "$OCR_PIPELINE" --json > sg.json
opal say generate --voice-id "$VOICE_ID" \
  --text "The sign says: $(jq -r '.observations[0].text // empty' sg.json)" \
  --output-format wav --output-file sign.wav
```

### X3 — Speech-to-text notes

```bash
opal listen recognition test-audio --file dictation.wav --save-log true --json > d.json
jq -r '.transcript' d.json >> notes.txt
opal event event publish --topic access.notes \
  --source dictation --data "$(jq -c '{transcript:.transcript}' d.json)" --json
```

### X4 — No-touch control

```bash
opal listen recognition test-text --text 'dim the bedroom lights' --json > x.json
opal event action execute bedroom-dim \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name}}' x.json)" --json
```

### X5 — Orientation helper

```bash
opal look source frame <camera_id> --output-file room.jpg
opal look analyze image --image room.jpg --pipeline-id <pipeline_id> --json > r.json
opal think task watch <tid>
```

## Pet Care

### P1 — Did the pet eat?

```bash
opal look source frame pet-kitchen --output-file bowl.jpg
opal look analyze image --image bowl.jpg --pipeline-id <pipeline_id> --json > b.json
opal think task watch <tid>
```

### P2 — Bark alert

```bash
opal listen recognition test-audio --file bark.wav --save-log true --json > bk.json
if [ "$(jq -r '.matched' bk.json)" = "true" ]; then
  opal event event publish --topic pet.bark --source yard-mic \
    --data '{"bark":true}' --json
fi
```

### P3 — Crate escape check

```bash
opal look source frame crate-cam --output-file crate.jpg
opal look analyze image --image crate.jpg --pipeline-id "$PIPELINE_ID" --json > cr.json
EMPTY=$(jq '[.observations[] | select(.label=="crate_empty")] | length' cr.json)
if [ "$EMPTY" -gt 0 ]; then
  opal event event publish --topic pet.escape --source crate-cam \
    --data '{"crate":"empty"}' --json
fi
```

### P4 — Vet visit prep

```bash
opal event event list --topic <topic> --limit 10 --json
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > vet-prep.txt
```

### P5 — Alone-time report

```bash
opal event event list --topic pet.bark --limit 20 --json > solo.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Property Monitoring

### M1 — Vacancy verification

```bash
opal look source frame unit-101 --output-file unit.jpg
opal look analyze image --image unit.jpg --pipeline-id "$PIPELINE_ID" --json > u.json
TID=$(opal think task create \
  --prompt 'Does this room look vacant and show-ready? Yes or no with a reason.' \
  --context "{\"observations\":$(jq -c '.observations' u.json)}" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### M2 — Leak photo triage

```bash
opal look analyze image --image under-sink.jpg --pipeline-id <pipeline_id> --json > lk.json
opal think task watch <tid>
opal event event publish --topic property.maintenance.leak \
```

### M3 — Parking count

```bash
opal look analyze image --image lot.jpg --pipeline-id "$PIPELINE_ID" --json > lot.json
CARS=$(jq '[.observations[] | select(.label=="car" or .label=="truck")] | length' lot.json)
opal event event publish --topic property.parking \
  --source lot-cam --data "{\"vehicles\":$CARS}" --json
```

### M4 — Hallway patrol

```bash
opal look source frame <src> --output-file "patrol-<src>.jpg"
opal look analyze image --image "patrol-<src>.jpg" \
opal event event publish --topic property.patrol \
```

### M5 — Landlord digest

```bash
opal event event list --topic <topic> --limit 10 --json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Shopping and Pantry

### G1 — Spoken grocery item

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file add-item.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create --prompt 'Turn this spoken request into a list entry.' \
  --context "{\"speech\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' >> grocery-list.txt
```

### G2 — Pantry inventory

```bash
opal look analyze image --image pantry.jpg --pipeline-id "$OCR_PIPELINE" --json > pn.json
TID=$(opal think task create \
  --prompt 'List items that look nearly empty on this pantry shelf.' \
  --context "{\"observations\":$(jq -c '.observations' pn.json)}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > restock.txt
```

### G3 — Label read-aloud

```bash
opal look analyze image --image label.jpg --pipeline-id "$OCR_PIPELINE" --json > lb.json
opal say generate --voice-id "$VOICE_ID" \
  --text "Label says: $(jq -r '.observations[0].text // empty' lb.json)" \
  --output-format wav --output-file label.wav
```

### G4 — Receipt log

```bash
opal look analyze image --image receipt.jpg --pipeline-id "$OCR_PIPELINE" --json > rc.json
opal event event publish --topic shopping.receipt \
  --source scanner --data "{\"text\":\"$(jq -r '.observations[0].text // empty' rc.json)\"}" --json
```

### G5 — Dinner suggestion

```bash
opal look analyze image --image pantry.jpg --pipeline-id <ocr_pipeline> --json > dn.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Stargazing

### N1 — Sky condition check

```bash
opal look source frame allsky-1 --output-file sky.jpg
opal look analyze image --image sky.jpg --pipeline-id <pipeline_id> --json > sk.json
opal think task watch <tid>
```

### N2 — Spoken sighting log

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file sighting.wav --save-log true --json | jq -r '.transcript')
opal event event publish --topic sky.sighting \
  --source eyepiece-mic --data "{\"note\":\"$TRANSCRIPT\"}" --json
```

### N3 — Aurora alert

```bash
opal look analyze image --image sky.jpg --pipeline-id "$PIPELINE_ID" --json > au.json
GLOW=$(jq '[.observations[] | select(.label=="aurora" or .label=="glow")] | length' au.json)
if [ "$GLOW" -gt 0 ]; then
  opal event event publish --topic sky.aurora --source allsky --data '{"glow":true}' --json
  opal say generate --voice-id "$VOICE_ID" --text 'Possible aurora on the north camera.' \
    --output-format wav --output-file aurora.wav
fi
```

### N4 — Meteor count

```bash
COUNT=$(opal look data observation list --source-id allsky-1 --label streak --limit 50 --json | jq '.items | length')
opal event event publish --topic sky.meteor \
  --source allsky-cam --data "{\"streaks\":$COUNT}" --json
```

### N5 — Session recap

```bash
opal event event list --topic <topic> --limit 10 --json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Office Work

### O1 — Meeting note dictation

```bash
opal listen recognition test-audio --file meeting.wav --save-log true --json > mt.json
TID=$(opal think task create \
  --prompt 'Summarize this meeting transcript into three bullets and one action item.' \
  --context "{\"transcript\":\"$(jq -r '.transcript' mt.json)\"}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > meeting-notes.txt
```

### O2 — Spoken memo to file

```bash
opal listen recognition test-audio --file memo.wav --save-log true --json > mo.json
jq -r '.transcript' mo.json >> memos.txt
```

### O3 — Voice task triage

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file todos.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Sort these tasks by urgency; read back the top three.' \
  --context "{\"tasks\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file todos.wav
```

### O4 — Status rollup

```bash
opal listen info ready --json | jq -r '.status'
opal look info ready --json | jq -r '.status'
opal say info ready --json | jq -r '.status'
opal event stats show --json | jq -c '{observed:.observed_events}'
```

### O5 — Report read-aloud

```bash
opal look analyze image --image report.jpg --pipeline-id <ocr_pipeline> --json > rp.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

## Practical Notes

- **Extract handoff fields with `jq`.** `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` are the reliable link points between
  services.
- **Part I never crosses services.** Every command inside a single-service
  section calls only that interface — mix and match freely.
- **Sequence THINK turns.** `task watch` observes; submit the next task
  only after the current one completes in a session.
- **Keep ETags quoted.** `--if-match '"REVISION"'` on every configuration
  mutation; `428` missing, `412` stale, `422` malformed.
- **Log before you act.** Publishing to an event topic first preserves the
  record regardless of what the action does afterwards.
