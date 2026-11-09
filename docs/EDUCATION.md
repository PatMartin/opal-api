# OPAL Education Recipes

Twenty teaching and learning workflows that chain multiple OPAL services
together — Listen hears, Look sees, Think reasons, Say speaks, and Event
records and reacts. Where COOKBOOK.md exercises one service per recipe,
these composite recipes pass results between them.

Every example is a fenced `bash` block so Markdown renderers such as GitHub
show a **Copy** button. Replace capitalized IDs (`VOICE_ID`, `CAMERA_ID`,
`PIPELINE_ID`, ...) with values from your deployment, and set these once per
shell:

```bash
VOICE_ID=narrator                 # from: opal say voice list --json
CAMERA_ID=classroom-1             # from: opal look source list --json
OCR_PIPELINE=text-pipeline        # from: opal look info capabilities --json
MODEL_ID=default                  # from: opal think model list --json
```

Field notes used below: Listen results carry `transcript`, `intent_name`,
`matched`; THINK tasks carry `.id` on create and `.answer` once `completed`;
Look image analysis returns `observations`; Event requires `topic` and `data`.

## Contents

1. [Classroom and Lecture Tools](#1-classroom-and-lecture-tools)
2. [Reading and Literacy](#2-reading-and-literacy)
3. [Language Learning](#3-language-learning)
4. [Field Learning and Research](#4-field-learning-and-research)

## 1. Classroom and Lecture Tools

### 1. Voice roll call — spoken name to attendance event

Student says their name into a clip; Listen transcribes, Event logs the
attendance record.

```bash
opal listen recognition test-audio --file student-name.wav --save-log true --json > name.json
NAME=$(jq -r '.transcript' name.json)
opal event event publish --topic classroom.attendance \
  --source roll-call --data "{\"student\":\"$NAME\",\"present\":true}" --json
```

### 2. Lecture question answering — spoken question to spoken answer

A student's spoken question is transcribed, answered by THINK with lecture
notes as context, and read back aloud.

```bash
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer'
opal say generate --voice-id <voice_id> --text <answer> \
```

### 3. Oral quiz — speak the question, hear and grade the answer

Say poses the question, the student's spoken answer is transcribed, and
THINK grades it against an expected answer.

```bash
opal say generate --voice-id <voice_id> \
opal think task create \
```

### 4. Whiteboard capture — photo of the board to lecture notes

Look grabs a frame or photo of the board, analyzes it for text and diagrams,
and THINK turns it into tidy notes.

```bash
opal look source frame "$CAMERA_ID" --output-file whiteboard.jpg
opal look analyze image --image whiteboard.jpg --pipeline-id "$OCR_PIPELINE" --json > board.json
OBS=$(jq -c '.observations' board.json)
TID=$(opal think task create \
  --prompt 'Turn this captured whiteboard content into concise lecture notes.' \
  --context "{\"observations\":$OBS}" --timeout-seconds 180 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > whiteboard-notes.txt
```

### 5. Absent-student recap — transcript to narrated summary

Transcribe a discussion segment, have THINK summarize the key points, and
generate a narrated recap file.

```bash
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > recap.txt
opal say generate --voice-id <voice_id> --text "$(cat recap.txt)" \
```

## 2. Reading and Literacy

### 6. Read a printed page aloud

Look extracts the page text and Say reads it — an instant accessibility
helper for print materials.

```bash
opal look analyze image --image page.jpg --pipeline-id "$OCR_PIPELINE" --json > page.json
TEXT=$(jq -r '.observations[0].text // .observations[0].label' page.json)
opal say generate --voice-id "$VOICE_ID" --text "$TEXT" \
  --output-format wav --output-file page-audio.wav
```

### 7. Reading practice feedback — expected text vs spoken words

The student reads a known passage aloud; the transcript is compared to the
expected text and THINK writes encouraging, specific feedback.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file reading.wav --json \
  | jq -r '.transcript')
TID=$(opal think task create \
  --prompt 'Compare the student reading to the expected passage. Give two kind, specific improvement tips.' \
  --context "{\"expected\":\"The cat sat on the mat.\",\"heard\":\"$TRANSCRIPT\"}" \
  --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer'
```

### 8. Pronunciation drill loop

Say speaks the target phrase, the student repeats it into a clip, and THINK
evaluates the match — repeatable in a small loop.

```bash
opal say generate --voice-id <voice_id> \
opal think task create \
```

### 9. Flashcard practice — card photo to spoken definition

Look reads a vocabulary card, THINK produces a short definition, Say
dictates word and definition for review.

```bash
opal look analyze image --image flashcard.jpg --pipeline-id <ocr_pipeline> --json > card.json
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer'
```

### 10. DIY audiobook — page photos to a narrated WAV

Scan page images through OCR, let THINK clean the text, and synthesize a
single narrated file.

```bash
opal look analyze image --image <f> --pipeline-id <ocr_pipeline> --json \
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > chapter.txt
```

## 3. Language Learning

### 11. Phrase rehearsal with progress log

Say the target phrase, transcribe the student's attempt, score it, and
publish a progress event for the learner's record.

```bash
opal say generate --voice-id "$VOICE_ID" --text 'Bonjour, comment allez-vous?' \
  --output-format wav --output-file phrase-target.wav
TRANSCRIPT=$(opal listen recognition test-audio --file phrase-attempt.wav --json \
  | jq -r '.transcript')
opal event event publish --topic language.practice \
  --source phrase-drill \
  --data "{\"target\":\"Bonjour, comment allez-vous?\",\"heard\":\"$TRANSCRIPT\"}" --json
```

### 12. Spoken translation check

The student speaks a translation; THINK compares it to the source sentence
and reports accuracy in English.

```bash
TRANSCRIPT=$(opal listen recognition test-audio --file translation.wav --json \
  | jq -r '.transcript')
opal think task create \
  --prompt 'Judge whether the spoken French correctly translates the English source. Reply in English.' \
  --context "{\"source_en\":\"Where is the library?\",\"student_fr\":\"$TRANSCRIPT\"}" \
  --timeout-seconds 120 --json
```

### 13. Picture vocabulary — see it, name it in the target language

Look identifies an object in a photo and THINK/Say teach the word in the
target language.

```bash
opal look analyze image --image object.jpg --pipeline-id PIPELINE_ID --json > obj.json
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > vocab.txt
```

### 14. Listening comprehension quiz

Say dictates a short passage, the student answers aloud, and THINK checks
comprehension against the passage.

```bash
opal say generate --voice-id <voice_id> \
opal think task create \
```

### 15. Conversation partner — spoken turn, spoken reply

A THINK session keeps the dialogue coherent: each spoken turn is
transcribed, answered in session, and spoken back.

```bash
CSID=$(opal think session add --title 'French conversation practice' --json | jq -er '.id')
TRANSCRIPT=$(opal listen recognition test-audio --file turn-1.wav --json | jq -r '.transcript')
TID=$(opal think task create --prompt "Reply in simple French to: $TRANSCRIPT" \
  --session-id "$CSID" --timeout-seconds 120 --json | jq -er '.id')
opal think task watch "$TID"
opal think task show "$TID" --json | jq -er '.answer' > reply.txt
opal say generate --voice-id "$VOICE_ID" --text "$(cat reply.txt)" \
  --output-format wav --output-file reply.wav
```

## 4. Field Learning and Research

### 16. Museum exhibit explainer

Photograph an exhibit or placard, have THINK explain it at a chosen reading
level, and play the audio.

```bash
opal look analyze image --image exhibit.jpg --pipeline-id <ocr_pipeline> --json > exhibit.json
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > exhibit-note.txt
```

### 17. Nature walk journal — photo to observation log

Photograph a plant or insect, analyze it, and publish a timestamped journal
entry on the event bus.

```bash
opal look analyze image --image specimen.jpg --pipeline-id PIPELINE_ID --json > find.json
OBS=$(jq -c '.observations' find.json)
opal event event publish --topic field.journal \
  --source nature-walk --data "{\"observations\":$OBS}" --json
opal event event list --topic field.journal --limit 20 --json
```

### 18. Science fair rubric scoring

Look reads a project poster and THINK scores it against a rubric, then the
score is published for review.

```bash
opal look analyze image --image poster.jpg --pipeline-id <ocr_pipeline> --json > poster.json
opal think task watch <tid>
opal think task show <tid> --json > score.json
```

### 19. Lab safety watch — missing gear to spoken alert

A Look rule watches for missing safety gear; matching observations publish
an event whose action can trigger a spoken reminder through Say.

```bash
opal look data observation list --source-id <camera_id> --label person \
opal event event publish --topic lab.safety --source lab-monitor \
opal say generate --voice-id <voice_id> \
```

### 20. Study group debrief — discussion to recap and action items

Transcribe a study-group segment, have THINK pull out key points and action
items, and narrate the recap.

```bash
opal think task watch <tid>
opal think task show <tid> --json | jq -er '.answer' > debrief.txt
opal say generate --voice-id <voice_id> --text "$(cat debrief.txt)" \
```

## Practical Notes

- **Chain with `jq`.** Recipe outputs are plain JSON; extract handoff fields
  (`transcript`, `.id`, `.answer`, `.observations`) explicitly rather than
  assuming field order.
- **Use `--json` on every producer step.** Diagnostics stay on stderr so
  pipes stay clean.
- **Wait between THINK turns.** `task watch` only observes — it does not
  block submission of the next task in a session unless you sequence it.
- **Replace IDs, not semantics.** Any pipeline, voice, model, or camera ID
  works as long as the deployment lists it; adapt the JSON contexts to your
  rubric, language, or curriculum.
- **Respect recognition limits.** Confidence is not a pronunciation score;
  review transcripts before grading decisions.
