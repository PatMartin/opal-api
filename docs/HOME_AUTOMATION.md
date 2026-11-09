# OPAL Home Automation Recipes

Twenty household workflows that chain multiple OPAL services together —
Listen hears a command, Look sees the house, Think decides what it means,
Say answers back, and Event records and triggers automations. Where
COOKBOOK.md exercises one service per recipe, these composite recipes pass
results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, `RULE_ID`, ...) with values from your deployment, and set
these once per shell:

```bash
VOICE_ID=narrator                 # from: opal say voices list --json
CAMERA_ID=front-door              # from: opal look sources list --json
PIPELINE_ID=detector-pipeline     # from: opal look info capabilities --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Voice-Controlled Home](#1-voice-controlled-home)
2. [Monitoring and Security](#2-monitoring-and-security)
3. [Household Status and Notifications](#3-household-status-and-notifications)
4. [Automation and Maintenance](#4-automation-and-maintenance)

## 1. Voice-Controlled Home

### 1. Voice-controlled light — spoken command to action execution

Listen resolves the spoken phrase to an intent, then a registered Event
action drives the device.

```bash
opal listen recognition test-text \
  --text 'turn on the kitchen light' --save-log true --json > cmd.json
jq -r '{intent_name, matched, slot_values}' cmd.json
# when matched, trigger the mapped automation action
opal event actions execute kitchen-light-on \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name,slots:.slot_values}}' cmd.json)" \
  --json
```

### 2. Thermostat by voice — command with slot value

The spoken setpoint lands in `slot_values` and is forwarded to a
climate-control action.

```bash
opal listen recognition test-text \
  --text 'set the thermostat to 21 degrees' --json > hvac.json
TEMP=$(jq -r '.slot_values.degrees // empty' hvac.json)
opal event actions execute thermostat-set \
  --event "$(jq -nc --arg t "$TEMP" '{topic:"home.climate",data:{setpoint_c:$t}}')" \
  --json
```

### 3. Confirmation loop — speak, confirm, act

Risky commands get a spoken read-back before the action executes.

```bash
opal listen recognition test-audio --file unlock-request.wav --json > req.json
INTENT=$(jq -r '.intent_name' req.json)
opal say generate --voice-id "$VOICE_ID" \
  --text "You asked to run intent $INTENT. Confirm on the panel to proceed." \
  --output-format wav --output-file confirm.wav
# after local confirmation:
opal event actions execute front-door-unlock \
  --event "$(jq -c '{topic:"home.access",data:{intent:.intent_name}}' req.json)" --json
```

### 4. Scene activation — one phrase, many devices

One spoken intent fans out to several registered actions and the results
are inspected afterwards.

```bash
opal listen recognition test-text --text 'movie night' --json > scene.json
for ACTION in lights-dim blinds-close projector-on; do
  opal event actions execute "$ACTION" \
    --event "$(jq -c '{topic:"home.scene",data:{scene:.intent_name}}' scene.json)" --json
done
opal event executions list --limit 10 --json
```

### 5. Guest wakeword — custom intent for visitors

Register a guest-friendly intent phrase and verify it matches.

```bash
opal listen intents add --name guest-lights \
  --phrases '["lights please","can you turn the lights on"]' \
  --enabled true --if-match '"CURRENT_CONFIG_ETAG"' --json
