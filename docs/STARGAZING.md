# OPAL Stargazing Recipes

Twenty astronomy workflows that chain multiple OPAL services together —
Look watches the all-sky camera and telescope feed, Listen captures spoken
observing notes, Think identifies objects and summarizes sessions, Say
narrates alerts and reports, and Event logs every sighting for the
observing journal. Where COOKBOOK.md exercises one service per recipe,
these composite recipes pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal say voices list --json
CAMERA_ID=allsky-1                # from: opal look sources list --json
PIPELINE_ID=detector-pipeline     # from: opal look capabilities show --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Observing Sessions](#1-observing-sessions)
2. [Sky Monitoring and Alerts](#2-sky-monitoring-and-alerts)
3. [Learning and Identification](#3-learning-and-identification)
4. [Astrophotography and Records](#4-astrophotography-and-records)

## 1. Observing Sessions

### 1. Spoken sighting log — say it, save it

Dictate what you just saw at the eyepiece; the transcript becomes a dated
journal event.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file sighting.wav --save-log true --json | jq -r '.transcript')
opal event events publish --topic sky.sighting \
  --source eyepiece-mic --data "{\"note\":\"$TRANSCRIPT\"}" --json
opal event events list --topic sky.sighting --limit 10 --json
```

### 2. Sky condition check — clouds or clear?

Frame the all-sky camera and get a spoken verdict on observing conditions.

```bash
opal look sources frame "$CAMERA_ID" --output-file sky.jpg
opal look analyze image --image sky.jpg --pipeline-id "$PIPELINE_ID" --json > sky.json
OBS=$(jq -c '.observations' sky.json)
TID=$(opal think task create \
  --prompt 'Are these night-sky conditions clear, partly cloudy, or overcast? One word plus a note.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file sky-check.wav
```

### 3. Telescope session opener — spoken plan to checklist

Dictate tonight's targets; THINK orders them into a sensible observing
plan.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file plan.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Order these targets into a sensible observing plan, easiest first.' \
  --context "{\"targets\":\"$TRANSCRIPT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > observing-plan.txt
cat observing-plan.txt
```

### 4. Session timer reminder — wrap-up nudge

Log the session start as an event and set a spoken reminder check at the
end.

```bash
opal event events publish --topic sky.session \
  --source observatory --data '{"state":"started"}' --json
opal say generate --voice-id "$VOICE_ID" \
  --text 'Session logged. Give a final sky check before packing up.' \
  --output-format wav --output-file wrapup.wav
opal event events publish --topic sky.session \
  --source observatory --data '{"state":"ended"}' --json
```

### 5. Group tour narration — show the sky aloud

Point the telescope camera at a target and narrate what visitors see.

```bash
opal look sources frame telescope-cam --output-file target.jpg
opal look analyze image --image target.jpg --pipeline-id "$PIPELINE_ID" --json > t.json
OBS=$(jq -c '.observations' t.json)
TID=$(opal think task create \
  --prompt 'Describe this object for a first-time visitor in two friendly sentences.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file tour.wav
```

## 2. Sky Monitoring and Alerts

### 6. Meteor count — streak detections to event log

Meteor-like observations on the all-sky cam publish a running count.

```bash
opal look observations list --source-id "$CAMERA_ID" --label streak \
  --limit 50 --json > meteors.json
COUNT=$(jq '.items | length' meteors.json)
opal event events publish --topic sky.meteor \
  --source allsky-cam --data "{\"streaks\":$COUNT}" --json
opal event events list --topic sky.meteor --limit 10 --json
```

### 7. Aurora watch — glow detection to spoken alert

An unusual sky glow becomes a logged event plus a wake-up narration.

```bash
opal look sources frame "$CAMERA_ID" --output-file aurora.jpg
opal look analyze image --image aurora.jpg --pipeline-id "$PIPELINE_ID" --json > a.json
GLOW=$(jq '[.observations[] | select(.label=="glow" or .label=="aurora")] | length' a.json)
if [ "$GLOW" -gt 0 ]; then
  opal event events publish --topic sky.aurora \
    --source allsky-cam --data '{"glow":true}' --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Possible aurora visible on the north camera.' \
    --output-format wav --output-file aurora-alert.wav
fi
```

### 8. Clouds rolling in — deteriorating sky warning

Compare a fresh frame's observations and warn before packing up the scope.

```bash
opal look sources frame "$CAMERA_ID" --output-file now.jpg
opal look analyze image --image now.jpg --pipeline-id "$PIPELINE_ID" --json > now.json
CLOUD=$(jq '[.observations[] | select(.label=="cloud")] | length' now.json)
if [ "$CLOUD" -gt 3 ]; then
  opal event events publish --topic sky.clouds \
    --source allsky-cam --data "{\"cloud_marks\":$CLOUD}" --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Clouds building — finish this target and cover the scope.' \
    --output-format wav --output-file cloud-warning.wav
fi
```

### 9. Satellite pass sighting — bright mover to journal

A fast-moving point becomes a logged candidate for later identification.

```bash
opal look observations list --source-id "$CAMERA_ID" --label mover \
  --limit 10 --json > movers.json
COUNT=$(jq '.items | length' movers.json)
if [ "$COUNT" -gt 0 ]; then
  opal event events publish --topic sky.satellite \
    --source allsky-cam --data "{\"movers\":$COUNT}" --json
fi
```

### 10. Dew alert — optics fogging check

A hazy frame hints at dew forming on the optics.

```bash
opal look sources frame "$CAMERA_ID" --output-file dew.jpg
opal look analyze image --image dew.jpg --pipeline-id "$PIPELINE_ID" --json > dew.json
HAZE=$(jq '[.observations[] | select(.label=="haze" or .label=="fog")] | length' dew.json)
if [ "$HAZE" -gt 0 ]; then
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Possible dew on the optics — check the dew heater.' \
    --output-format wav --output-file dew-alert.wav
fi
```

## 3. Learning and Identification

### 11. What is that bright object? — eyepiece question to answer

Ask aloud what you are looking at; THINK answers from the described
context.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file what-is-it.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Identify the likely celestial object from this description: $TRANSCRIPT" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file id-answer.wav
```

### 12. Constellation tutor — spoken question to spoken lesson

Ask about a constellation and hear a short lesson for beginners.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'tell me about Orion' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Give a two-sentence beginner guide to: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file constellation.wav
```

### 13. Star-hop directions — from a known star to a faint target

Ask for hop directions aloud and get a spoken route.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'how do I star-hop to the Ring Nebula?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Give simple star-hop directions for a small telescope: $TRANSCRIPT" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file star-hop.wav
```

### 14. Magnitude and visibility explainer

Ask whether a target is visible tonight and get a plain answer.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'can I see M13 in binoculars tonight?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Answer yes or no with one reason, for a suburban sky: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 15. Equipment question — eyepiece or filter choice

Ask which eyepiece or filter suits a target and hear the suggestion.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file gear.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Recommend an eyepiece or filter in one sentence for: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file gear-advice.wav
```

## 4. Astrophotography and Records

### 16. Frame quality triage — keep or toss?

Judge a captured frame's quality before it joins the stack.

```bash
opal look analyze image --image frame-042.jpg --pipeline-id "$PIPELINE_ID" --json > frame.json
OBS=$(jq -c '.observations' frame.json)
TID=$(opal think task create \
  --prompt 'Is this astro frame sharp enough to keep for stacking? Reply keep or discard with a reason.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 17. Imaging session log — target, settings, results

Dictate capture settings and log the session for the imaging record.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file capture-notes.wav --save-log true --json | jq -r '.transcript')
opal event events publish --topic sky.imaging \
  --source camera-notes --data "{\"settings\":\"$TRANSCRIPT\"}" --json
opal event events list --topic sky.imaging --limit 10 --json
```

### 18. Plate-solving hint — describe the field

Analyze a raw frame and let THINK suggest the field for plate solving.

```bash
opal look analyze image --image field.jpg --pipeline-id "$PIPELINE_ID" --json > field.json
OBS=$(jq -c '.observations' field.json)
TID=$(opal think task create \
  --prompt 'Guess which sky region this star field likely shows, for plate solving. One sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > field-hint.txt
cat field-hint.txt
```

### 19. Session recap — night's log to narrated summary

Roll up the night's sightings and imaging events into a spoken recap.

```bash
for TOPIC in sky.sighting sky.imaging sky.meteor sky.session; do
  opal event events list --topic "$TOPIC" --limit 10 --json
done > night.jsonl
TID=$(opal think task create \
  --prompt 'Summarize tonight\'s observing session in three sentences for a logbook.' \
  --context "$(jq -cs '{events:.}' night.jsonl)" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file night-recap.wav
```

### 20. Next-target picker — journal review to suggestion

Review recent sightings and let THINK suggest tonight's best target.

```bash
opal event events list --topic sky.sighting --limit 20 --json > journal.json
TID=$(opal think task create \
  --prompt 'From this observing journal, suggest one target worth revisiting tonight and why.' \
  --context "$(jq -c '{items:.items}' journal.json)" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file next-target.wav
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Separate seeing from saying.** A camera verdict and a spoken narration
  are different services — keep both for the record.
- **Log first, identify later.** Publish sightings as they happen; THINK
  identification can run on the journal afterwards.
- **Replace IDs, not semantics.** Any all-sky, telescope, or finder camera
  works; adapt topics and contexts to your site.
- **Respect recognition limits.** A bright streak or glow is a candidate,
  not a confirmed object — verify before announcing to the group.
