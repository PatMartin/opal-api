# OPAL Cookbook

Fifty shell recipes for OPAL Listen, Say, Look, Event, and Think.
Markdown renderers such as GitHub provide a **Copy** control on every fenced
shell block. Replace capitalized IDs with values from your deployment. Add
`--url URL --token TOKEN` to any command when your CLI is not preconfigured.

Mutating configuration requires a current, quoted strong ETag:
`--if-match '"CURRENT_CONFIG_ETAG"'`. Do not use `*`.

## 1. Discover The Deployment

### 1. Check Listen health
```bash
opal listen health --json
```

### 2. Find audio devices
```bash
opal listen health audio-devices --json
```

### 3. Discover Look capabilities
```bash
opal look capabilities show --json
```

### 4. List speech engines
```bash
opal say engines list --json
```

### 5. List THINK models
```bash
opal think model list --json
```

## 2. Recognize Speech

### 6. Test a text command
```bash
opal listen recognition test-text --text 'hello opal' --save-log true --json
```

### 7. Transcribe a WAV file
```bash
opal listen recognition test-audio --file question.wav --save-log true --json
```

### 8. Require a wakeword
```bash
opal listen recognition test-audio --file command.wav --require-wakeword true --save-log true --json
```

### 9. Check live recognition
```bash
opal listen recognition status --json
```

### 10. Review matched logs
```bash
opal listen logs list --matched true --limit 25 --json
```

## 3. Build A Vocabulary

### 11. List intents
```bash
opal listen intents list --json
```

### 12. Add a greeting intent
```bash
opal listen intents add --name greeting --phrases '["hello opal","good morning"]' --enabled true --if-match '"CURRENT_CONFIG_ETAG"' --json
```

### 13. List an intent's phrases
```bash
opal listen phrases list INTENT_ID --json
```

### 14. Add a phrase
```bash
opal listen phrases add INTENT_ID --phrase 'start the daily briefing' --if-match '"CURRENT_CONFIG_ETAG"' --json
```

### 15. Run regression tests
```bash
opal listen regression run --enabled-only true --json
```

## 4. Generate Speech

### 16. List voices
```bash
opal say voices list --json
```

### 17. Validate a voice
```bash
opal say voices validate VOICE_ID --json
```

### 18. Create a WAV announcement
```bash
opal say generate --voice-id VOICE_ID --text 'Your OPAL services are ready.' --output-format wav --output-file announcement.wav
```

### 19. Tune voice pacing
```bash
opal say voices test VOICE_ID --text 'Testing a comfortable pace.' --speed 0.9 --volume 0.8 --output-format wav --output-file voice-test.wav
```

### 20. Play a PCM stream
```bash
opal say stream --voice-id VOICE_ID --text 'This is a live OPAL stream.' --sample-rate 22050 | aplay -f S16_LE -r 22050 -c 1
```

## 5. Inspect Visual Sources

### 21. List cameras and sources
```bash
opal look sources list --json
```

### 22. Probe a source
```bash
opal look sources probe CAMERA_ID --json
```

### 23. Save one camera frame
```bash
opal look sources frame CAMERA_ID --output-file camera-frame.jpg
```

### 24. Analyze a still image
```bash
opal look analyze image --image porch.jpg --pipeline-id PIPELINE_ID --persist-results true --json
```

### 25. Browse source observations
```bash
opal look observations list --source-id CAMERA_ID --limit 25 --json
```

## 6. Run Visual Work

### 26. Start a live session
```bash
opal look sessions start --source-id CAMERA_ID --pipeline-id PIPELINE_ID --auto-start true --json
```

### 27. Inspect a session
```bash
opal look sessions show SESSION_ID --json
```

### 28. List session observations
```bash
opal look sessions observations SESSION_ID --limit 50 --json
```

### 29. Submit a video job
```bash
opal look jobs submit --kind analyze_video --source-id CAMERA_ID --pipeline-id PIPELINE_ID --range '{"start_ms":0,"end_ms":30000}' --json
```

### 30. Stop a session
```bash
opal look sessions stop SESSION_ID --json
```

## 7. Automate With Events

### 31. Publish a sensor event
```bash
opal event events publish --topic sensor.greenhouse --source greenhouse-1 --data '{"temperature_c":31.4,"humidity_pct":42}' --json
```

### 32. Filter event history by topic
```bash
opal event events list --topic sensor.greenhouse --limit 20 --json
```

### 33. List automation rules
```bash
opal event rules list --json
```

### 34. Test a rule safely
```bash
opal event rules test RULE_ID --event '{"topic":"sensor.greenhouse","data":{"temperature_c":31.4}}' --json
```

### 35. Inspect action executions
```bash
opal event executions list --action-id ACTION_ID --limit 20 --json
```

## 8. Ask THINK

### 36. Submit an operational question
```bash
opal think task create --prompt 'Summarize current operational risks in one paragraph.' --timeout-seconds 120 --json
```

### 37. Include structured incident context
```bash
opal think task create --prompt 'Suggest two diagnostic checks.' --context '{"service":"listen","symptom":"microphone overflows increased"}' --timeout-seconds 120 --json
```

### 38. Watch a task
```bash
opal think task watch TASK_ID
```

### 39. Retrieve a result
```bash
opal think task show TASK_ID --json
```

### 40. Create a named conversation
```bash
opal think session add --title 'Greenhouse operations review' --json
```

## 9. Audit History And Evidence

### 41. Count recognition logs
```bash
opal listen logs count --json
```

### 42. Inspect latest recognition performance
```bash
opal listen performance last --json
```

### 43. Page performance history
```bash
opal listen performance history --limit 50 --json
```

### 44. List uploaded media
```bash
opal look media list --limit 25 --json
```

### 45. Download an artifact
```bash
opal look artifacts download ARTIFACT_ID --output-file artifact.bin
```

## 10. Safely Handle Configuration

### 46. Export Listen configuration
```bash
opal listen backup export --json > listen-config.json
```

### 47. Validate an export before import
```bash
opal listen backup validate --request @listen-config.json --json
```

### 48. Inspect a Say setting
```bash
opal say settings show SETTING_KEY --json
```

### 49. Export Look configuration
```bash
opal look configuration export --json > look-config.json
```

### 50. Inspect Event statistics
```bash
opal event stats show --json
```

## Practical Notes

- Use IDs from `list` and `show` responses, not display names.
- Keep `--if-match` quotes intact. Missing, stale, and malformed validators
  produce `428`, `412`, and `422`, respectively.
- Keep JSON output separate from diagnostics: use `--json`, redirect to a
  file, or process it with `jq`.
- Discover deployment-specific image labels, models, and options through
  `opal look capabilities show --json`; do not guess them.
- Run `opal SERVICE COMMAND --help` before composing a mutation.

For the complete generated-command reference, see [CLI.astra.md](CLI.astra.md).
