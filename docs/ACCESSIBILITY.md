# OPAL Accessibility Recipes

Twenty assistive workflows that chain multiple OPAL services together —
Listen turns speech into text and intent, Look describes the visual world,
Think simplifies and explains, Say speaks the answer, and Event records
alerts that other systems can act on. Where COOKBOOK.md exercises one
service per recipe, these composite recipes pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal config voice list --json
CAMERA_ID=hallway-1               # from: opal look source list --json
PIPELINE_ID=detector-pipeline     # from: opal look info capabilities --json
OCR_PIPELINE=text-pipeline        # from: opal look info capabilities --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Vision Assistance](#1-vision-assistance)
2. [Hearing Assistance](#2-hearing-assistance)
3. [Motor and Mobility Support](#3-motor-and-mobility-support)
4. [Cognitive and Daily Living Support](#4-cognitive-and-daily-living-support)

## 1. Vision Assistance

### 1. Scene description on demand

Frame what the camera sees, analyze it, and hear a plain-English
description.

```bash
opal look source frame "$CAMERA_ID" --output-file scene.jpg
opal look analyze image --image scene.jpg --pipeline-id "$PIPELINE_ID" --json > scene.json
OBS=$(jq -c '.observations' scene.json)
TID=$(opal think task create \
  --prompt 'Describe this scene for a blind person in one clear sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file scene.wav
```

### 2. Read printed mail aloud

OCR a letter or bill and hear it read back — no screen required.

```bash
opal look analyze image --image letter.jpg --pipeline-id "$OCR_PIPELINE" --json > mail.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' mail.json)
opal say generate --voice-id "$VOICE_ID" --text "$TEXT" \
  --output-format wav --output-file mail-audio.wav
```

### 3. Label mystery items

Photograph an unlabeled jar, tool, or package and hear what it likely is.

```bash
opal look analyze image --image item.jpg --pipeline-id "$PIPELINE_ID" --json > item.json
OBS=$(jq -c '.observations' item.json)
TID=$(opal think task create \
  --prompt 'Name this household item in one short phrase.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file item-label.wav
```

### 4. Sign and notice reader

Photograph a sign, menu board, or posted notice and hear the text.

```bash
opal look analyze image --image sign.jpg --pipeline-id "$OCR_PIPELINE" --json > sign.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' sign.json)
opal say generate --voice-id "$VOICE_ID" --text "The sign says: $TEXT" \
  --output-format wav --output-file sign.wav
```

### 5. Obstacle check before moving

Frame the path ahead and hear whether anything is in the way.

```bash
opal look source frame "$CAMERA_ID" --output-file path.jpg
opal look analyze image --image path.jpg --pipeline-id "$PIPELINE_ID" --json > path.json
OBS=$(jq -c '.observations' path.json)
TID=$(opal think task create \
  --prompt 'Say "clear" if the walkway is unobstructed, otherwise name the obstacle briefly.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file path-check.wav
```

## 2. Hearing Assistance

### 6. Doorbell or knock alert to a text event

A captured door sound becomes a logged event that lights, watches, or
phones can react to.

```bash
opal listen recognition test-audio --file doorbell.wav --save-log true --json > door.json
opal data event publish --topic home.alert.sound \
  --source door-mic --data "$(jq -c '{heard:.transcript,matched:.matched}' door.json)" --json
opal data event list --topic home.alert.sound --limit 10 --json
```

### 7. Spoken visitor reply to text

Transcribe what the visitor said so it can be read instead of heard.

```bash
opal listen recognition test-audio --file visitor.wav --json > visitor.json
jq -r '.transcript' visitor.json > visitor-said.txt
cat visitor-said.txt
opal data event publish --topic home.door.transcript \
  --source door-mic --data "$(jq -c '{transcript:.transcript}' visitor.json)" --json
```

### 8. Speech-to-text notes

Dictate a reminder and keep it as a text file instead of needing audio.

```bash
opal listen recognition test-audio --file reminder.wav --save-log true --json > rem.json
jq -r '.transcript' rem.json >> reminders.txt
cat reminders.txt
```

### 9. Household sound log

Log recognized sounds — smoke alarm, kettle, baby monitor — as timestamped
events.

```bash
opal listen recognition test-audio --file kitchen-sound.wav --save-log true --json > snd.json
opal data event publish --topic home.sound.log \
  --source kitchen-mic --data "$(jq -c '{heard:.transcript,matched:.matched}' snd.json)" --json
opal data event list --topic home.sound.log --limit 20 --json
```

### 10. Live caption feed

Stream the latest recognized transcripts to a text display or file.

```bash
opal listen recognition status --json | jq -r '.running'
opal listen recognition stream --json
```

## 3. Motor and Mobility Support

### 11. Voice-only device control

A spoken phrase resolves to an intent and executes the registered action —
no hands needed.

```bash
opal listen recognition test-text --text 'turn on the living room fan' --json > fan.json
opal config action execute living-fan-on \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name,slots:.slot_values}}' fan.json)" --json
```

### 12. Hands-free call for help

A spoken help intent publishes an alert and confirms out loud.

```bash
opal listen recognition test-audio --file help-call.wav --save-log true --json > help.json
if [ "$(jq -r '.matched' help.json)" = "true" ]; then
  opal data event publish --topic home.alert.help \
    --source voice-button --data "$(jq -c '{intent:.intent_name}' help.json)" --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Help request sent.' --output-format wav --output-file help-ack.wav
fi
```

### 13. No-touch light control

Change lighting with a phrase; the action executes on the event bus.

```bash
opal listen recognition test-text --text 'dim the bedroom lights' --json > dim.json
opal config action execute bedroom-lights-dim \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name}}' dim.json)" --json
```

### 14. Voice dictation to a document

Speak a paragraph and append the transcript to a running document.

```bash
opal listen recognition test-audio --file dictation.wav --save-log true --json > dict.json
jq -r '.transcript' dict.json >> document.txt
wc -l document.txt
```

### 15. Confirmed action remote

For actions with side effects, speak the command, hear the read-back, then
execute after local confirmation.

```bash
opal listen recognition test-audio --file command.wav --json > cmd.json
INTENT=$(jq -r '.intent_name' cmd.json)
opal say generate --voice-id "$VOICE_ID" \
  --text "Command recognized as $INTENT. Press confirm to run it." \
  --output-format wav --output-file confirm.wav
opal config action execute "$INTENT" \
  --event "$(jq -c '{topic:"home.command",data:{intent:.intent_name}}' cmd.json)" --json
```

## 4. Cognitive and Daily Living Support

### 16. Medication reminder voice check

Ask whether it is time; THINK checks a simple schedule context and Say
reminds gently.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'do I take my pills now?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Using this schedule, answer yes or no and which dose is due.' \
  --context "{\"question\":\"$TRANSCRIPT\",\"schedule\":{\"morning\":\"08:00\",\"evening\":\"20:00\"}}" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file meds.wav
```

### 17. Appliance step coach

Photograph a microwave, washer, or thermostat and hear step-by-step use.

```bash
opal look analyze image --image appliance.jpg --pipeline-id "$OCR_PIPELINE" --json > app.json
OBS=$(jq -c '.observations' app.json)
TID=$(opal think task create \
  --prompt 'Give three simple numbered steps to use this appliance.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file coach.wav
```

### 18. Simplify complex text

Paste dense instructions or a form and hear a plain-language version.

```bash
opal look analyze image --image form.jpg --pipeline-id "$OCR_PIPELINE" --json > form.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' form.json)
TID=$(opal think task create \
  --prompt 'Rewrite this text in plain, simple language, one idea per sentence.' \
  --context "{\"text\":\"$TEXT\"}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file simplified.wav
```

### 19. Orientation helper — what room is this?

Frame the surroundings and hear a short orientation description.

```bash
opal look source frame "$CAMERA_ID" --output-file room.jpg
opal look analyze image --image room.jpg --pipeline-id "$PIPELINE_ID" --json > room.json
OBS=$(jq -c '.observations' room.json)
TID=$(opal think task create \
  --prompt 'Name the room and the two most important things in it for orientation.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file orientation.wav
```

### 20. Spoken daily check-in journal

Dictate a daily check-in; the transcript becomes a dated event the family
or caregiver can review.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file check-in.wav --save-log true --json | jq -r '.transcript')
opal data event publish --topic care.check_in \
  --source daily-journal --data "{\"note\":\"$TRANSCRIPT\"}" --json
opal data event list --topic care.check_in --limit 7 --json
```

## Practical Notes

- **Keep prompts literal and short.** Accessibility output should be one
  clear sentence before detail — adjust the THINK prompt, not the services.
- **Confirm risky intents.** Actions that unlock, disable, or call for help
  deserve a spoken read-back before `actions execute`.
- **Extract fields explicitly with `jq`.** `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` are the reliable handoff points.
- **Prefer text and audio together.** Most recipes produce a transcript and
  a WAV; pair them so the output works with or without hearing or vision.
- **Respect recognition limits.** Confidence is not identity — review
  transcripts before acting on health- or safety-related commands.
