# OPAL Voice Assistant Recipes

Twenty voice-assistant workflows that chain multiple OPAL services
together — Listen turns speech into text and intent, Think answers and
reasons, Say speaks the reply, Look adds visual context when needed, and
Event logs requests and scheduled reminders. Where COOKBOOK.md exercises
one service per recipe, these composite recipes pass results between
them to make a richer assistant.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once
per shell:

```bash
VOICE_ID=narrator                 # from: opal say voice list --json
CAMERA_ID=hallway-1               # from: opal look source list --json
PIPELINE_ID=detector-pipeline     # from: opal look info capabilities --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`, `slot_values`; THINK tasks carry `.id` on create and `.answer`
once `completed`; Event requires `topic` and `data`.

## Contents

1. [Spoken Q&A](#1-spoken-qa)
2. [Reminders, Notes, and Lists](#2-reminders-notes-and-lists)
3. [Conversational Assistant](#3-conversational-assistant)
4. [Briefings and Reports](#4-briefings-and-reports)

## 1. Spoken Q&A

### 1. Ask anything — spoken question to spoken answer

Transcribe the question, let THINK answer it, and hear the reply.

```bash
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

### 2. Definition lookup — hear a word explained

Ask for a definition aloud and get a one-line spoken explanation.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'what does photosynthesis mean?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Define this term in one simple sentence: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file definition.wav
```

### 3. Fact check a claim

Speak a claim and hear whether it holds up, with a reason.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file claim.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Is this claim accurate? Reply with yes, no, or partly plus a one-line reason.' \
  --context "{\"claim\":\"$TRANSCRIPT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 4. Conversion helper — units and currency

Ask for a conversion and hear the computed answer.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'how many cups are in two liters?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Compute this conversion and answer in one sentence: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file conversion.wav
```

### 5. Explain like I'm five — complex topic, simple answer

Ask a hard question aloud and get a simplified spoken explanation.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file hard-question.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Explain this in one paragraph a child could understand: $TRANSCRIPT" \
  --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file eli5.wav
```

## 2. Reminders, Notes, and Lists

### 6. Spoken reminder to event log

Dictate a reminder; it becomes a dated event the rest of the system can
act on.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file reminder.wav --save-log true --json | jq -r '.transcript')
opal event event publish --topic assistant.reminder \
  --source voice-memo --data "{\"note\":\"$TRANSCRIPT\"}" --json
opal event event list --topic assistant.reminder --limit 10 --json
```

### 7. Shopping list dictation

Speak items and append them to a running grocery list file.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file groceries.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Turn this spoken sentence into a comma-separated shopping list.' \
  --context "{\"speech\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' >> groceries.txt
cat groceries.txt
```

### 8. Read back today's reminders

Summarize pending reminder events aloud.

```bash
opal event event list --topic assistant.reminder --limit 20 --json > rem.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

### 9. Voice note to file

Dictate a paragraph and store the transcript for later.

```bash
opal listen recognition test-audio --file note.wav --save-log true --json > note.json
jq -r '.transcript' note.json >> notes.txt
wc -l notes.txt
```

### 10. Spoken to-do triage

Dictate a task list; THINK sorts by urgency and reads back the top three.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file todos.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Sort these spoken tasks by urgency and read back the top three with one phrase each.' \
  --context "{\"tasks\":\"$TRANSCRIPT\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file todos.wav
```

## 3. Conversational Assistant

### 11. Multi-turn chat session

Keep a THINK session so follow-up questions remember context.

```bash
CSID=$(opal think session add --title 'Voice assistant chat' --json | jq -er '.id')
T1=$(opal listen recognition test-audio --file turn1.wav --json | jq -r '.transcript')
TID=$(opal think task create --prompt "$T1" --session-id "$CSID" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file reply1.wav
```

### 12. Hands-free cooking help

While cooking, ask a substitution question and hear the swap aloud.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file cooking.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Give a one-sentence cooking substitution answer to: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file sub.wav
```

### 13. Recipe read-aloud

Photograph a recipe card and hear it read back step by step.

```bash
opal look analyze image --image recipe.jpg --pipeline-id "$OCR_PIPELINE" --json > recipe.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' recipe.json)
opal say generate --voice-id "$VOICE_ID" --text "$TEXT" \
  --output-format wav --output-file recipe-audio.wav
```

### 14. Bedtime story generator

Ask for a story and hear a short narrated tale.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file story-request.wav --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Tell a gentle two-paragraph bedtime story about: $TRANSCRIPT" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file story.wav
```

### 15. Quick translation spoken back

Ask for a phrase in another language and hear it pronounced.

```bash
TRANSCRIPT=$(opal listen recognition test-text --text 'how do I say thank you in Japanese?' --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt "Translate as asked and reply with just the phrase: $TRANSCRIPT" \
  --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file translation.wav
```

## 4. Briefings and Reports

### 16. Morning status briefing

Roll camera status, recognitions, and event stats into a spoken morning
summary.

```bash
opal look source status <camera_id> --json | jq -c '{state:.state}'
opal listen recognition status --json | jq -c '{running:.running}'
opal event stats show --json | jq -c '{observed:.observed_events}'
```

### 17. Event digest — what happened today

Summarize the day's event log into a spoken digest.

```bash
opal event event list --topic <topic> --limit 10 --json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

### 18. Document summary on demand

Hand THINK a text file's context and hear a two-sentence summary.

```bash
opal look analyze image --image doc.jpg --pipeline-id <ocr_pipeline> --json > doc.json
opal think task watch <tid>
opal say generate --voice-id <voice_id> \
```

### 19. Task list report — what's open

Summarize outstanding reminders and notes aloud.

```bash
NOTES=$(cat notes.txt 2>/dev/null; cat groceries.txt 2>/dev/null)
TID=$(opal think task create \
  --prompt 'Summarize open items from these notes into a short spoken list.' \
  --context "{\"notes\":\"$NOTES\"}" --timeout-seconds 60 --json | jq -er '.id')
opal think task watch "$TID"
opal say generate --voice-id "$VOICE_ID" \
  --text "$(opal think task show "$TID" --json | jq -er '.answer')" \
  --output-format wav --output-file open-items.wav
```

### 20. Weekly voice journal — spoken recap

Dictate a week-in-review and save a narrated recap file.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file week.wav --save-log true --json | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Turn this week\'s spoken recap into a three-bullet journal entry.' \
  --context "{\"recap\":\"$TRANSCRIPT\"}" --timeout-seconds 90 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > week-journal.txt
opal say generate --voice-id "$VOICE_ID" --text "$(cat week-journal.txt)" \
  --output-format wav --output-file week-journal.wav
```

## Practical Notes

- **Chain with `jq`.** Extract `transcript`, `.id`, `.answer`,
  `.observations`, and `.matched` explicitly; do not assume field order.
- **Wait for each THINK turn.** `task watch` observes but does not queue
  the next prompt — sequence session turns yourself.
- **Keep answers spoken-length.** Ask THINK for one or two sentences when
  output goes straight to `say generate` or `say stream`.
- **Log what matters.** Reminders, notes, and answers become dated events
  other systems can search or replay.
- **Respect recognition limits.** Confidence is not certainty — confirm
  transcripts for anything that triggers an external action.