opal listen recognition test-text --text 'lights please' --json
```

## 2. Monitoring and Security

### 6. Porch check — who's at the door

Frame the doorbell camera, analyze the image, and get a spoken answer.

```bash
opal look sources frame "$CAMERA_ID" --output-file porch.jpg
opal look analyze image --image porch.jpg --pipeline-id "$PIPELINE_ID" --json > porch.json
OBS=$(jq -c '.observations' porch.json)
TID=$(opal think task create \
  --prompt 'Describe who or what is at the front door in one sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > door.txt
opal say generate --voice-id "$VOICE_ID" --text "$(cat door.txt)" \
  --output-format wav --output-file door-report.wav
```

### 7. Delivery review — package spotted to notification

Look detects a package observation and Event notifies the household
timeline.

```bash
opal look observations list --source-id "$CAMERA_ID" --label package \
  --limit 10 --json > pkgs.json
COUNT=$(jq '.items | length' pkgs.json)
if [ "$COUNT" -gt 0 ]; then
  opal event events publish --topic home.delivery --source front-door \
    --data "{\"packages_seen\":$COUNT}" --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'A delivery was spotted at the front door.' \
    --output-format wav --output-file delivery.wav
fi
```

### 8. Is the garage door open? — status question to spoken answer

Frame the garage camera and let THINK judge the door state.

```bash
opal look sources frame garage-1 --output-file garage.jpg
opal look analyze image --image garage.jpg --pipeline-id "$PIPELINE_ID" --json > g.json
OBS=$(jq -c '.observations' g.json)
TID=$(opal think task create \
  --prompt 'Is the garage door open or closed? Answer with one word plus confidence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file garage-answer.wav
```

### 9. Night perimeter sweep — every camera, one report

Frame each outdoor source, collect observations, and let THINK summarize
anything unusual.

```bash
for SRC in front-door garage-1 backyard; do
  opal look sources frame "$SRC" --output-file "night-$SRC.jpg"
  opal look analyze image --image "night-$SRC.jpg" \
    --pipeline-id "$PIPELINE_ID" --json > "night-$SRC.json"
done
OBS=$(jq -sc '[.[].observations]' night-*.json)
TID=$(opal think task create \
  --prompt 'Report anything unusual in these nighttime camera observations, or say all clear.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 180 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 10. Unknown face alert — detection to security event

Unfamiliar-person observations publish a security topic for downstream
rules and actions.

```bash
opal look observations list --source-id "$CAMERA_ID" --label person \
  --limit 25 --json > people.json
UNKNOWN=$(jq '[.items[] | select(.attributes.known==false)] | length' people.json)
if [ "$UNKNOWN" -gt 0 ]; then
  opal event events publish --topic home.security.unknown_person \
    --source "$CAMERA_ID" --data "{\"count\":$UNKNOWN}" --json
fi
opal event events list --topic home.security.unknown_person --limit 10 --json
```

## 3. Household Status and Notifications

### 11. Morning briefing — house status narrated

Gather camera status, recognition status, and event stats into one spoken
briefing.

```bash
CAM=$(opal look sources status "$CAMERA_ID" --json | jq -c '{state:.state}')
REC=$(opal listen recognition status --json | jq -c '{running:.running}')
EVT=$(opal event data stats show --json | jq -c '{observed:.observed_events}')
TID=$(opal think task create \
  --prompt 'Write a friendly two-sentence morning house briefing from this status.' \
  --context "{\"camera\":$CAM,\"recognition\":$REC,\"events\":$EVT}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file morning-briefing.wav
```

### 12. Plant watering reminder — photo check to nudge

Look at the plant shelf; THINK judges dryness and Say reminds.

```bash
opal look sources frame plant-shelf --output-file plants.jpg
opal look analyze image --image plants.jpg --pipeline-id "$PIPELINE_ID" --json > p.json
OBS=$(jq -c '.observations' p.json)
TID=$(opal think task create \
  --prompt 'Do these plants look like they need water today? Answer yes or no with a reason.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > water.txt
grep -qi '^yes' water.txt && opal say generate --voice-id "$VOICE_ID" \
  --text 'Reminder: the plants need watering.' \
  --output-format wav --output-file water-reminder.wav
```

### 13. Laundry done? — appliance status check to notification

A camera or sensor observation decides whether the washer finished; the
household gets a spoken ping.

```bash
opal look sources frame laundry --output-file washer.jpg
opal look analyze image --image washer.jpg --pipeline-id "$PIPELINE_ID" --json > w.json
STATE=$(jq -r '.observations[0].label // "unknown"' w.json)
if [ "$STATE" = "cycle_done" ]; then
  opal say generate --voice-id "$VOICE_ID" \
    --text 'The laundry cycle is finished.' \
    --output-format wav --output-file laundry.wav
  opal event events publish --topic home.chores --source laundry \
    --data '{"washer":"cycle_done"}' --json
fi
```

### 14. Fridge inventory snapshot — photo to shopping list

Photograph the fridge shelf; THINK lists what looks low.

```bash
opal look sources frame fridge-cam --output-file fridge.jpg
opal look analyze image --image fridge.jpg --pipeline-id "$OCR_PIPELINE" --json > fridge.json
OBS=$(jq -c '.observations' fridge.json)
TID=$(opal think task create \
  --prompt 'List items that look nearly empty or missing from this fridge shelf.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > shopping-list.txt
cat shopping-list.txt
```

### 15. Mailbox check — did the post arrive?

A quick frame and analysis answers whether the mailbox is full.

```bash
opal look sources frame mailbox --output-file mail.jpg
opal look analyze image --image mail.jpg --pipeline-id "$PIPELINE_ID" --json > m.json
HAS_MAIL=$(jq -r '[.observations[] | select(.label=="mail")] | length' m.json)
opal say generate --voice-id "$VOICE_ID" \
  --text "$([ "$HAS_MAIL" -gt 0 ] && echo 'Mail has arrived.' || echo 'No mail yet.')" \
  --output-format wav --output-file mail.wav
```

## 4. Automation and Maintenance

### 16. Porch light at dusk — rule-driven automation

Register a rule that turns on the porch light when a person is detected
after sunset, then test it before enabling.

```bash
opal event rules test porch-light-rule \
  --event '{"topic":"home.camera.front","data":{"label":"person","hour":21}}' --json
opal event actions execute porch-light-on \
  --event '{"topic":"home.camera.front","data":{"label":"person","hour":21}}' --json
opal event executions list --action-id porch-light-on --limit 5 --json
```

### 17. Water leak triage — sensor event to spoken warning

A leak sensor event becomes a THINK-triaged, spoken household warning.

```bash
opal event events publish --topic home.sensor.water \
  --source basement-sensor --data '{"leak":true,"zone":"basement"}' --json
TID=$(opal think task create \
  --prompt 'Draft a calm one-sentence spoken alert for a basement water leak and one immediate action.' \
  --context '{"leak":true,"zone":"basement"}' --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file leak-alert.wav
```

### 18. Camera health patrol — probe every source

Check each registered source and publish any degraded ones for follow-up.

```bash
for SRC in $(opal look sources list --json | jq -r '.items[].id'); do
  STATE=$(opal look sources status "$SRC" --json | jq -r '.state')
  if [ "$STATE" != "ok" ] && [ "$STATE" != "online" ]; then
    opal event events publish --topic home.maintenance.camera --source patrol \
      --data "{\"source\":\"$SRC\",\"state\":\"$STATE\"}" --json
  fi
done
opal event events list --topic home.maintenance.camera --limit 10 --json
```

### 19. Voice command audit — what did the house hear?

Review recent recognitions and failed utterances to tune the vocabulary.

```bash
opal listen data failed-utterance list --limit 25 --json > misses.json
jq '.items[] | {transcript, expected_intent}' misses.json
opal listen data failed-utterance list --reviewed false --limit 25 --json > review.json
jq '.items[] | {id, transcript, expected_intent}' review.json
```

### 20. Config handoff — move household automation to a second hub

Export, validate, and re-import portable configuration between hubs.

```bash
opal listen backup export --json > listen-home.json
opal listen backup validate --request @listen-home.json --json
# on the second hub:
opal listen backup import --request @listen-home.json \
  --if-match '"TARGET_CONFIG_ETAG"' --json
opal event events publish --topic home.admin --source migration \
  --data '{"action":"config_handoff","service":"listen"}' --json
```

## Practical Notes

- **Chain with `jq`.** Extract handoff fields (`transcript`, `.id`,
  `.answer`, `.observations`, `.slot_values`) explicitly; do not assume
  field order.
- **Separate detection from action.** Observations and events are facts;
  actions are the consequence. Testing rules before enabling them keeps a
  house safe.
- **Confirm risky intents.** Anything that unlocks, disables, or heats is
  worth a spoken read-back before `actions execute`.
- **Use `--json` on producer steps** so pipes stay clean; narration files go
  to `--output-file`.
- **Respect recognition limits.** Confidence is not identity or intent
  certainty — review transcripts for commands that affect security.
