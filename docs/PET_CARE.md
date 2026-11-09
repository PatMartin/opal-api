# OPAL Pet Care Recipes

Twenty pet-care workflows that chain multiple OPAL services together —
Look watches feeding stations, crates, and yards; Listen hears barks and
commands; Think judges behavior and drafts notes; Say delivers spoken
reports and reminders; and Event logs everything for the vet record or
the family timeline. Where COOKBOOK.md exercises one service per recipe,
these composite recipes pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal config voice list --json
CAMERA_ID=kitchen-pet             # from: opal look source list --json
PIPELINE_ID=detector-pipeline     # from: opal look info capabilities --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Feeding and Daily Care](#1-feeding-and-daily-care)
2. [Behavior and Safety Monitoring](#2-behavior-and-safety-monitoring)
3. [Health and Vet Preparation](#3-health-and-vet-preparation)
4. [Enrichment and Check-ins](#4-enrichment-and-check-ins)

## 1. Feeding and Daily Care

### 1. Did the dog eat? — bowl check to answer

Frame the feeding station and get a spoken verdict on whether the bowl was
emptied.

```bash
opal look source frame "$CAMERA_ID" --output-file bowl.jpg
opal look analyze image --image bowl.jpg --pipeline-id "$PIPELINE_ID" --json > bowl.json
OBS=$(jq -c '.observations' bowl.json)
TID=$(opal think task create \
  --prompt 'Is this pet bowl empty, partly eaten, or untouched? One word plus a short note.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file bowl-check.wav
```

### 2. Missed-meal alert — untouched bowl to notification

An untouched bowl past mealtime publishes a reminder event and a spoken
nudge.

```bash
opal look source frame "$CAMERA_ID" --output-file meal.jpg
opal look analyze image --image meal.jpg --pipeline-id "$PIPELINE_ID" --json > m.json
UNTOUCHED=$(jq '[.observations[] | select(.label=="bowl_full")] | length' m.json)
if [ "$UNTOUCHED" -gt 0 ]; then
  opal data event publish --topic pet.meal.missed \
    --source feeder-cam --data '{"bowl":"untouched"}' --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'The pet bowl is still full.' \
    --output-format wav --output-file meal-alert.wav
fi
```

### 3. Water bowl level check

Verify the water station is full before leaving for the day.

```bash
opal look analyze image --image water-bowl.jpg --pipeline-id "$PIPELINE_ID" --json > water.json
LOW=$(jq '[.observations[] | select(.label=="water_low")] | length' water.json)
if [ "$LOW" -gt 0 ]; then
  opal data event publish --topic pet.water.low \
    --source water-cam --data '{"level":"low"}' --json
fi
```

### 4. Feeding log — meal events over time

Every verified meal becomes a dated event for the feeding history.

```bash
opal data observation list --source-id "$CAMERA_ID" --label bowl_empty \
  --limit 10 --json > meals.json
COUNT=$(jq '.items | length' meals.json)
opal data event publish --topic pet.meal.log \
  --source feeder-cam --data "{\"empty_bowls\":$COUNT}" --json
opal data event list --topic pet.meal.log --limit 20 --json
```

### 5. Portion photo for the vet diet plan

Photograph today's portion and log it against the vet's feeding plan.

```bash
opal look analyze image --image portion.jpg --pipeline-id "$PIPELINE_ID" --json > portion.json
OBS=$(jq -c '.observations' portion.json)
TID=$(opal think task create \
  --prompt 'Estimate whether this portion matches a medium-dog cup measure. One sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal data event publish --topic pet.diet \
  --source owner-photo --data "$(opal think task show "$TID" --json | jq -c '{portion_note:.answer}')" --json
```

## 2. Behavior and Safety Monitoring

### 6. Bark detection to alert event

A captured bark becomes a timestamped alert for the household timeline.

```bash
opal listen recognition test-audio --file bark.wav --save-log true --json > bark.json
if [ "$(jq -r '.matched' bark.json)" = "true" ]; then
  opal data event publish --topic pet.bark \
    --source yard-mic --data '{"bark":true}' --json
fi
```

### 7. Crate escape check — is the dog still crated?

Frame the crate area and detect an empty crate with the dog elsewhere.

```bash
opal look source frame crate-cam --output-file crate.jpg
opal look analyze image --image crate.jpg --pipeline-id "$PIPELINE_ID" --json > crate.json
ESCAPED=$(jq '[.observations[] | select(.label=="crate_empty")] | length' crate.json)
if [ "$ESCAPED" -gt 0 ]; then
  opal data event publish --topic pet.escape \
    --source crate-cam --data '{"crate":"empty"}' --json
fi
```

### 8. Counter-surfing dog — kitchen intrusion to spoken scold

Dog detected on the counter triggers a recorded deterrent and a logged
event.

```bash
opal data observation list --source-id kitchen-pet --label dog \
  --limit 5 --json > counter.json
ON_COUNTER=$(jq '[.items[] | select(.attributes.on_counter==true)] | length' counter.json)
if [ "$ON_COUNTER" -gt 0 ]; then
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Off the counter.' --output-format wav --output-file scold.wav
  opal data event publish --topic pet.counter \
    --source kitchen-pet --data '{"on_counter":true}' --json
fi
```

### 9. Door-dash guard — dog near the front door

Detect the dog hovering at the door before opening it.

```bash
opal look source frame front-door --output-file door.jpg
opal look analyze image --image door.jpg --pipeline-id "$PIPELINE_ID" --json > door.json
NEAR=$(jq '[.observations[] | select(.label=="dog" or .label=="cat")] | length' door.json)
if [ "$NEAR" -gt 0 ]; then
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Pet near the door — check before opening.' \
    --output-format wav --output-file door-warning.wav
fi
```

### 10. Zoomies or distress? — activity clip triage

A short audio/video check distinguishes play energy from distress.

```bash
opal listen recognition test-audio --file yard-activity.wav --save-log true --json > act.json
opal look source frame yard-cam --output-file yard.jpg
opal look analyze image --image yard.jpg --pipeline-id "$PIPELINE_ID" --json > yard.json
OBS=$(jq -c '.observations' yard.json)
TID=$(opal think task create \
  --prompt 'From this sound transcript and image observations, is the pet playing or distressed? One word plus a note.' \
  --context "{\"heard\":\"$(jq -r '.transcript' act.json)\",\"observations\":$OBS}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

## 3. Health and Vet Preparation

### 11. Limp check — gait observation to note

Frame the pet moving and note any visible limp or stiffness for the vet
file.

```bash
opal look source frame "$CAMERA_ID" --output-file gait.jpg
opal look analyze image --image gait.jpg --pipeline-id "$PIPELINE_ID" --json > gait.json
OBS=$(jq -c '.observations' gait.json)
TID=$(opal think task create \
  --prompt 'Does this pet show signs of limping or stiffness? One sentence for a vet note.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal data event publish --topic pet.health.gait \
  --source gait-check --data "$(opal think task show "$TID" --json | jq -c '{note:.answer}')" --json
```

### 12. Skin or coat photo for the vet

Photograph a spot and capture a description for the next appointment.

```bash
opal look analyze image --image skin-spot.jpg --pipeline-id "$PIPELINE_ID" --json > skin.json
OBS=$(jq -c '.observations' skin.json)
TID=$(opal think task create \
  --prompt 'Describe this pet skin/coat area neutrally for a vet note: size, color, coverage.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > skin-note.txt
```

### 13. Stool check on the walk pad — quick health signal

A litter/pad frame flags anything unusual for the daily health log.

```bash
opal look analyze image --image pad.jpg --pipeline-id "$PIPELINE_ID" --json > pad.json
OBS=$(jq -c '.observations' pad.json)
TID=$(opal think task create \
  --prompt 'Anything unusual for a pet health log in this pad photo? Answer normal or describe briefly.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal data event publish --topic pet.health.pad \
  --source pad-check --data "$(opal think task show "$TID" --json | jq -c '{note:.answer}')" --json
```

### 14. Medication reminder spoken check

Ask whether the evening dose is due and hear the answer aloud.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'did the cat get her pill tonight?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Using this med schedule, answer yes or no and which dose is next.' \
  --context "{\"question\":\"$TRANSCRIPT\",\"schedule\":{\"morning\":\"08:00\",\"evening\":\"20:00\"}}" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file pet-meds.wav
```

### 15. Vet visit prep — roll up the health events

Summarize the week's health and behavior events for the appointment.

```bash
for TOPIC in pet.health.gait pet.health.pad pet.diet pet.bark; do
  opal data event list --topic "$TOPIC" --limit 10 --json
done > week.jsonl
TID=$(opal think task create \
  --prompt 'Summarize this week of pet events for a vet visit in three bullets.' \
  --context "$(jq -cs '{events:.}' week.jsonl)" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > vet-prep.txt
cat vet-prep.txt
```

## 4. Enrichment and Check-ins

### 16. Midday pet check-in — spoken report card

Frame the pet's usual spot and hear a reassuring status summary.

```bash
opal look source frame "$CAMERA_ID" --output-file noon.jpg
opal look analyze image --image noon.jpg --pipeline-id "$PIPELINE_ID" --json > noon.json
OBS=$(jq -c '.observations' noon.json)
TID=$(opal think task create \
  --prompt 'Describe the pet in one reassuring sentence for an owner at work.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file checkin.wav
```

### 17. Favorite-spot tracker — where does the cat nap?

Check several camera frames and report where the pet settled.

```bash
for SRC in living-room bedroom windowsill; do
  opal look source frame "$SRC" --output-file "nap-$SRC.jpg"
  opal look analyze image --image "nap-$SRC.jpg" \
    --pipeline-id "$PIPELINE_ID" --json > "nap-$SRC.json"
done
OBS=$(jq -sc '[.[].observations]' nap-*.json)
TID=$(opal think task create \
  --prompt 'Which of these rooms contains the pet? Answer with the source name.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 18. Trick training log — spoken cue to transcript record

Speak a cue, capture the pet's response audio, and log the attempt for the
training record.

```bash
opal say generate --voice-id "$VOICE_ID" --text 'Sit.' \
  --output-format wav --output-file cue.wav
opal listen recognition test-audio --file response.wav --save-log true --json > resp.json
opal data event publish --topic pet.training \
  --source trick-session --data "$(jq -c '{cue:"sit",response:.transcript}' resp.json)" --json
```

### 19. Alone-time report — how long was the pet solo?

Review bark and activity events for the day and summarize solo behavior.

```bash
opal data event list --topic pet.bark --limit 20 --json > solo-bark.json
opal data observation list --source-id "$CAMERA_ID" --label dog \
  --limit 20 --json > solo-obs.json
TID=$(opal think task create \
  --prompt 'From these events, summarize how the pet did alone today in one sentence.' \
  --context "{\"barks\":$(jq -c '.items' solo-bark.json),\"observations\":$(jq -c '.items' solo-obs.json)}" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file solo-report.wav
```

### 20. Pet-friendly voice routine — speak, confirm, dispense

A spoken intent triggers a registered treat-dispenser action after a
confirmation read-back.

```bash
opal listen recognition test-text --text 'give the dog a treat' --json > treat.json
INTENT=$(jq -r '.intent_name' treat.json)
opal say generate --voice-id "$VOICE_ID" \
  --text "Giving a treat for intent $INTENT." \
  --output-format wav --output-file treat-ack.wav
opal config action execute treat-dispense \
  --event "$(jq -c '{topic:"pet.reward",data:{intent:.intent_name}}' treat.json)" --json
opal data execution list --action-id treat-dispense --limit 5 --json
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Verify before alerting.** A missed meal or a bark is a signal, not a
  diagnosis — confirm with a second capture before notifying a vet or a
  pet sitter.
- **Log everything.** Published events become the vet file, the feeding
  history, and the training record all at once.
- **Replace IDs, not semantics.** Any camera, bowl station, or pipeline
  works; adapt topics and contexts to your animals and rooms.
- **Respect recognition limits.** Confidence is not a health judgment —
  use recipes to spot-check, not to diagnose.
