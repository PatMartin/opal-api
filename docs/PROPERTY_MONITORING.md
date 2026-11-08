# OPAL Property Monitoring Recipes

Twenty landlord and facilities workflows that chain multiple OPAL services
together — Look inspects units and common areas, Listen captures reports
and checks audio, Think judges condition and drafts summaries, Say reads
alerts or summaries aloud, and Event logs everything for the record. Where
COOKBOOK.md exercises one service per recipe, these composite recipes pass
results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal say voices list --json
CAMERA_ID=unit-101-entry          # from: opal look sources list --json
PIPELINE_ID=detector-pipeline     # from: opal look capabilities show --json
OCR_PIPELINE=text-pipeline        # from: opal look capabilities show --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Vacancy and Turnover Checks](#1-vacancy-and-turnover-checks)
2. [Maintenance and Issue Detection](#2-maintenance-and-issue-detection)
3. [Tenant and Amenity Monitoring](#3-tenant-and-amenity-monitoring)
4. [Inspection and Reporting](#4-inspection-and-reporting)

## 1. Vacancy and Turnover Checks

### 1. Vacancy verification — is the unit actually empty?

Frame the unit's camera and let THINK judge whether it looks occupied.

```bash
opal look sources frame unit-101-entry --output-file unit-101.jpg
opal look analyze image --image unit-101.jpg --pipeline-id "$PIPELINE_ID" --json > u.json
OBS=$(jq -c '.observations' u.json)
TID=$(opal think task create \
  --prompt 'Does this room look vacant and show-ready? Answer yes or no with a reason.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 2. Move-out condition snapshot

Capture the unit's condition at turnover and log it as a dated event for
the deposit file.

```bash
opal look sources frame unit-101-entry --output-file moveout-101.jpg
opal look analyze image --image moveout-101.jpg --pipeline-id "$PIPELINE_ID" --json > c.json
OBS=$(jq -c '.observations' c.json)
opal event events publish --topic property.turnover \
  --source unit-101 --data "{\"unit\":\"101\",\"observations\":$OBS}" --json
opal event events list --topic property.turnover --limit 10 --json
```

### 3. Pre-show readiness check

Before a showing, verify lights on, beds made, no visible damage.

```bash
opal look sources frame unit-101-entry --output-file presales.jpg
opal look analyze image --image presales.jpg --pipeline-id "$PIPELINE_ID" --json > s.json
OBS=$(jq -c '.observations' s.json)
TID=$(opal think task create \
  --prompt 'Is this unit show-ready? Check lighting, tidiness, and visible damage. Reply pass or fix-list.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > show-ready.txt
cat show-ready.txt
```

### 4. Left-behind items check

After move-out, check for abandoned furniture or boxes that need removal.

```bash
opal look analyze image --image empty-unit.jpg --pipeline-id "$PIPELINE_ID" --json > left.json
ITEMS=$(jq '[.observations[] | select(.label=="box" or .label=="furniture")] | length' left.json)
if [ "$ITEMS" -gt 0 ]; then
  opal event events publish --topic property.turnover.items \
    --source unit-101 --data "{\"abandoned_items\":$ITEMS}" --json
  opal say generate --voice-id "$VOICE_ID" \
    --text "Unit 101 still contains $ITEMS items." \
    --output-format wav --output-file items-alert.wav
fi
```

### 5. Post-clean quality verification

After the cleaning crew finishes, verify the unit passed.

```bash
opal look sources frame unit-101-entry --output-file postclean.jpg
opal look analyze image --image postclean.jpg --pipeline-id "$PIPELINE_ID" --json > pc.json
OBS=$(jq -c '.observations' pc.json)
TID=$(opal think task create \
  --prompt 'Judge whether this room looks professionally cleaned. Reply pass or needs-work with a reason.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

## 2. Maintenance and Issue Detection

### 6. Leak under the sink — photo triage

A tenant's under-sink photo is analyzed and triaged into an urgent event
or a routine work order.

```bash
opal look analyze image --image under-sink.jpg --pipeline-id "$PIPELINE_ID" --json > sink.json
OBS=$(jq -c '.observations' sink.json)
TID=$(opal think task create \
  --prompt 'Is this under-sink photo an active leak, a stain, or dry? Reply with one word plus a note.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
VERDICT=$(opal think task show "$TID" --json | jq -er '.answer')
opal event events publish --topic property.maintenance.leak \
  --source tenant-photo --data "{\"verdict\":\"$VERDICT\"}" --json
```

### 7. Light fixture out? — hallway lamp check

A hallway frame decides whether a fixture needs replacement.

```bash
opal look sources frame hallway-2 --output-file hall.jpg
opal look analyze image --image hall.jpg --pipeline-id "$PIPELINE_ID" --json > h.json
DARK=$(jq '[.observations[] | select(.label=="fixture_dark")] | length' h.json)
if [ "$DARK" -gt 0 ]; then
  opal event events publish --topic property.maintenance.lighting \
    --source hallway-2 --data '{"fixture":"hall-2","state":"dark"}' --json
fi
```

### 8. HVAC condenser status — equipment check to spoken verdict

Frame the outdoor unit and get a spoken maintenance verdict.

```bash
opal look sources frame hvac-pad --output-file hvac.jpg
opal look analyze image --image hvac.jpg --pipeline-id "$PIPELINE_ID" --json > hvac.json
OBS=$(jq -c '.observations' hvac.json)
TID=$(opal think task create \
  --prompt 'Does this HVAC condenser look damaged, blocked, or clear? One sentence.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file hvac-verdict.wav
```

### 9. Water stain watch — ceiling check over time

Repeated frames flag a growing ceiling stain before it becomes a claim.

```bash
opal look sources frame unit-201-ceiling --output-file ceiling.jpg
opal look analyze image --image ceiling.jpg --pipeline-id "$PIPELINE_ID" --json > ceil.json
STAIN=$(jq '[.observations[] | select(.label=="water_stain")] | length' ceil.json)
if [ "$STAIN" -gt 0 ]; then
  opal event events publish --topic property.maintenance.stain \
    --source unit-201 --data "{\"stains\":$STAIN}" --json
fi
```

### 10. Broken window check — exterior frame to event

An exterior frame flags broken glazing for the maintenance queue.

```bash
opal look sources frame exterior-east --output-file ext.jpg
opal look analyze image --image ext.jpg --pipeline-id "$PIPELINE_ID" --json > ext.json
BROKEN=$(jq '[.observations[] | select(.label=="broken_glass")] | length' ext.json)
if [ "$BROKEN" -gt 0 ]; then
  opal event events publish --topic property.maintenance.glazing \
    --source exterior-east --data "{\"broken_windows\":$BROKEN}" --json
fi
```

## 3. Tenant and Amenity Monitoring

### 11. Noise complaint audio check

Capture a hallway audio clip and verify whether it crosses the noise
threshold before escalating.

```bash
opal listen recognition test-audio --file hallway-noise.wav --save-log true --json > noise.json
TRANSCRIPT=$(jq -r '.transcript' noise.json)
opal event events publish --topic property.noise \
  --source hallway-mic --data "{\"heard\":\"$TRANSCRIPT\"}" --json
```

### 12. Parking lot occupancy count

Frame the lot, count visible vehicles, and publish utilization for
tenants' parking complaints.

```bash
opal look sources frame parking-lot --output-file lot.jpg
opal look analyze image --image lot.jpg --pipeline-id "$PIPELINE_ID" --json > lot.json
CARS=$(jq '[.observations[] | select(.label=="car" or .label=="truck")] | length' lot.json)
opal event events publish --topic property.parking \
  --source lot-cam --data "{\"vehicles\":$CARS}" --json
```

### 13. Amenity room condition — pool or gym check

Verify the pool gate or gym equipment area looks safe and tidy.

```bash
opal look sources frame amenity-pool --output-file pool.jpg
opal look analyze image --image pool.jpg --pipeline-id "$PIPELINE_ID" --json > pool.json
OBS=$(jq -c '.observations' pool.json)
TID=$(opal think task create \
  --prompt 'Does this amenity area look safe and tidy for tenants? Reply yes or list issues.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 14. Common area crowd check — before quiet hours

Count people in the common room before enforcing quiet hours.

```bash
opal look sources frame common-room --output-file common.jpg
opal look analyze image --image common.jpg --pipeline-id "$PIPELINE_ID" --json > cr.json
PEOPLE=$(jq '[.observations[] | select(.label=="person")] | length' cr.json)
if [ "$PEOPLE" -gt 6 ]; then
  opal event events publish --topic property.common.crowd \
    --source common-room --data "{\"count\":$PEOPLE}" --json
fi
```

### 15. Unauthorized access after hours

Detect a person in a restricted area after hours and log a security event
plus a spoken alert.

```bash
opal look observations list --source-id garage-door --label person \
  --limit 5 --json > access.json
FOUND=$(jq '[.items[] | select(.attributes.after_hours==true)] | length' access.json)
if [ "$FOUND" -gt 0 ]; then
  opal event events publish --topic property.security.access \
    --source garage-door --data "{\"unauthorized\":$FOUND}" --json
  opal say generate --voice-id "$VOICE_ID" \
    --text 'Security notice: activity detected in the garage after hours.' \
    --output-format wav --output-file access-alert.wav
fi
```

## 4. Inspection and Reporting

### 16. Weekly hallway condition patrol

Frame each hallway, collect issues, and publish a patrol report.

```bash
for SRC in hall-1 hall-2 hall-3; do
  opal look sources frame "$SRC" --output-file "patrol-$SRC.jpg"
  opal look analyze image --image "patrol-$SRC.jpg" \
    --pipeline-id "$PIPELINE_ID" --json > "patrol-$SRC.json"
done
OBS=$(jq -sc '[.[].observations]' patrol-*.json)
opal event events publish --topic property.patrol \
  --source weekly-walk --data "{\"observations\":$OBS}" --json
```

### 17. Smoke detector check — battery chirp detection

Audio check for a chirping detector before it becomes a complaint.

```bash
opal listen recognition test-audio --file detector-chirp.wav --save-log true --json > chirp.json
if [ "$(jq -r '.matched' chirp.json)" = "true" ]; then
  opal event events publish --topic property.safety.detector \
    --source unit-101 --data '{"chirp":true}' --json
fi
```

### 18. Exterior grounds inspection

Sweep the grounds and let THINK summarize landscaping or litter issues.

```bash
for SRC in front-lawn back-lawn sidewalk; do
  opal look sources frame "$SRC" --output-file "grounds-$SRC.jpg"
  opal look analyze image --image "grounds-$SRC.jpg" \
    --pipeline-id "$PIPELINE_ID" --json > "grounds-$SRC.json"
done
OBS=$(jq -sc '[.[].observations]' grounds-*.json)
TID=$(opal think task create \
  --prompt 'Summarize grounds maintenance needs from these observations in two sentences.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > grounds-report.txt
```

### 19. Move-in welcome voice check

A new tenant's spoken check-in gets transcribed and logged for the
landlord's records.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file movein.wav --save-log true --json | jq -r '.transcript')
opal event events publish --topic property.tenant.checkin \
  --source unit-101 --data "{\"note\":\"$TRANSCRIPT\"}" --json
```

### 20. Monthly condition digest — everything in one report

Roll up the month's property events into a spoken landlord digest.

```bash
for TOPIC in property.maintenance.leak property.patrol property.turnover property.noise; do
  opal event events list --topic "$TOPIC" --limit 10 --json
done > month-events.jsonl
TID=$(opal think task create \
  --prompt 'Summarize this month of property events for a landlord in three sentences.' \
  --context "$(jq -cs '{events:.}' month-events.jsonl)" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file monthly-digest.wav
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Document, don't just detect.** Publishing every finding to a dated
  event topic builds the audit trail a deposit or insurance claim needs.
- **Verify before escalating.** A chirp or a stain deserves a second
  capture before dispatching a vendor.
- **Replace IDs, not semantics.** Any unit, camera, or pipeline ID works;
  adapt topics and contexts to your property map.
- **Respect recognition limits.** Audio detections are hints — confirm
  noisy-unit or detector claims before notifying tenants.
