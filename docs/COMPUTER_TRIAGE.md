# OPAL Computer Triage Recipes

Twenty IT and helpdesk workflows that chain multiple OPAL services
together — Look reads error screens and rack lights, Listen captures
spoken problem reports, Think diagnoses and drafts fixes, Say reads
verdicts aloud, and Event logs incidents for the ticket trail. Where
COOKBOOK.md exercises one service per recipe, these composite recipes
pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`OCR_PIPELINE`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal say voices list --json
CAMERA_ID=rack-1                  # from: opal look sources list --json
OCR_PIPELINE=text-pipeline        # from: opal look capabilities show --json
PIPELINE_ID=detector-pipeline     # from: opal look capabilities show --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Error Reading and Diagnosis](#1-error-reading-and-diagnosis)
2. [Incident Capture and Logging](#2-incident-capture-and-logging)
3. [Hardware and Facilities Checks](#3-hardware-and-facilities-checks)
4. [Resolution and Follow-up](#4-resolution-and-follow-up)

## 1. Error Reading and Diagnosis

### 1. Error dialog to plain-English fix

Photograph a baffling error dialog and hear what it means and what to do.

```bash
opal look analyze image --image error-dialog.png --pipeline-id "$OCR_PIPELINE" --json > err.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' err.json)
TID=$(opal think task create \
  --prompt 'Explain this error in one sentence and give one fix step.' \
  --context "{\"error\":\"$TEXT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file error-fix.wav
```

### 2. Spoken symptom to diagnosis hints

Dictate a user's symptom description and get likely causes back.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file symptom.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'List the three most likely causes of this reported symptom, one line each.' \
  --context "{\"symptom\":\"$TRANSCRIPT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > diagnosis.txt
cat diagnosis.txt
```

### 3. Screenshot stack trace to summary

OCR a stack trace and get a one-paragraph triage summary.

```bash
opal look analyze image --image stacktrace.png --pipeline-id "$OCR_PIPELINE" --json > st.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' st.json)
TID=$(opal think task create \
  --prompt 'Summarize this stack trace: probable cause, affected component, first fix to try.' \
  --context "{\"trace\":\"$TEXT\"}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > triage-summary.txt
```

### 4. Blue screen of death capture

Photograph a BSOD and get an immediate spoken read of the stop code.

```bash
opal look analyze image --image bsod.jpg --pipeline-id "$OCR_PIPELINE" --json > bsod.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' bsod.json)
TID=$(opal think task create \
  --prompt 'Name the stop code and the most likely cause in one sentence.' \
  --context "{\"screen\":\"$TEXT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file bsod-verdict.wav
```

### 5. Slow machine — spoken complaint to checklist

Dictate "computer is slow" symptoms and get a structured check plan.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'the laptop takes ten minutes to boot and fans spin loudly' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Give a five-step diagnostic checklist for this slow-computer complaint.' \
  --context "{\"complaint\":\"$TRANSCRIPT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > checklist.txt
cat checklist.txt
```

## 2. Incident Capture and Logging

### 6. User voice report to ticket event

A user's spoken problem report becomes a timestamped incident event.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file report.wav --save-log true --json | jq -r '.transcript')
opal event events publish --topic it.incident.report \
  --source helpdesk-mic --data "{\"report\":\"$TRANSCRIPT\"}" --json
opal event events list --topic it.incident.report --limit 10 --json
```

### 7. Photo evidence to the ticket

Attach a photo of the failing setup to the incident event.

```bash
opal look analyze image --image setup-fault.jpg --pipeline-id "$OCR_PIPELINE" --json > ev.json
OBS=$(jq -c '.observations' ev.json)
opal event events publish --topic it.incident.evidence \
  --source desk-photo --data "{\"observations\":$OBS}" --json
```

### 8. Service status rollup — what's degraded?

Collect service health and publish a degraded summary.

```bash
LISTEN_STATE=$(opal listen health ready --json | jq -r '.status // "unknown"')
LOOK_STATE=$(opal look health ready --json | jq -r '.status // "unknown"')
opal event events publish --topic it.status \
  --source status-poll \
  --data "{\"listen\":\"$LISTEN_STATE\",\"look\":\"$LOOK_STATE\"}" --json
opal event events list --topic it.status --limit 10 --json
```

### 9. Repeat-offender detection — same error again?

Search incident events for a recurring error before escalating.

```bash
opal event events list --topic it.incident.report --limit 50 --json > incidents.json
COUNT=$(jq '[.items[] | select(.data.report | test("printer"))] | length' incidents.json)
if [ "$COUNT" -gt 3 ]; then
  opal event events publish --topic it.incident.pattern \
    --source triage --data "{\"recurring\":\"printer\",\"count\":$COUNT}" --json
fi
```

### 10. Priority triage — urgent or queue?

Let THINK score a report's urgency and route it.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file urgent.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Rate this incident P1 outage, P2 degraded, or P3 routine, with a one-line reason.' \
  --context "{\"report\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
PRIORITY=$(opal think task show "$TID" --json | jq -er '.answer')
opal event events publish --topic it.incident.priority \
  --source triage --data "{\"priority\":\"$PRIORITY\"}" --json
```

## 3. Hardware and Facilities Checks

### 11. Rack status LEDs — green or angry?

Frame the rack and read the LED state visually.

```bash
opal look sources frame "$CAMERA_ID" --output-file rack.jpg
opal look analyze image --image rack.jpg --pipeline-id "$PIPELINE_ID" --json > rack.json
ALERT=$(jq '[.observations[] | select(.label=="led_red" or .label=="led_amber")] | length' rack.json)
if [ "$ALERT" -gt 0 ]; then
  opal event events publish --topic it.hardware.alert \
    --source rack-cam --data "{\"warning_leds\":$ALERT}" --json
fi
```

### 12. Cable and port photo ID

Photograph a mystery cable or port and identify it aloud.

```bash
opal look analyze image --image cable.jpg --pipeline-id "$PIPELINE_ID" --json > cable.json
OBS=$(jq -c '.observations' cable.json)
TID=$(opal think task create \
  --prompt 'Name this cable or connector in one short phrase.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file cable-id.wav
```

### 13. Printer status panel read

OCR the printer's LCD panel and log its state for the floor's printer
map.

```bash
opal look analyze image --image printer-panel.jpg --pipeline-id "$OCR_PIPELINE" --json > pp.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' pp.json)
opal event events publish --topic it.printer.status \
  --source floor-2 --data "{\"panel\":\"$TEXT\"}" --json
```

### 14. UPS battery check

Photograph the UPS display and flag anything below healthy.

```bash
opal look analyze image --image ups.jpg --pipeline-id "$OCR_PIPELINE" --json > ups.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' ups.json)
TID=$(opal think task create \
  --prompt 'Is this UPS reading healthy? Answer yes or describe the warning.' \
  --context "{\"display\":\"$TEXT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 15. Server fan noise check

Audio-capture a rack fan's noise before it becomes a failure.

```bash
opal listen recognition test-audio --file fan-noise.wav --save-log true --json > fan.json
if [ "$(jq -r '.matched' fan.json)" = "true" ]; then
  opal event events publish --topic it.hardware.fan \
    --source rack-mic --data '{"noisy_fan":true}' --json
fi
```

## 4. Resolution and Follow-up

### 16. Draft a fix-it message for the user

THINK writes a friendly user-facing reply from the diagnosis.

```bash
TID=$(opal think task create \
  --prompt 'Write a two-sentence user-facing reply explaining the fix and the workaround.' \
  --context "$(jq -c '{diagnosis:.}' diagnosis.txt 2>/dev/null || echo '{"diagnosis":"restart the print spooler"}')" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > user-reply.txt
cat user-reply.txt
```

### 17. Post-fix verification — is it actually fixed?

Re-run the original check and confirm the incident cleared.

```bash
opal listen health ready --json | jq -r '.status'
opal look health ready --json | jq -r '.status'
opal event events publish --topic it.incident.resolved \
  --source post-check --data '{"verified":true}' --json
```

### 18. Spoken resolution notes to the log

Dictate what fixed it; the transcript closes the incident record.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file resolution.wav --save-log true --json | jq -r '.transcript')
opal event events publish --topic it.incident.resolution \
  --source helpdesk --data "{\"fix\":\"$TRANSCRIPT\"}" --json
```

### 19. Knowledge-base draft from a solved ticket

THINK turns a solved incident thread into a KB article draft.

```bash
opal event events list --topic it.incident.resolution --limit 10 --json > resolved.json
TID=$(opal think task create \
  --prompt 'Draft a short internal KB article from these resolutions: symptom, cause, fix.' \
  --context "$(jq -c '{items:.items}' resolved.json)" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > kb-draft.md
cat kb-draft.md
```

### 20. Weekly helpdesk digest — narrated summary

Summarize the week's incidents into a spoken team digest.

```bash
for TOPIC in it.incident.report it.incident.priority it.incident.resolution; do
  opal event events list --topic "$TOPIC" --limit 20 --json
done > week.jsonl
TID=$(opal think task create \
  --prompt 'Summarize this week of helpdesk events in three sentences for the team.' \
  --context "$(jq -cs '{events:.}' week.jsonl)" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file weekly-digest.wav
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Photo first, fix second.** Error dialogs, panels, and LEDs all go
  through `analyze image` — keep the evidence before clearing the fault.
- **Log every incident.** Published events build the audit trail that
  makes recurring problems visible.
- **Triage before acting.** A THINK priority call is advisory — confirm
  P1s with a human check before paging anyone.
- **Replace IDs, not semantics.** Any rack cam, OCR pipeline, or voice ID
  works; adapt topics and contexts to your environment.
