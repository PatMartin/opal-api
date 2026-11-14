# The OPAL CLI Cookbook

*Recipes for five services that can hear you, see your porch, think about it, gossip over an event bus, and announce the verdict out loud.*

This cookbook describes the unified `opal` [Typer](https://typer.tiangolo.com/) CLI implied by the v1.7.1 OpenAPI contracts in [`openapi/`](../openapi) and the shared kernel at [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml). Every command maps to exactly one REST operation in those contracts.

One honest caveat before the fun starts: this repository ships contracts, not an `opal` executable. Treat this as the menu for a restaurant whose kitchen is specified in great detail.

## Contents

- [Before you cook](#before-you-cook)
- [Part 1: Interface](#part-1-interface)
  - [opal-say](#opal-say) · [opal-listen](#opal-listen) · [opal-look](#opal-look) · [opal-think](#opal-think) · [opal-event](#opal-event)
- [Part 2: Usecases](#part-2-usecases)
  - [opal-say](#opal-say-usecases) · [opal-listen](#opal-listen-usecases) · [opal-look](#opal-look-usecases) · [opal-think](#opal-think-usecases) · [opal-event](#opal-event-usecases)
- [Part 3: Combined](#part-3-combined)
  - [Plumbing](#plumbing-do-this-once)
  - [Voice lab](#voice-lab) · [Eyes on the property](#eyes-on-the-property) · [The classroom](#the-classroom) · [Voice assistant](#voice-assistant) · [Home automation](#home-automation) · [Office and computer](#office-and-computer) · [Fleet operations](#fleet-operations)

## Before you cook

### How commands are named

The kernel's `x-opal-cli-format` extension defines the shape of every command:

```text
opal <service> [parent] [group] <command>
```

Look and Think annotate every operation with `x-opal-cli`, so their command names come straight from the contracts. Event, Listen, and Say annotate only their `config setting` and `service` commands. For the rest, this cookbook proposes names that follow the same kernel format and the Look/Think vocabulary (`list`, `add`, `show`, `update`, `remove`, plus explicit verbs for operations). Proposed names are marked with **†** in the command tables.

### How options are named

- Path parameters become positional arguments: `/voice/{voice_id}` becomes `<voice_id>`.
- Query parameters and JSON body fields become kebab-case options: `engine_voice_ref` becomes `--engine-voice-ref`.
- Booleans become flag pairs: `--enabled/--no-enabled`.
- Objects and arrays are passed as JSON: `--stages '[...]'`.
- A request's primary payload is positional: `<prompt>` on `task create` (and its `ask`/`chat` aliases), `<text>` on `say generate` and `say stream`.
- Request headers become options: `--if-match`, `--idempotency-key`, `--last-event-id`, `--range`.

### Client-side conveniences

These live in the CLI, not in the contracts. The recipes lean on them, so here they are in plain sight:

| Convenience | Behavior |
|---|---|
| `--if-match` is optional | Configuration mutations require a strong `If-Match` ETag. When you omit the option, the CLI reads the current ETag first and sends it for you. |
| `--out PATH` | Write a binary or JSON response body to a file. |
| `--play` | Play the audio returned by `opal say` on this machine's default output device. The Say API returns bytes only; playback is explicitly outside its contract. |
| `--wait` | After a `202 Accepted`, poll the resource until it reaches a terminal state, then print it. |
| `-` as a value | Read the value from standard input, for example `opal say generate -` or `--context -`. |
| `@path` as a value | Read the value from a file, for example `opal say generate @chapter-one.txt`. |
| `opal think ask` and `chat` | Aliases of `task create` that wait for the task and print only the final `answer`, which makes them easy to pipe. `chat` is `ask` bound to a session via `--session-id`. |
| Output | Commands print JSON on standard output unless the response is binary. |

### Assumptions in the examples

- **Addresses.** Event, Say, and Think all list `127.0.0.1:8080` as their example server; Look lists `127.0.0.1:8082` and Listen lists `localhost:8000`. Since three services cannot share one port, where a recipe needs one service to call another it assumes Event on `8080`, Say on `8081`, Look on `8082`, Think on `8083`, and Listen on `8000`. Adjust to your deployment.
- **Identifiers.** Voices (`en-gb-alan-low`), engines (`piper`), cameras (`cam-front`), models (`ollama:llama3.2`), and IDs such as `ses-42` or `tsk-123` are examples. Use the IDs your services return.
- **Shell.** Examples use POSIX quoting. In PowerShell, keep the single quotes around JSON and escape inner double quotes as your version requires.
- **Copy button.** Every snippet is a fenced code block, so GitHub and most Markdown viewers render a copy button in its top-right corner.

---

## Part 1: Interface

### opal-say

Text-to-speech over engines already installed on the host, such as Piper or Kokoro. Say registers and uses voices; it never downloads models and never plays audio itself.

#### Typer command tree

```text
opal say
├── generate
├── stream
├── engine                list | show | update | validate
├── config
│   ├── voice             list | add | show | update | remove | validate | test
│   ├── profile           list | add | show | update | remove | activate
│   ├── persona           list | add | validate | show | update | remove
│   └── setting           list | update | show | set | remove
├── info                  health | version | ping | live | ready
├── backup                list | create | download | restore | remove | export | import | validate-stored | validate
└── service               start | stop | log
```

#### REST tree

```text
/api/v1
├── /engine/                                GET
│   └── /{engine_id}                        GET, PATCH
│       └── /validate                       POST
├── /voice/                                 GET, POST
│   └── /{voice_id}                         GET, PATCH, DELETE
│       ├── /validate                       POST
│       └── /test                           POST
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /persona/                               GET, POST
│   └── /{persona_id}                       GET, PATCH, DELETE
│       └── /validate                       POST
├── /generate                               POST
│   └── /stream                             POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
├── /backup
│   ├── /list                               GET
│   ├── /create                             POST
│   ├── /download
│   │   └── /{filename}                     GET
│   ├── /restore
│   │   └── /{filename}                     POST
│   ├── /{filename}                         DELETE
│   ├── /export                             GET
│   ├── /import                             POST
│   └── /validate                           GET, POST
├── /info/                                  GET
│   └── /ping                               GET
└── /service
    ├── /start                              POST
    ├── /stop                               POST
    └── /log                                GET
```

#### Commands

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal say engine list` † | — | List engines. `GET /api/v1/engine/` |
| `opal say engine show` † | `<engine_id>` | Get engine. `GET /api/v1/engine/{engine_id}` |
| `opal say engine update` † | `<engine_id>`, `--if-match ETAG`, `--enabled/--no-enabled`, `--options JSON` | Update engine. `PATCH /api/v1/engine/{engine_id}` |
| `opal say engine validate` † | `<engine_id>` | Validate Engine. `POST /api/v1/engine/{engine_id}/validate` |
| `opal say config voice list` † | `--engine-id ID`, `--language TEXT`, `--enabled/--no-enabled` | List Voice. `GET /api/v1/voice/` |
| `opal say config voice add` † | `--if-match ETAG`, `--voice-id ID`, `--name TEXT`, `--description TEXT`, `--engine-id ID`, `--engine-voice-ref TEXT`, `--language TEXT`, `--enabled/--no-enabled`, `--engine-options JSON` | Register Voice. `POST /api/v1/voice/` |
| `opal say config voice show` † | `<voice_id>` | Get Voice. `GET /api/v1/voice/{voice_id}` |
| `opal say config voice update` † | `<voice_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--engine-id ID`, `--engine-voice-ref TEXT`, `--language TEXT`, `--enabled/--no-enabled`, `--engine-options JSON` | Update Voice. `PATCH /api/v1/voice/{voice_id}` |
| `opal say config voice remove` † | `<voice_id>`, `--if-match ETAG` | Unregister Voice. `DELETE /api/v1/voice/{voice_id}` |
| `opal say config voice validate` † | `<voice_id>` | Validate Voice. `POST /api/v1/voice/{voice_id}/validate` |
| `opal say config voice test` † | `<voice_id>`, `--text TEXT`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON`, `--out PATH`, `--play` | Test Voice. `POST /api/v1/voice/{voice_id}/test` |
| `opal say config profile list` † | — | List profiles. `GET /api/v1/profile/` |
| `opal say config profile add` † | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active`, `--voice-id ID`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON` | Create profile. `POST /api/v1/profile/` |
| `opal say config profile show` † | `<profile_id>` | Get profile. `GET /api/v1/profile/{profile_id}` |
| `opal say config profile update` † | `<profile_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active`, `--voice-id ID`, `--speed FLOAT`, `--volume FLOAT`, `--output-format [wav\|pcm]`, `--sample-rate INT`, `--engine-options JSON` | Update profile. `PATCH /api/v1/profile/{profile_id}` |
| `opal say config profile remove` † | `<profile_id>`, `--if-match ETAG` | Delete profile. `DELETE /api/v1/profile/{profile_id}` |
| `opal say config profile activate` † | `<profile_id>`, `--if-match ETAG` | Activate profile. `POST /api/v1/profile/{profile_id}/activate` |
| `opal say config persona list` † | `--enabled/--no-enabled` | List Personas. `GET /api/v1/persona/` |
| `opal say config persona add` † | `--if-match ETAG`, `--persona-id ID`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Create Persona. `POST /api/v1/persona/` |
| `opal say config persona validate` † | `<persona_id>` | Validate Persona. `POST /api/v1/persona/{persona_id}/validate` |
| `opal say config persona show` † | `<persona_id>` | Get Persona. `GET /api/v1/persona/{persona_id}` |
| `opal say config persona update` † | `<persona_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Update Persona. `PATCH /api/v1/persona/{persona_id}` |
| `opal say config persona remove` † | `<persona_id>`, `--if-match ETAG` | Delete Persona. `DELETE /api/v1/persona/{persona_id}` |
| `opal say generate` † | `<text>`, `--profile-id INT`, `--voice-id ID`, `--persona ID`, `--engine-id ID`, `--speed FLOAT`, `--volume FLOAT`, `--sample-rate INT`, `--engine-options JSON`, `--output-format [wav\|pcm]`, `--out PATH`, `--play` | Synthesize completed WAV or raw PCM audio from text. `POST /api/v1/generate` |
| `opal say stream` † | `<text>`, `--profile-id INT`, `--voice-id ID`, `--persona ID`, `--engine-id ID`, `--speed FLOAT`, `--volume FLOAT`, `--sample-rate INT`, `--engine-options JSON`, `--out PATH`, `--play` | Synthesize progressive raw `s16le` mono PCM from text. `POST /api/v1/generate/stream` |
| `opal say config setting list` | — | List settings. `GET /api/v1/setting/` |
| `opal say config setting update` | `--if-match ETAG`, `--data JSON` | Patch settings (alias: `opal say config setting patch`). `PATCH /api/v1/setting/` |
| `opal say config setting show` | `<key>` | Get setting (alias: `opal say setting get`). `GET /api/v1/setting/{key}` |
| `opal say config setting set` | `<key>`, `<value>`, `--if-match ETAG` | Set setting. `PUT /api/v1/setting/{key}` |
| `opal say config setting remove` | `<key>`, `--if-match ETAG` | Delete setting (alias: `opal say setting delete`). `DELETE /api/v1/setting/{key}` |
| `opal say info health` † | — | Service health report. `GET /api/v1/health/` |
| `opal say backup list` † | — | List backups. `GET /api/v1/backup/list` |
| `opal say backup create` † | — | Create backup. `POST /api/v1/backup/create` |
| `opal say backup download` † | `<filename>`, `--out PATH` | Download backup. `GET /api/v1/backup/download/{filename}` |
| `opal say backup restore` † | `<filename>`, `--if-match ETAG` | Restore backup. `POST /api/v1/backup/restore/{filename}` |
| `opal say backup remove` † | `<filename>` | Delete backup. `DELETE /api/v1/backup/{filename}` |
| `opal say backup export` † | `--out PATH` | Export configuration. `GET /api/v1/backup/export` |
| `opal say backup import` † | `--if-match ETAG`, `--file PATH` | Import configuration. `POST /api/v1/backup/import` |
| `opal say backup validate-stored` † | — | Validate stored configuration. `GET /api/v1/backup/validate` |
| `opal say backup validate` † | `--file PATH` | Validate configuration. `POST /api/v1/backup/validate` |
| `opal say info version` † | — | Service Info. `GET /api/v1/info/` |
| `opal say info ping` † | — | Ping. `GET /api/v1/info/ping` |
| `opal say info live` † | — | Liveness probe. `GET /api/v1/health/live` |
| `opal say info ready` † | — | Readiness probe. `GET /api/v1/health/ready` |
| `opal say service start` | `--append/--no-append` | Start service. `POST /api/v1/service/start` |
| `opal say service stop` | — | Stop service. `POST /api/v1/service/stop` |
| `opal say service log` | `--lines INT` | Tail service log. `GET /api/v1/service/log` |

† Proposed name; the operation has no `x-opal-cli` annotation yet.

### opal-listen

Wakewords, speech-to-text, intent recognition, and slot extraction, plus a regression harness for people tired of saying "turn on the kitchen lights" at 2 AM.

#### Typer command tree

```text
opal listen
├── config
│   ├── wakeword          list | add | show | update | remove
│   ├── intent            list | add | show | update | remove
│   ├── phrase            list | add | remove
│   ├── slot              list | add | show | update | remove
│   ├── slot-value        list | add | remove
│   ├── slot-alias        list | add | remove
│   ├── profile           list | add | show | update | remove | activate
│   ├── setting           list | update | show | set | remove
│   └── persona           list | add | validate | show | update | remove
├── recognition           test-text | test-audio | start | stop | status | stream
├── data
│   └── failed-utterance  list | add | show | update | remove | promote
├── regression            list | add | run | show | update | remove
├── performance           last | summary | history
├── info                  health | audio-devices | version | ping | live | ready
├── backup                list | create | download | restore | remove | export | import | validate-stored | validate
└── service               start | stop | log
```

#### REST tree

```text
/api/v1
├── /wakeword/                              GET, POST
│   └── /{wakeword_id}                      GET, PATCH, DELETE
├── /intent/                                GET, POST
│   └── /{intent_id}                        GET, PATCH, DELETE
│       └── /phrase                         GET, POST
│           └── /{phrase_id}                DELETE
├── /slot/                                  GET, POST
│   └── /{slot_id}                          GET, PATCH, DELETE
│       └── /value                          GET, POST
│           └── /{value_id}                 DELETE
│               └── /alias                  GET, POST
│                   └── /{alias_id}         DELETE
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /recognition
│   ├── /test_text                          POST
│   ├── /test_audio                         POST
│   ├── /start                              POST
│   ├── /stop                               POST
│   ├── /status                             GET
│   └── /stream                             GET
├── /failed_utterance/                      GET, POST
│   └── /{fu_id}                            GET, PATCH, DELETE
│       └── /promote                        POST
├── /regression/                            GET, POST
│   ├── /run                                POST
│   └── /{test_id}                          GET, PATCH, DELETE
├── /performance
│   ├── /last                               GET
│   ├── /summary                            GET
│   └── /history                            GET
├── /health/                                GET
│   ├── /audio_devices                      GET
│   ├── /live                               GET
│   └── /ready                              GET
├── /info/                                  GET
│   └── /ping                               GET
├── /backup
│   ├── /list                               GET
│   ├── /create                             POST
│   ├── /download
│   │   └── /{filename}                     GET
│   ├── /restore
│   │   └── /{filename}                     POST
│   ├── /{filename}                         DELETE
│   ├── /export                             GET
│   ├── /import                             POST
│   └── /validate                           GET, POST
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
└── /persona/                               GET, POST
    └── /{persona_id}                       GET, PATCH, DELETE
        └── /validate                       POST
```

#### Commands

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal listen config wakeword list` † | — | List Wakewords. `GET /api/v1/wakeword/` |
| `opal listen config wakeword add` † | `--if-match ETAG`, `--name TEXT`, `--enabled/--no-enabled`, `--confidence-threshold FLOAT` | Create Wakeword. `POST /api/v1/wakeword/` |
| `opal listen config wakeword show` † | `<wakeword_id>` | Get Wakeword. `GET /api/v1/wakeword/{wakeword_id}` |
| `opal listen config wakeword update` † | `<wakeword_id>`, `--if-match ETAG`, `--name TEXT`, `--enabled/--no-enabled`, `--confidence-threshold FLOAT` | Update Wakeword. `PATCH /api/v1/wakeword/{wakeword_id}` |
| `opal listen config wakeword remove` † | `<wakeword_id>`, `--if-match ETAG` | Delete Wakeword. `DELETE /api/v1/wakeword/{wakeword_id}` |
| `opal listen config intent list` † | — | List Intents. `GET /api/v1/intent/` |
| `opal listen config intent add` † | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--enabled/--no-enabled`, `--confidence-threshold FLOAT`, `--phrases JSON` | Create Intent. `POST /api/v1/intent/` |
| `opal listen config intent show` † | `<intent_id>` | Get Intent. `GET /api/v1/intent/{intent_id}` |
| `opal listen config intent update` † | `<intent_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--enabled/--no-enabled`, `--confidence-threshold FLOAT` | Update Intent. `PATCH /api/v1/intent/{intent_id}` |
| `opal listen config intent remove` † | `<intent_id>`, `--if-match ETAG` | Delete Intent. `DELETE /api/v1/intent/{intent_id}` |
| `opal listen config phrase list` † | `<intent_id>` | List Phrases. `GET /api/v1/intent/{intent_id}/phrase` |
| `opal listen config phrase add` † | `<intent_id>`, `--if-match ETAG`, `--phrase TEXT` | Add Phrase. `POST /api/v1/intent/{intent_id}/phrase` |
| `opal listen config phrase remove` † | `<intent_id>`, `<phrase_id>`, `--if-match ETAG` | Delete Phrase. `DELETE /api/v1/intent/{intent_id}/phrase/{phrase_id}` |
| `opal listen config slot list` † | — | List Slots. `GET /api/v1/slot/` |
| `opal listen config slot add` † | `--if-match ETAG`, `--name TEXT`, `--slot-type TEXT`, `--description TEXT` | Create Slot. `POST /api/v1/slot/` |
| `opal listen config slot show` † | `<slot_id>` | Get Slot. `GET /api/v1/slot/{slot_id}` |
| `opal listen config slot update` † | `<slot_id>`, `--if-match ETAG`, `--name TEXT`, `--slot-type TEXT`, `--description TEXT` | Update Slot. `PATCH /api/v1/slot/{slot_id}` |
| `opal listen config slot remove` † | `<slot_id>`, `--if-match ETAG` | Delete Slot. `DELETE /api/v1/slot/{slot_id}` |
| `opal listen config slot-value list` † | `<slot_id>` | List Slot Values. `GET /api/v1/slot/{slot_id}/value` |
| `opal listen config slot-value add` † | `<slot_id>`, `--if-match ETAG`, `--value TEXT` | Add Slot Value. `POST /api/v1/slot/{slot_id}/value` |
| `opal listen config slot-value remove` † | `<slot_id>`, `<value_id>`, `--if-match ETAG` | Delete Slot Value. `DELETE /api/v1/slot/{slot_id}/value/{value_id}` |
| `opal listen config slot-alias list` † | `<slot_id>`, `<value_id>` | List Aliases. `GET /api/v1/slot/{slot_id}/value/{value_id}/alias` |
| `opal listen config slot-alias add` † | `<slot_id>`, `<value_id>`, `--if-match ETAG`, `--alias TEXT` | Add Alias. `POST /api/v1/slot/{slot_id}/value/{value_id}/alias` |
| `opal listen config slot-alias remove` † | `<slot_id>`, `<value_id>`, `<alias_id>`, `--if-match ETAG` | Delete Alias. `DELETE /api/v1/slot/{slot_id}/value/{value_id}/alias/{alias_id}` |
| `opal listen config profile list` † | — | List profiles. `GET /api/v1/profile/` |
| `opal listen config profile add` † | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active`, `--wakeword-names JSON`, `--confidence-thresholds JSON`, `--vad-settings JSON`, `--enabled-intents JSON`, `--enabled-slots JSON`, `--model-paths JSON` | Create profile. `POST /api/v1/profile/` |
| `opal listen config profile show` † | `<profile_id>` | Get profile. `GET /api/v1/profile/{profile_id}` |
| `opal listen config profile update` † | `<profile_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active`, `--wakeword-names JSON`, `--confidence-thresholds JSON`, `--vad-settings JSON`, `--enabled-intents JSON`, `--enabled-slots JSON`, `--model-paths JSON` | Update profile. `PATCH /api/v1/profile/{profile_id}` |
| `opal listen config profile remove` † | `<profile_id>`, `--if-match ETAG` | Delete profile. `DELETE /api/v1/profile/{profile_id}` |
| `opal listen config profile activate` † | `<profile_id>`, `--if-match ETAG` | Activate profile. `POST /api/v1/profile/{profile_id}/activate` |
| `opal listen config setting list` | — | List settings. `GET /api/v1/setting/` |
| `opal listen config setting update` | `--if-match ETAG`, `--data JSON` | Patch settings (alias: `opal listen config setting patch`). `PATCH /api/v1/setting/` |
| `opal listen config setting show` | `<key>` | Get setting (alias: `opal listen setting get`). `GET /api/v1/setting/{key}` |
| `opal listen config setting set` | `<key>`, `<value>`, `--if-match ETAG` | Set setting. `PUT /api/v1/setting/{key}` |
| `opal listen config setting remove` | `<key>`, `--if-match ETAG` | Delete setting (alias: `opal listen setting unset`). `DELETE /api/v1/setting/{key}` |
| `opal listen recognition test-text` † | `--save-log/--no-save-log`, `--text TEXT` | Run text through intent matching and slot extraction (never published). `POST /api/v1/recognition/test_text` |
| `opal listen recognition test-audio` † | `<file>`, `--save-log/--no-save-log`, `--require-wakeword/--no-require-wakeword` | Run an audio file through wakeword, STT and intent matching (never published). `POST /api/v1/recognition/test_audio` |
| `opal listen recognition start` † | — | Start the live microphone pipeline. `POST /api/v1/recognition/start` |
| `opal listen recognition stop` † | — | Stop the live microphone pipeline. `POST /api/v1/recognition/stop` |
| `opal listen recognition status` † | — | Show live pipeline state and metrics. `GET /api/v1/recognition/status` |
| `opal listen recognition stream` † | `--debug/--no-debug` | Stream live recognition results (SSE, live-only). `GET /api/v1/recognition/stream` |
| `opal listen data failed-utterance list` † | `--reviewed/--no-reviewed`, `--promoted/--no-promoted`, `--limit INT`, `--offset INT` | List Failed Utterances. `GET /api/v1/failed_utterance/` |
| `opal listen data failed-utterance add` † | `--transcript TEXT`, `--expected-intent TEXT`, `--notes TEXT`, `--recognition-log-id INT` | Create Failed Utterance. `POST /api/v1/failed_utterance/` |
| `opal listen data failed-utterance show` † | `<fu_id>` | Get Failed Utterance. `GET /api/v1/failed_utterance/{fu_id}` |
| `opal listen data failed-utterance update` † | `<fu_id>`, `--expected-intent TEXT`, `--notes TEXT`, `--reviewed/--no-reviewed`, `--promoted-to-phrase/--no-promoted-to-phrase` | Update Failed Utterance. `PATCH /api/v1/failed_utterance/{fu_id}` |
| `opal listen data failed-utterance remove` † | `<fu_id>` | Delete Failed Utterance. `DELETE /api/v1/failed_utterance/{fu_id}` |
| `opal listen data failed-utterance promote` † | `<fu_id>`, `--intent-name TEXT`, `--create-regression/--no-create-regression`, `--if-match ETAG` | Promote To Phrase. `POST /api/v1/failed_utterance/{fu_id}/promote` |
| `opal listen regression list` † | — | List Regression Tests. `GET /api/v1/regression/` |
| `opal listen regression add` † | `--if-match ETAG`, `--name TEXT`, `--phrase TEXT`, `--expected-intent TEXT`, `--enabled/--no-enabled`, `--expected-slots JSON` | Create Regression Test. `POST /api/v1/regression/` |
| `opal listen regression run` † | `--enabled-only/--no-enabled-only` | Run Regression Tests. `POST /api/v1/regression/run` |
| `opal listen regression show` † | `<test_id>` | Get Regression Test. `GET /api/v1/regression/{test_id}` |
| `opal listen regression update` † | `<test_id>`, `--if-match ETAG`, `--name TEXT`, `--phrase TEXT`, `--expected-intent TEXT`, `--expected-slots JSON`, `--enabled/--no-enabled` | Update Regression Test. `PATCH /api/v1/regression/{test_id}` |
| `opal listen regression remove` † | `<test_id>`, `--if-match ETAG` | Delete Regression Test. `DELETE /api/v1/regression/{test_id}` |
| `opal listen performance last` † | — | Get Last Performance. `GET /api/v1/performance/last` |
| `opal listen performance summary` † | `--limit INT` | Get Performance Summary. `GET /api/v1/performance/summary` |
| `opal listen performance history` † | `--limit INT` | Get Performance History. `GET /api/v1/performance/history` |
| `opal listen info health` † | — | Service health report. `GET /api/v1/health/` |
| `opal listen info audio-devices` † | — | List host audio input devices. `GET /api/v1/health/audio_devices` |
| `opal listen info version` † | — | Service Info. `GET /api/v1/info/` |
| `opal listen info ping` † | — | Ping. `GET /api/v1/info/ping` |
| `opal listen info live` † | — | Liveness probe. `GET /api/v1/health/live` |
| `opal listen info ready` † | — | Readiness probe. `GET /api/v1/health/ready` |
| `opal listen backup list` † | — | List backups. `GET /api/v1/backup/list` |
| `opal listen backup create` † | — | Create backup. `POST /api/v1/backup/create` |
| `opal listen backup download` † | `<filename>`, `--out PATH` | Download backup. `GET /api/v1/backup/download/{filename}` |
| `opal listen backup restore` † | `<filename>`, `--if-match ETAG` | Restore backup. `POST /api/v1/backup/restore/{filename}` |
| `opal listen backup remove` † | `<filename>` | Delete backup. `DELETE /api/v1/backup/{filename}` |
| `opal listen backup export` † | `--out PATH` | Export configuration. `GET /api/v1/backup/export` |
| `opal listen backup import` † | `--if-match ETAG`, `--file PATH` | Import configuration. `POST /api/v1/backup/import` |
| `opal listen backup validate-stored` † | — | Validate stored configuration. `GET /api/v1/backup/validate` |
| `opal listen backup validate` † | `--file PATH` | Validate configuration. `POST /api/v1/backup/validate` |
| `opal listen service start` | `--append/--no-append` | Start service. `POST /api/v1/service/start` |
| `opal listen service stop` | — | Stop service. `POST /api/v1/service/stop` |
| `opal listen service log` | `--lines INT` | Tail service log. `GET /api/v1/service/log` |
| `opal listen config persona list` † | `--enabled/--no-enabled` | List Personas. `GET /api/v1/persona/` |
| `opal listen config persona add` † | `--if-match ETAG`, `--persona-id ID`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Create Persona. `POST /api/v1/persona/` |
| `opal listen config persona validate` † | `<persona_id>` | Validate Persona. `POST /api/v1/persona/{persona_id}/validate` |
| `opal listen config persona show` † | `<persona_id>` | Get Persona. `GET /api/v1/persona/{persona_id}` |
| `opal listen config persona update` † | `<persona_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Update Persona. `PATCH /api/v1/persona/{persona_id}` |
| `opal listen config persona remove` † | `<persona_id>`, `--if-match ETAG` | Delete Persona. `DELETE /api/v1/persona/{persona_id}` |

† Proposed name; the operation has no `x-opal-cli` annotation yet.

### opal-look

Visual observation: optional engine discovery, engine-owned models, single-image prediction, compute hardware, and ephemeral RTSP streams with SSE metadata, MJPEG video, JPEG snapshots, and per-stream metrics. Video-only streams run with zero installed engines; detection streams and `predict` always select an engine and model explicitly. Stream source credentials are redacted from every response, event, log, and error.

#### Typer command tree

```text
opal look
├── info                  version | ping | health | live | ready
├── engine                list | show | discover | capabilities
├── model                 list | show | load | unload
├── predict               image
├── hardware              list | show
├── stream                start | list | show | stop | watch | watch-video | snapshot | metrics
├── config
│   ├── engine            update
│   ├── profile           list | add | show | update | remove | activate
│   └── setting           list | update | show | set | remove
├── backup                list | create | download | restore | remove | export | import | validate
└── service               start | stop | log
```

#### REST tree

```text
/api/v1
├── /engine/                                GET
│   ├── /discover                           POST
│   └── /{engine_id}                        GET, PATCH
│       └── /capabilities                   GET
├── /model/                                 GET
│   └── /{model_id}                         GET
│       ├── /load                           POST
│       └── /unload                         POST
├── /predict                                POST
├── /hardware/                              GET
│   └── /{device_id}                        GET
├── /stream/                                GET, POST
│   └── /{stream_id}                        GET
│       ├── /stop                           POST
│       ├── /events                         GET (SSE)
│       ├── /video                          GET (MJPEG)
│       ├── /snapshot                       GET
│       └── /metrics                        GET
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /backup
│   ├── /list                               GET
│   ├── /create                             POST
│   ├── /download
│   │   └── /{filename}                     GET
│   ├── /restore
│   │   └── /{filename}                     POST
│   ├── /{filename}                         DELETE
│   ├── /export                             GET
│   ├── /import                             POST
│   └── /validate                           POST
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
├── /info/                                  GET
│   └── /ping                               GET
└── /service
    ├── /start                              POST
    ├── /stop                               POST
    └── /log                                GET
```

#### Commands

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal look engine list` | — | List discovered engines. `GET /api/v1/engine/` |
| `opal look engine show` | `<engine_id>` | Get engine. `GET /api/v1/engine/{engine_id}` |
| `opal look engine discover` | — | Trigger engine discovery. `POST /api/v1/engine/discover` |
| `opal look engine capabilities` | `<engine_id>` | Inspect engine capabilities and accepted options. `GET /api/v1/engine/{engine_id}/capabilities` |
| `opal look config engine update` | `<engine_id>`, `--if-match ETAG`, `--enabled/--no-enabled`, `--options JSON` | Update engine. `PATCH /api/v1/engine/{engine_id}` |
| `opal look model list` | `--engine-id ID` | List engine-owned models. `GET /api/v1/model/` |
| `opal look model show` | `<model_id>` | Get model. `GET /api/v1/model/{model_id}` |
| `opal look model load` | `<model_id>` | Load a model into its engine. `POST /api/v1/model/{model_id}/load` |
| `opal look model unload` | `<model_id>` | Unload a model from its engine. `POST /api/v1/model/{model_id}/unload` |
| `opal look predict image` | `--engine-id ID`, `--model-id ID`, `--source PATH`, `--confidence FLOAT`, `--device-id ID`, `--engine-options JSON`, `--include-native/--no-include-native` | Detect objects in a single image. `POST /api/v1/predict` |
| `opal look hardware list` | — | List compute devices. `GET /api/v1/hardware/` |
| `opal look hardware show` | `<device_id>` | Get device details. `GET /api/v1/hardware/{device_id}` |
| `opal look stream start` | `--source URI`, `--engine-id ID`, `--model-id ID`, `--confidence FLOAT`, `--device-id ID`, `--engine-options JSON`, `--annotate/--no-annotate`, `--buffer-policy [drop_oldest|drop_newest|block]`, `--buffer-size INT`, `--idempotency-key KEY` | Start a video or detection stream (202). `POST /api/v1/stream/` |
| `opal look stream list` | — | List streams. `GET /api/v1/stream/` |
| `opal look stream show` | `<stream_id>` | Get stream status with a redacted source. `GET /api/v1/stream/{stream_id}` |
| `opal look stream stop` | `<stream_id>` | Stop a stream and release its resources. `POST /api/v1/stream/{stream_id}/stop` |
| `opal look stream watch` | `<stream_id>` | Follow stream metadata and detection events over SSE. `GET /api/v1/stream/{stream_id}/events` |
| `opal look stream watch-video` | `<stream_id>`, `--annotated/--no-annotated`, `--out PATH` | Watch the live MJPEG feed. `GET /api/v1/stream/{stream_id}/video` |
| `opal look stream snapshot` | `<stream_id>`, `--annotated/--no-annotated`, `--out PATH` | Capture the current frame as JPEG. `GET /api/v1/stream/{stream_id}/snapshot` |
| `opal look stream metrics` | `<stream_id>` | Per-stream counters and latency. `GET /api/v1/stream/{stream_id}/metrics` |
| `opal look config setting list` | — | List settings. `GET /api/v1/setting/` |
| `opal look config setting update` | `--if-match ETAG`, `--data JSON` | Patch settings. `PATCH /api/v1/setting/` |
| `opal look config setting show` | `<key>` | Get setting. `GET /api/v1/setting/{key}` |
| `opal look config setting set` | `<key>`, `<value>`, `--if-match ETAG` | Set setting. `PUT /api/v1/setting/{key}` |
| `opal look config setting remove` | `<key>`, `--if-match ETAG` | Delete setting. `DELETE /api/v1/setting/{key}` |
| `opal look config profile list` | — | List profiles. `GET /api/v1/profile/` |
| `opal look config profile add` | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Create profile. `POST /api/v1/profile/` |
| `opal look config profile show` | `<profile_id>` | Get profile. `GET /api/v1/profile/{profile_id}` |
| `opal look config profile update` | `<profile_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Update profile. `PATCH /api/v1/profile/{profile_id}` |
| `opal look config profile remove` | `<profile_id>`, `--if-match ETAG` | Delete profile. `DELETE /api/v1/profile/{profile_id}` |
| `opal look config profile activate` | `<profile_id>`, `--if-match ETAG` | Activate profile. `POST /api/v1/profile/{profile_id}/activate` |
| `opal look backup list` | — | List backups. `GET /api/v1/backup/list` |
| `opal look backup create` | — | Create backup. `POST /api/v1/backup/create` |
| `opal look backup download` | `<filename>`, `--out PATH` | Download backup. `GET /api/v1/backup/download/{filename}` |
| `opal look backup restore` | `<filename>`, `--if-match ETAG` | Restore backup. `POST /api/v1/backup/restore/{filename}` |
| `opal look backup remove` | `<filename>` | Delete backup. `DELETE /api/v1/backup/{filename}` |
| `opal look backup export` | `--out PATH` | Export configuration. `GET /api/v1/backup/export` |
| `opal look backup import` | `--if-match ETAG`, `--file PATH` | Import configuration. `POST /api/v1/backup/import` |
| `opal look backup validate` | `--file PATH` | Validate configuration. `POST /api/v1/backup/validate` |
| `opal look info version` | — | Service Info. `GET /api/v1/info/` |
| `opal look info ping` | — | Ping. `GET /api/v1/info/ping` |
| `opal look info health` | — | Service health report. `GET /api/v1/health/` |
| `opal look info live` | — | Liveness probe. `GET /api/v1/health/live` |
| `opal look info ready` | — | Readiness probe. `GET /api/v1/health/ready` |
| `opal look service start` | `--append/--no-append` | Start service. `POST /api/v1/service/start` |
| `opal look service stop` | — | Stop service. `POST /api/v1/service/stop` |
| `opal look service log` | `--lines INT` | Tail service log. `GET /api/v1/service/log` |

### opal-think

Bounded reasoning tasks over configured models. Think can discover and execute actions registered in Event, but it cannot administer them.

#### Typer command tree

```text
opal think
├── ask                   alias of `task create`
├── chat                  alias of `task create`
├── task                  list | create | show | watch | cancel
├── session               list | add | show | remove
├── model                 list | show
├── config
│   ├── profile           list | add | show | update | remove | activate
│   ├── setting           list | update | show | set | remove
│   └── persona           list | add | validate | show | update | remove
├── info                  health | version | ping | live | ready
├── backup                list | create | download | restore | remove | export | import | validate
└── service               start | stop | log
```

#### REST tree

```text
/api/v1
├── /task/                                  GET, POST
│   └── /{task_id}                          GET
│       ├── /stream                         GET
│       └── /cancel                         POST
├── /session/                               GET, POST
│   └── /{session_id}                       GET, DELETE
├── /model/                                 GET
│   └── /{model_id}                         GET
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
├── /info/                                  GET
│   └── /ping                               GET
├── /backup
│   ├── /list                               GET
│   ├── /create                             POST
│   ├── /download
│   │   └── /{filename}                     GET
│   ├── /restore
│   │   └── /{filename}                     POST
│   ├── /{filename}                         DELETE
│   ├── /export                             GET
│   ├── /import                             POST
│   └── /validate                           POST
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
└── /persona/                               GET, POST
    └── /{persona_id}                       GET, PATCH, DELETE
        └── /validate                       POST
```

#### Commands

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal think task list` | `--status [queued\|running\|completed\|failed\|cancelled\|timed_out]`, `--session-id ID`, `--limit INT` | List retained tasks. `GET /api/v1/task/` |
| `opal think task create` | `<prompt>`, `--idempotency-key KEY`, `--session-id ID`, `--model-id ID`, `--context JSON`, `--max-steps INT`, `--timeout-seconds INT`, `--metadata JSON`, `--wait` | Create task (alias: `opal think ask`, `opal think chat`). `POST /api/v1/task/` |
| `opal think task show` | `<task_id>` | Show task. `GET /api/v1/task/{task_id}` |
| `opal think task watch` | `<task_id>` | Watch task output and progress. `GET /api/v1/task/{task_id}/stream` |
| `opal think task cancel` | `<task_id>` | Request task cancellation. `POST /api/v1/task/{task_id}/cancel` |
| `opal think session list` | `--limit INT` | List sessions. `GET /api/v1/session/` |
| `opal think session add` | `--title TEXT` | Add session. `POST /api/v1/session/` |
| `opal think session show` | `<session_id>` | Show session. `GET /api/v1/session/{session_id}` |
| `opal think session remove` | `<session_id>` | Remove session. `DELETE /api/v1/session/{session_id}` |
| `opal think model list` | — | List available and known models. `GET /api/v1/model/` |
| `opal think model show` | `<model_id>` | Show model. `GET /api/v1/model/{model_id}` |
| `opal think config profile list` | — | List profiles. `GET /api/v1/profile/` |
| `opal think config profile add` | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Create profile. `POST /api/v1/profile/` |
| `opal think config profile show` | `<profile_id>` | Get profile. `GET /api/v1/profile/{profile_id}` |
| `opal think config profile update` | `<profile_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Update profile. `PATCH /api/v1/profile/{profile_id}` |
| `opal think config profile remove` | `<profile_id>`, `--if-match ETAG` | Delete profile. `DELETE /api/v1/profile/{profile_id}` |
| `opal think config profile activate` | `<profile_id>`, `--if-match ETAG` | Activate profile. `POST /api/v1/profile/{profile_id}/activate` |
| `opal think config setting list` | — | List settings. `GET /api/v1/setting/` |
| `opal think config setting update` | `--if-match ETAG`, `--data JSON` | Patch settings (alias: `opal think setting patch`). `PATCH /api/v1/setting/` |
| `opal think config setting show` | `<key>` | Get setting. `GET /api/v1/setting/{key}` |
| `opal think config setting set` | `<key>`, `<value>`, `--if-match ETAG` | Set setting. `PUT /api/v1/setting/{key}` |
| `opal think config setting remove` | `<key>`, `--if-match ETAG` | Delete setting. `DELETE /api/v1/setting/{key}` |
| `opal think info health` | — | Service health report. `GET /api/v1/health/` |
| `opal think info version` | — | Service Info. `GET /api/v1/info/` |
| `opal think info ping` | — | Ping. `GET /api/v1/info/ping` |
| `opal think info live` | — | Liveness probe. `GET /api/v1/health/live` |
| `opal think info ready` | — | Readiness probe. `GET /api/v1/health/ready` |
| `opal think backup list` | — | List backups. `GET /api/v1/backup/list` |
| `opal think backup create` | — | Create backup. `POST /api/v1/backup/create` |
| `opal think backup download` | `<filename>`, `--out PATH` | Download backup. `GET /api/v1/backup/download/{filename}` |
| `opal think backup restore` | `<filename>`, `--if-match ETAG` | Restore backup. `POST /api/v1/backup/restore/{filename}` |
| `opal think backup remove` | `<filename>` | Delete backup. `DELETE /api/v1/backup/{filename}` |
| `opal think backup export` | `--out PATH` | Export configuration. `GET /api/v1/backup/export` |
| `opal think backup import` | `--if-match ETAG`, `--file PATH` | Import configuration. `POST /api/v1/backup/import` |
| `opal think backup validate` | `--file PATH` | Validate configuration. `POST /api/v1/backup/validate` |
| `opal think service start` | `--append/--no-append` | Start service. `POST /api/v1/service/start` |
| `opal think service stop` | — | Stop service. `POST /api/v1/service/stop` |
| `opal think service log` | `--lines INT` | Tail service log. `GET /api/v1/service/log` |
| `opal think config persona list` | `--enabled/--no-enabled` | List Personas. `GET /api/v1/persona/` |
| `opal think config persona add` | `--if-match ETAG`, `--persona-id ID`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Create Persona. `POST /api/v1/persona/` |
| `opal think config persona validate` | `<persona_id>` | Validate Persona. `POST /api/v1/persona/{persona_id}/validate` |
| `opal think config persona show` | `<persona_id>` | Get Persona. `GET /api/v1/persona/{persona_id}` |
| `opal think config persona update` | `<persona_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Update Persona. `PATCH /api/v1/persona/{persona_id}` |
| `opal think config persona remove` | `<persona_id>`, `--if-match ETAG` | Delete Persona. `DELETE /api/v1/persona/{persona_id}` |

### opal-event

Event publication, rule routing, and registered shell, HTTP, and Python actions. A `202` here means "admitted", never "delivered"; the bus is best effort and proud of it.

#### Typer command tree

```text
opal event
├── publish
├── data
│   ├── event             list | clear | show | remove
│   ├── topic             list
│   └── execution         list | show
├── config
│   ├── rule              list | add | show | update | remove | test
│   ├── action            list | add | show | update | remove | execute
│   ├── profile           list | add | show | update | remove | activate
│   ├── setting           list | update | show | set | remove
│   └── persona           list | add | validate | show | update | remove
├── info                  health | stats | version | ping | live | ready
├── backup                list | create | download | restore | remove | export | import | validate
└── service               start | stop | log
```

#### REST tree

```text
/api/v1
├── /event/                                 GET, POST, DELETE
│   └── /{event_id}                         GET, DELETE
├── /topic/                                 GET
├── /rule/                                  GET, POST
│   └── /{rule_id}                          GET, PATCH, DELETE
│       └── /test                           POST
├── /action/                                GET, POST
│   └── /{action_id}                        GET, PATCH, DELETE
│       └── /execute                        POST
├── /execution/                             GET
│   └── /{execution_id}                     GET
├── /health/                                GET
│   ├── /live                               GET
│   └── /ready                              GET
├── /stats/                                 GET
├── /profile/                               GET, POST
│   └── /{profile_id}                       GET, PATCH, DELETE
│       └── /activate                       POST
├── /setting/                               GET, PATCH
│   └── /{key}                              GET, PUT, DELETE
├── /info/                                  GET
│   └── /ping                               GET
├── /backup
│   ├── /list                               GET
│   ├── /create                             POST
│   ├── /download
│   │   └── /{filename}                     GET
│   ├── /restore
│   │   └── /{filename}                     POST
│   ├── /{filename}                         DELETE
│   ├── /export                             GET
│   ├── /import                             POST
│   └── /validate                           POST
├── /service
│   ├── /start                              POST
│   ├── /stop                               POST
│   └── /log                                GET
└── /persona/                               GET, POST
    └── /{persona_id}                       GET, PATCH, DELETE
        └── /validate                       POST
```

#### Commands

| COMMAND | OPTIONS | DESCRIPTION |
|---|---|---|
| `opal event data event list` † | `--limit INT`, `--topic TEXT`, `--source TEXT`, `--from ISO`, `--to ISO` | List stored events. `GET /api/v1/event/` |
| `opal event publish` † | `--id ID`, `--topic TEXT`, `--source TEXT`, `--timestamp ISO`, `--data JSON` | Publish an event (202 means admitted, not delivered). `POST /api/v1/event/` |
| `opal event data event clear` † | — | Clear all stored events. `DELETE /api/v1/event/` |
| `opal event data event show` † | `<event_id>` | Get stored event. `GET /api/v1/event/{event_id}` |
| `opal event data event remove` † | `<event_id>` | Delete stored event. `DELETE /api/v1/event/{event_id}` |
| `opal event data topic list` † | — | List observed topics. `GET /api/v1/topic/` |
| `opal event config rule list` † | — | List rules. `GET /api/v1/rule/` |
| `opal event config rule add` † | `--if-match ETAG`, `--id ID`, `--enabled/--no-enabled`, `--topic TEXT`, `--conditions JSON`, `--actions JSON` | Create rule. `POST /api/v1/rule/` |
| `opal event config rule show` † | `<rule_id>` | Get rule. `GET /api/v1/rule/{rule_id}` |
| `opal event config rule update` † | `<rule_id>`, `--if-match ETAG`, `--enabled/--no-enabled`, `--topic TEXT`, `--conditions JSON`, `--actions JSON` | Partially update rule. `PATCH /api/v1/rule/{rule_id}` |
| `opal event config rule remove` † | `<rule_id>`, `--if-match ETAG` | Delete rule. `DELETE /api/v1/rule/{rule_id}` |
| `opal event config rule test` † | `<rule_id>`, `--event JSON` | Evaluate rule without execution. `POST /api/v1/rule/{rule_id}/test` |
| `opal event config action list` † | — | List actions. `GET /api/v1/action/` |
| `opal event config action add` † | `--if-match ETAG`, `--id ID`, `--type [shell\|http\|python]`, `--enabled/--no-enabled`, `--description TEXT`, `--input-schema JSON`, `--keywords JSON`, `--suggested-prompts JSON`, `--mode [exec\|sh\|bash\|cmd\|powershell]`, `--executable PATH`, `--script-path PATH`, `--args JSON`, `--stdin [event_json\|none]`, `--timeout-seconds INT`, `--method [GET\|POST\|PUT\|PATCH\|DELETE]`, `--url URL`, `--headers JSON`, `--body JSON`, `--body-mode [template\|event_json\|none]`, `--module TEXT`, `--function TEXT` | Create action. `POST /api/v1/action/` |
| `opal event config action show` † | `<action_id>` | Get action. `GET /api/v1/action/{action_id}` |
| `opal event config action update` † | `<action_id>`, `--if-match ETAG`, `--enabled/--no-enabled`, `--mode [exec\|sh\|bash\|cmd\|powershell]`, `--executable PATH`, `--script-path PATH`, `--args JSON`, `--stdin [event_json\|none]`, `--timeout-seconds INT`, `--description TEXT`, `--input-schema JSON`, `--keywords JSON`, `--suggested-prompts JSON`, `--method [GET\|POST\|PUT\|PATCH\|DELETE]`, `--url URL`, `--headers JSON`, `--body JSON`, `--body-mode [template\|event_json\|none]`, `--module TEXT`, `--function TEXT` | Partially update action. `PATCH /api/v1/action/{action_id}` |
| `opal event config action remove` † | `<action_id>`, `--if-match ETAG` | Delete unused action. `DELETE /api/v1/action/{action_id}` |
| `opal event config action execute` † | `<action_id>`, `--event JSON`, `--wait` | Execute registered action manually. `POST /api/v1/action/{action_id}/execute` |
| `opal event data execution list` † | `--status TEXT`, `--rule-id ID`, `--action-id ID`, `--event-id ID`, `--limit INT` | List executions. `GET /api/v1/execution/` |
| `opal event data execution show` † | `<execution_id>` | Get execution result. `GET /api/v1/execution/{execution_id}` |
| `opal event info health` † | — | Service health report. `GET /api/v1/health/` |
| `opal event info stats` † | — | Get event and execution counters. `GET /api/v1/stats/` |
| `opal event config profile list` † | — | List profiles. `GET /api/v1/profile/` |
| `opal event config profile add` † | `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Create profile. `POST /api/v1/profile/` |
| `opal event config profile show` † | `<profile_id>` | Get profile. `GET /api/v1/profile/{profile_id}` |
| `opal event config profile update` † | `<profile_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--is-active/--no-is-active` | Update profile. `PATCH /api/v1/profile/{profile_id}` |
| `opal event config profile remove` † | `<profile_id>`, `--if-match ETAG` | Delete profile. `DELETE /api/v1/profile/{profile_id}` |
| `opal event config profile activate` † | `<profile_id>`, `--if-match ETAG` | Activate profile. `POST /api/v1/profile/{profile_id}/activate` |
| `opal event config setting list` | — | List settings (alias: `opal event setting get`). `GET /api/v1/setting/` |
| `opal event config setting update` | `--if-match ETAG`, `--data JSON` | Patch settings (alias: `opal event config setting patch`). `PATCH /api/v1/setting/` |
| `opal event config setting show` | `<key>` | Get setting (alias: `opal event setting get-key`). `GET /api/v1/setting/{key}` |
| `opal event config setting set` | `<key>`, `<value>`, `--if-match ETAG` | Set setting (alias: `opal event setting set-key`). `PUT /api/v1/setting/{key}` |
| `opal event config setting remove` | `<key>`, `--if-match ETAG` | Delete setting (alias: `opal event setting reset-key`). `DELETE /api/v1/setting/{key}` |
| `opal event info version` † | — | Service Info. `GET /api/v1/info/` |
| `opal event info ping` † | — | Ping. `GET /api/v1/info/ping` |
| `opal event info live` † | — | Liveness probe. `GET /api/v1/health/live` |
| `opal event info ready` † | — | Readiness probe. `GET /api/v1/health/ready` |
| `opal event backup list` † | — | List backups. `GET /api/v1/backup/list` |
| `opal event backup create` † | — | Create backup. `POST /api/v1/backup/create` |
| `opal event backup download` † | `<filename>`, `--out PATH` | Download backup. `GET /api/v1/backup/download/{filename}` |
| `opal event backup restore` † | `<filename>`, `--if-match ETAG` | Restore backup. `POST /api/v1/backup/restore/{filename}` |
| `opal event backup remove` † | `<filename>` | Delete backup. `DELETE /api/v1/backup/{filename}` |
| `opal event backup export` † | `--out PATH` | Export configuration. `GET /api/v1/backup/export` |
| `opal event backup import` † | `--if-match ETAG`, `--file PATH` | Import configuration. `POST /api/v1/backup/import` |
| `opal event backup validate` † | `--file PATH` | Validate configuration. `POST /api/v1/backup/validate` |
| `opal event service start` | `--append/--no-append` | Start service. `POST /api/v1/service/start` |
| `opal event service stop` | — | Stop service. `POST /api/v1/service/stop` |
| `opal event service log` | `--lines INT` | Tail service log. `GET /api/v1/service/log` |
| `opal event config persona list` † | `--enabled/--no-enabled` | List Personas. `GET /api/v1/persona/` |
| `opal event config persona add` † | `--if-match ETAG`, `--persona-id ID`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Create Persona. `POST /api/v1/persona/` |
| `opal event config persona validate` † | `<persona_id>` | Validate Persona. `POST /api/v1/persona/{persona_id}/validate` |
| `opal event config persona show` † | `<persona_id>` | Get Persona. `GET /api/v1/persona/{persona_id}` |
| `opal event config persona update` † | `<persona_id>`, `--if-match ETAG`, `--name TEXT`, `--description TEXT`, `--voice-id ID`, `--enabled/--no-enabled` | Update Persona. `PATCH /api/v1/persona/{persona_id}` |
| `opal event config persona remove` † | `<persona_id>`, `--if-match ETAG` | Delete Persona. `DELETE /api/v1/persona/{persona_id}` |

† Proposed name; the operation has no `x-opal-cli` annotation yet.

---

---

## Part 2: Usecases

One-liners per service. Each one calls only the service it is filed under, with no shell logic.

<a id="opal-say-usecases"></a>

### opal-say

**1. Say something out loud, right now.**

```bash
opal say generate "The build is green. I repeat, the build is green. This is not a drill." --play
```

**2. Save a greeting as a WAV file.**

```bash
opal say generate "Welcome to the museum. Please do not lick the exhibits." --out welcome.wav
```

**3. Pick a specific voice.**

```bash
opal say generate "Tea is served in the library." --voice-id en-gb-alan-low --play
```

**4. Speak as a persona and let its bound voice follow along.**

```bash
opal say generate "Good evening. I will be your narrator." --persona vox --play
```

**5. Slow down for the people in the back.**

```bash
opal say generate "Your verification code is four, seven, one, nine." --speed 0.8 --play
```

**6. Use an indoor voice.**

```bash
opal say generate "The baby is finally asleep. Nobody move." --volume 0.3 --play
```

**7. Produce raw 16 kHz PCM for a telephony system.**

```bash
opal say generate "Please hold. Your call is important to us, allegedly." --output-format pcm --sample-rate 16000 --out hold.pcm
```

**8. Stream a whole chapter as it is synthesized instead of waiting for the end.**

```bash
opal say stream @chapter-one.txt --play
```

**9. See which engines the host has installed.**

```bash
opal say engine list
```

**10. Check that an engine can run before blaming the voice.**

```bash
opal say engine validate piper
```

**11. Put a misbehaving engine in time-out without uninstalling it.**

```bash
opal say engine update kokoro --no-enabled
```

**12. Register a voice model that already lives on disk.**

```bash
opal say config voice add --voice-id en-us-lessac-medium --name "Lessac (US)" --engine-id piper --engine-voice-ref /opt/piper/voices/en_US-lessac-medium.onnx --language en-US
```

**13. Confirm that a voice's engine and files resolve.**

```bash
opal say config voice validate en-us-lessac-medium
```

**14. Audition a voice with a pangram.**

```bash
opal say config voice test en-us-lessac-medium --text "Sphinx of black quartz, judge my vow." --play
```

**15. List the enabled British voices.**

```bash
opal say config voice list --language en-GB --enabled
```

**16. Create a bedtime profile: slower, quieter, kinder.**

```bash
opal say config profile add --name bedtime --description "Slow and quiet for after dark" --voice-id en-gb-alan-low --speed 0.85 --volume 0.4
```

**17. Make that profile the default for every request that does not say otherwise.**

```bash
opal say config profile activate 2
```

**18. Create a persona bound to a voice.**

```bash
opal say config persona add --persona-id vox --name Vox --description "Calm narrator" --voice-id en-gb-alan-low
```

**19. Check that a persona's voice binding still resolves.**

```bash
opal say config persona validate vox
```

**20. Export the whole configuration before you start experimenting.**

```bash
opal say backup export --out say-config.json
```

<a id="opal-listen-usecases"></a>

### opal-listen

**1. Find the microphone before accusing the software of deafness.**

```bash
opal listen info audio-devices
```

**2. Register a wakeword with a stricter threshold.**

```bash
opal listen config wakeword add --name "hey opal" --confidence-threshold 0.85
```

**3. Create an intent with its first training phrases.**

```bash
opal listen config intent add --name lights.turn_on --description "Turn on the lights" --phrases '["turn on the lights","lights on","let there be light"]'
```

**4. Teach an existing intent one more way to say it.**

```bash
opal listen config phrase add 1 --phrase "illuminate the room"
```

**5. Create a slot for room names.**

```bash
opal listen config slot add --name room --slot-type list --description "Rooms in the house"
```

**6. Add a canonical value to the slot.**

```bash
opal listen config slot-value add 1 --value kitchen
```

**7. Give that value a nickname people actually use.**

```bash
opal listen config slot-alias add 1 1 --alias "the galley"
```

**8. Test a sentence against intents and slots without making a sound.**

```bash
opal listen recognition test-text --text "turn on the lights in the galley"
```

**9. Run a recording through the full pipeline, wakeword included.**

```bash
opal listen recognition test-audio kitchen-lights.wav --require-wakeword
```

**10. Try a silly sentence without cluttering the recognition log.**

```bash
opal listen recognition test-text --text "what is the airspeed velocity of an unladen swallow" --no-save-log
```

**11. Start listening on the live microphone.**

```bash
opal listen recognition start
```

**12. Watch live results, with debug detail, as they happen.**

```bash
opal listen recognition stream --debug
```

**13. Check pipeline state, queue depth, and dropped audio.**

```bash
opal listen recognition status
```

**14. Review the ten most recent misses nobody has looked at.**

```bash
opal listen data failed-utterance list --no-reviewed --limit 10
```

**15. Turn a miss into a training phrase and a regression case in one move.**

```bash
opal listen data failed-utterance promote 7 --intent-name lights.turn_on --create-regression
```

**16. Pin down expected behavior with a regression case.**

```bash
opal listen regression add --name "galley lights" --phrase "turn on the lights in the galley" --expected-intent lights.turn_on --expected-slots '{"room":"kitchen"}'
```

**17. Run the regression suite before you ship that "small tweak".**

```bash
opal listen regression run
```

**18. See where the milliseconds go.**

```bash
opal listen performance summary --limit 50
```

**19. Create a night profile that only understands light switches.**

```bash
opal listen config profile add --name night-mode --wakeword-names '["hey opal"]' --enabled-intents '["lights.turn_on","lights.turn_off"]'
```

**20. Allow live microphone matches to be published as events.**

```bash
opal listen config setting set event_publication_enabled true
```

<a id="opal-look-usecases"></a>

### opal-look

**1. See which inference engines the host offers.**

```bash
opal look engine list
opal look engine discover
```

**2. Inspect an engine's accepted options.**

```bash
opal look engine capabilities yolo
```

**3. List the models an engine owns.**

```bash
opal look model list --engine-id yolo
```

**4. Load a model for inference.**

```bash
opal look model load yolo11n
```

**5. Detect objects in a photo.**

```bash
opal look predict image --engine-id yolo --model-id yolo11n --source driveway.jpg
```

**6. Start a plain video stream — no engine needed.**

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1
```

**7. Watch the live feed.**

```bash
opal look stream watch-video str-42 --out front.mjpeg
```

**8. Grab the current frame as a JPEG.**

```bash
opal look stream snapshot str-42 --out front.jpg
```

**9. Turn on detection for the same camera.**

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1 --engine-id yolo --model-id yolo11n --annotate
```

**10. Follow detection events as they arrive.**

```bash
opal look stream watch str-43
```

**11. Watch the annotated feed.**

```bash
opal look stream watch-video str-43 --annotated --out detect.mjpeg
```

**12. Check a stream's counters and latency.**

```bash
opal look stream metrics str-43
```

**13. Stop a stream and release the camera.**

```bash
opal look stream stop str-43
```

**14. See what compute the service can use.**

```bash
opal look hardware list
```

**15. Make a stream start retry-safe.**

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1 --idempotency-key front-cam-2026-11-10
```

<a id="opal-think-usecases"></a>

### opal-think

**1. Ask a question and get the answer.**

```bash
opal think ask "Why is the sky blue? One sentence, no poetry."
```

**2. See which models are available right now.**

```bash
opal think model list
```

**3. Ask a specific model.**

```bash
opal think ask "Explain ETags to a golden retriever." --model-id ollama:llama3.2
```

**4. Submit a task with a leash: five steps, two minutes.**

```bash
opal think task create "Summarize the trade-offs between RTSP and MJPEG for home cameras." --max-steps 5 --timeout-seconds 120
```

**5. Watch a task's progress live.**

```bash
opal think task watch tsk-123
```

**6. Read the final, authoritative task record.**

```bash
opal think task show tsk-123
```

**7. Cancel a task that has wandered off.**

```bash
opal think task cancel tsk-123
```

**8. List recent failures.**

```bash
opal think task list --status failed --limit 10
```

**9. Open a session so follow-up questions have context.**

```bash
opal think session add --title "Lisbon trip"
```

**10. Start a conversation in that session.**

```bash
opal think chat "Plan a three-day trip to Lisbon for someone who hates hills." --session-id ses-lisbon
```

**11. Follow up without repeating yourself.**

```bash
opal think chat "Swap day two for something indoors; rain is forecast." --session-id ses-lisbon
```

**12. Review every task in the session.**

```bash
opal think task list --session-id ses-lisbon
```

**13. Remove the session and its retained tasks.**

```bash
opal think session remove ses-lisbon
```

**14. Supply facts as structured context.**

```bash
opal think ask "Which of these temperature readings looks wrong, and why?" --context '{"readings_c":[21.5,21.7,98.6,21.4]}'
```

**15. Tag a task with evaluation metadata.**

```bash
opal think task create "What is 17 times 23?" --metadata '{"evalset":"arithmetic","case_id":"mul-017"}' --wait
```

**16. Make a retry-safe submission with an idempotency key.**

```bash
opal think task create "Draft the nightly status report." --idempotency-key nightly-report-2026-11-10
```

**17. Set the default model.**

```bash
opal think config setting set models.default_id '"ollama:llama3.2"'
```

**18. Lower the default step budget.**

```bash
opal think config setting set task.default_max_steps 8
```

**19. Change several task limits in one atomic patch.**

```bash
opal think config setting update --data '{"task.max_concurrent":2,"task.retention_days":14}'
```

**20. Register a persona in the suite's authoritative persona registry.**

```bash
opal think config persona add --persona-id amy --name Amy --description "Ops assistant" --voice-id en-gb-alan-low
```

<a id="opal-event-usecases"></a>

### opal-event

**1. Publish an event.**

```bash
opal event publish --topic home.doorbell.pressed --data '{"door":"front"}'
```

**2. Publish a sensor reading with a named source.**

```bash
opal event publish --topic garden.soil.moisture --source greenhouse-pi --data '{"bed":"tomatoes","moisture_pct":14.2}'
```

**3. List the five most recent doorbell events.**

```bash
opal event data event list --topic home.doorbell.pressed --limit 5
```

**4. See every topic the service has observed.**

```bash
opal event data topic list
```

**5. Register a shell action that plays a chime.**

```bash
opal event config action add --id ring-bell --type shell --mode exec --executable /usr/bin/aplay --args '["/opt/sounds/ding-dong.wav"]' --stdin none --description "Play the doorbell chime."
```

**6. Register an HTTP action that forwards the whole event to a webhook.**

```bash
opal event config action add --id notify-webhook --type http --method POST --url https://hooks.example.com/opal --body-mode event_json --timeout-seconds 10
```

**7. Register an HTTP action with a templated body.**

```bash
opal event config action add --id log-door --type http --method POST --url https://hooks.example.com/doors --body-mode template --body '{"door":"{{data.door}}","event":"{{event}}"}'
```

**8. Register a Python plugin action.**

```bash
opal event config action add --id process-detection --type python --module opal_plugin --function process_detection --timeout-seconds 30
```

**9. Route doorbell events to the chime.**

```bash
opal event config rule add --id doorbell-chime --topic home.doorbell.pressed --conditions '[]' --actions '["ring-bell"]'
```

**10. Route a whole topic family, but only when a condition holds.**

```bash
opal event config rule add --id dry-tomatoes --topic 'garden.*' --conditions '[{"path":"data.moisture_pct","operator":"lt","value":20}]' --actions '["notify-webhook"]'
```

**11. Dry-run a rule against a sample event; no actions fire.**

```bash
opal event config rule test dry-tomatoes --event '{"topic":"garden.soil.moisture","data":{"bed":"tomatoes","moisture_pct":14.2}}'
```

**12. Fire an action by hand and wait for the result.**

```bash
opal event config action execute ring-bell --event '{"topic":"manual.test","data":{}}' --wait
```

**13. List recent failed executions.**

```bash
opal event data execution list --status failed --limit 20
```

**14. See everything one action has done lately.**

```bash
opal event data execution list --action-id ring-bell --limit 10
```

**15. Disable a rule without deleting it.**

```bash
opal event config rule update dry-tomatoes --no-enabled
```

**16. Tighten an action's timeout.**

```bash
opal event config action update notify-webhook --timeout-seconds 5
```

**17. Read the event and execution counters.**

```bash
opal event info stats
```

**18. Clear the stored event history.**

```bash
opal event data event clear
```

**19. Cap the size of accepted events.**

```bash
opal event config setting set max_event_bytes 262144
```

**20. Take a backup before rewiring the house.**

```bash
opal event backup create
```

---

---

## Part 3: Combined

Fifty recipes that use two or more services. Pipes between `opal` commands are the only shell used.

### Plumbing (do this once)

Most recipes rely on a few shared fixtures. Set them up first.

**Let Think find Event**, so tasks can discover and execute registered actions:

```bash
opal think config setting set event.base_url '"http://127.0.0.1:8080"'
```

**Let Listen publish live matches** to Event on `opal.listen.intent.match`. Only live microphone matches are published; `test-text` and `test-audio` results never are.

```bash
opal listen config setting update --data '{"event_publication_enabled":true,"event_transport":"http"}'
```

**Register a `speak` action.** Say returns audio bytes and plays nothing, so an HTTP action that posts to Say would synthesize speech that nobody hears. The `speak` action runs the CLI on the Event host instead, where `--play` reaches a speaker. Adjust the executable path to wherever `opal` is installed.

```bash
opal event config action add --id speak --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","{{data.text}}","--play"]' --stdin none --description "Speak data.text aloud through OPAL Say on this host's speakers." --keywords '["speak","say","announce"]' --input-schema '{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}'
```

Things to know before you wire anything:

- **Rule topics** are an exact topic or a `prefix.*` pattern. Conditions are ANDed. There are no timers, aggregation, or rule chains.
- **Templates** use `{{data.path}}` or `{{event}}`. A missing path fails the execution with `template_error`.
- **HTTP action destinations** must be on Event's allowlist.
- **Referenced resources must exist.** Recipes name streams, engines, models, intents, and sessions by ID without always creating them. Part 2 shows how to create each kind.
- **Speech is a Think decision.** Recipes that tell Think to "use the speak action" depend on the model choosing to call it. Read the task record with `opal think task show` when the house stays silent.
- **Payload field names are assumed.** The contracts name the topics (`opal.listen.intent.match`) but do not fix the fields under `data`. These recipes assume Listen publishes its recognition result fields (`data.intent_name`, `data.slot_values`, `data.transcript`) and that republished Look stream events carry the SSE detection payload (`data.detections[0].class_name`). Check a real event before trusting a condition:

```bash
opal event data event list --topic opal.listen.intent.match --limit 1
```

### Voice lab

#### 1. One phrase, every persona

*say + listen.* Generate the same phrase in each known persona's voice, then feed every recording to Listen to prove the intent matches regardless of who is talking. Repeat the pair of commands for each persona in the list.

```bash
opal say config persona list --enabled
opal say generate "hey opal, turn on the lights" --persona vox --out lights-vox.wav
opal say generate "hey opal, turn on the lights" --persona amy --out lights-amy.wav
opal say generate "hey opal, turn on the lights" --persona butler --out lights-butler.wav
opal listen recognition test-audio lights-vox.wav --require-wakeword
opal listen recognition test-audio lights-amy.wav --require-wakeword
opal listen recognition test-audio lights-butler.wav --require-wakeword
```

#### 2. Speed sweep

*say + listen.* Find out how fast someone can talk before recognition gives up.

```bash
opal say generate "hey opal, set a timer for ten minutes" --speed 0.75 --out timer-slow.wav
opal say generate "hey opal, set a timer for ten minutes" --speed 1.0 --out timer-normal.wav
opal say generate "hey opal, set a timer for ten minutes" --speed 1.5 --out timer-espresso.wav
opal listen recognition test-audio timer-slow.wav --require-wakeword
opal listen recognition test-audio timer-normal.wav --require-wakeword
opal listen recognition test-audio timer-espresso.wav --require-wakeword
```

#### 3. Paraphrase factory

*think + listen.* Let Think invent a new way to say something and add it straight to the intent's training phrases.

```bash
opal think ask "Give me one natural way a person might ask to turn on the lights that is not 'turn on the lights'. Reply with the phrase only, lowercase, no punctuation." | opal listen config phrase add 1 --phrase -
```

#### 4. Synthetic round trip

*think + say + listen.* Think writes a tricky utterance, Say speaks it, and Listen tries to understand it. No humans were inconvenienced.

```bash
opal think ask "Write one short, slightly mumbled-sounding way to ask for the kitchen lights to be turned on. Reply with the phrase only." | opal say generate - --out tricky.wav
opal listen recognition test-audio tricky.wav
```

#### 5. The miss whisperer

*listen + think.* Hand a failed utterance to Think and ask what the speaker meant.

```bash
opal listen data failed-utterance show 7 | opal think ask "This utterance matched no intent. My intents are lights.turn_on, lights.turn_off, and timer.set. Which one did the speaker most likely mean? Reply with the intent name only." --context -
opal listen data failed-utterance promote 7 --intent-name lights.turn_on --create-regression
```

#### 6. Spoken regression report

*listen + think + say.* Run the regression suite and have the result read to you while you get coffee.

```bash
opal listen regression run | opal think ask "Summarize this regression run in one sentence. Mention the pass rate and name any failing case." --context - | opal say generate - --play
```

#### 7. One persona, two services

*think + say.* Think owns the authoritative persona registry; Say binds the voice. Register the same `persona_id` in both, validate the binding, and use it.

```bash
opal think config persona add --persona-id amy --name Amy --description "Ops assistant" --voice-id en-gb-alan-low
opal say config persona add --persona-id amy --name Amy --description "Ops assistant" --voice-id en-gb-alan-low
opal say config persona validate amy
opal think ask "Introduce yourself as Amy, the ops assistant, in one friendly sentence." | opal say generate - --persona amy --play
```

### Eyes on the property

#### 8. Verbally notify me when someone is in my front yard

*look + event + say.* An inference stream republishes its detections to Event; Event routes a person match to Say. There are no zones in this contract, so aim the camera at the yard.

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1 --engine-id yolo --model-id yolo11n
opal look stream watch str-42 | opal event publish --topic yard.detection --source opal-look --data -
opal event config action add --id announce-front-yard --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Heads up. Someone is in the front yard.","--play"]' --stdin none --description "Announce a visitor in the front yard."
opal event config rule add --id front-yard-visitor --topic yard.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' --actions '["announce-front-yard"]'
```

#### 9. What does the camera see?

*look + think + say.* Snapshot a stream, run detection on the frame, and get a spoken one-sentence description.

```bash
opal look stream snapshot str-front --out front.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source front.jpg | opal think ask "Describe what the camera sees in one plain sentence, using only these detections." --context - | opal say generate - --play
```

#### 10. Package on the porch

*look + event + say.* A package appears on the porch stream; the house says so. This assumes a model with a `package` class.

```bash
opal look stream start --source rtsp://192.168.1.41:554/stream1 --engine-id yolo --model-id yolo11n
opal look stream watch str-44 | opal event publish --topic porch.detection --source opal-look --data -
opal event config action add --id announce-package --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","A package has arrived. Act natural.","--play"]' --stdin none --description "Announce a delivered package."
opal event config rule add --id package-alert --topic porch.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"package"}]' --actions '["announce-package"]'
```

#### 11. The porch visitor

*look + event + say.* Someone shows up at the porch: keep a frame and let them know, politely.

```bash
opal look stream watch str-porch | opal event publish --topic porch.detection --source opal-look --data -
opal event config action add --id snapshot-porch --type shell --mode exec --executable /usr/local/bin/opal --args '["look","stream","snapshot","str-porch","--out","/tmp/porch.jpg"]' --stdin none --description "Keep a frame from the porch camera."
opal event config action add --id warn-visitor --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Hello there. You are on camera. Have a lovely day.","--persona","vox","--play"]' --stdin none --description "Politely greet a visitor."
opal event config rule add --id porch-visitor-response --topic porch.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' --actions '["snapshot-porch","warn-visitor"]'
```

#### 12. Driveway is full

*look + think + say.* Three or more cars in the driveway means company. Snapshot, count the detections, and hear the verdict.

```bash
opal look stream snapshot str-driveway --out drive.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source drive.jpg | opal think ask "Using only these detections: if three or more cars appear, reply with one sentence announcing that the driveway is full; otherwise reply with exactly the word clear." --context - | opal say generate - --play
```

#### 13. The camera went dark

*look + event + say.* A stream fails; you hear about it before the burglars do.

```bash
opal look stream watch str-front | opal event publish --topic front.stream --source opal-look --data -
opal event config action add --id announce-camera-down --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","A camera stream has failed. Please check the cameras.","--play"]' --stdin none --description "Announce a failed camera stream."
opal event config rule add --id camera-down --topic front.stream --conditions '[{"path":"data.status","operator":"eq","value":"failed"}]' --actions '["announce-camera-down"]'
```

#### 14. Off the couch, Biscuit

*look + event + think + say.* The dog shows up on the couch camera. Think writes a fresh scolding every time, so Biscuit never gets used to it, and delivers it through the `speak` action.

```bash
opal look stream watch str-living-room | opal event publish --topic couch.detection --source opal-look --data -
opal event config action add --id scold-dog --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A dog named Biscuit just climbed onto the couch. Write one short, firm, funny sentence telling him to get off, then say it aloud with the speak action.","max_steps":4}' --description "Ask Think to scold the dog out loud."
opal event config rule add --id couch-patrol --topic couch.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"dog"}]' --actions '["scold-dog"]'
```

#### 15. The visitor digest

*look + event + think + say.* Republished detections pile up in Event all day; Think summarizes them at night. This reuses the `yard.detection` republisher from recipe 8.

```bash
opal event data event list --topic yard.detection --limit 100 | opal think ask "Summarize today's front-yard visitors in two sentences: roughly how many visits and at what times of day." --context - | opal say generate - --play
```

#### 16. Say "cheese"

*listen + event + look.* A spoken command snapshots the front camera stream. This needs a running stream, `str-front` here.

```bash
opal listen config intent add --name camera.snapshot --description "Capture a frame from the front camera" --phrases '["take a picture","snapshot the front yard","say cheese"]'
opal event config action add --id capture-front --type shell --mode exec --executable /usr/local/bin/opal --args '["look","stream","snapshot","str-front","--out","/tmp/cheese.jpg"]' --stdin none --description "Snapshot the front camera stream to a file."
opal event config rule add --id voice-snapshot --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"camera.snapshot"}]' --actions '["capture-front"]'
```

#### 17. "Who's at the door?"

*listen + event + think + look + say.* All five services, one question. Listen hears it, Event hands it to Think, Think runs the camera check through a registered action, reads the execution result, and answers with `speak`.

```bash
opal look stream start --source rtsp://192.168.1.40:554/stream1 --engine-id yolo --model-id yolo11n
opal listen config intent add --name door.who --description "Ask who is at the front door" --phrases '["who is at the door","is someone outside","check the front door"]'
opal event config action add --id look-front-door --type http --method POST --url http://127.0.0.1:8082/api/v1/predict --body-mode template --body '{"engine_id":"yolo","model_id":"yolo11n","source":"http://127.0.0.1:8082/api/v1/stream/str-front/snapshot"}' --description "Run detection on the current front-door frame and return the detections." --keywords '["camera","door","look"]'
opal event config action add --id answer-door --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Run the look-front-door action, then use the speak action to say in one sentence who or what is at the front door.","max_steps":6}' --description "Ask Think to check the door and answer aloud."
opal event config rule add --id who-is-there --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"door.who"}]' --actions '["answer-door"]'
```

### The classroom

#### 18. Random facts

*think + say.* One fact, spoken, on demand.

```bash
opal think ask "Tell me one surprising, true fact about octopuses in a single sentence." | opal say generate - --play
```

#### 19. "Tell me something interesting"

*listen + event + think + say.* The same trick, hands-free.

```bash
opal listen config intent add --name fact.random --description "Ask for a random fact" --phrases '["tell me something interesting","give me a fun fact","surprise me"]'
opal event config action add --id tell-fact --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Pick one surprising, true fact from science or history and say it aloud in a single sentence with the speak action.","max_steps":3}' --description "Ask Think to speak a random fact."
opal event config rule add --id fact-on-demand --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"fact.random"}]' --actions '["tell-fact"]'
```

#### 20. Make up a story about...

*think + say.* A bedtime story, streamed so the narration starts before the ending is synthesized.

```bash
opal think ask "Make up a two-minute bedtime story about a lighthouse keeper's cat who is afraid of the dark." --timeout-seconds 300 | opal say stream - --persona vox --speed 0.9 --play
```

#### 21. A story about whatever they just asked for

*listen + event + think + say.* Say "tell me a story about dragons" and the transcript carries the subject into Think's prompt.

```bash
opal listen config intent add --name story.tell --description "Ask for a made-up story" --phrases '["tell me a story about","make up a story about","story time"]'
opal event config action add --id tell-story --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A child asked for a story with these words: {{data.transcript}}. Make up a one-minute story on that subject and tell it aloud with the speak action.","timeout_seconds":300}' --description "Ask Think to tell a story about the requested topic."
opal event config rule add --id story-time --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"story.tell"}]' --actions '["tell-story"]'
```

#### 22. Multiplication tables

*think + say.* The seven times table, recited at a pace a nine-year-old can follow.

```bash
opal think ask "Recite the 7 times table from 7 times 1 through 7 times 12. One fact per sentence, with numbers written as words." | opal say generate - --speed 0.85 --play
```

#### 23. Timed multiplication tables

*think + say + listen + event.* A drill with a clock. Think asks each question through `speak`. The student answers into the live microphone, Listen publishes the match, and Event forwards the transcript plus the whole event, timestamp included, into the same Think session. Think marks late answers and asks the next question.

```bash
opal think session add --title "Timed sevens"
opal listen config intent add --name math.answer --description "A spoken answer to a math question" --phrases '["the answer is","my answer is","is it"]'
opal event config action add --id grade-answer --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"session_id":"ses-sevens","prompt":"The student answered: {{data.transcript}}. The context holds the answer event with its timestamp. If the answer is wrong, or arrived more than five seconds after your last question, count it as a miss. Use the speak action to give the verdict and ask the next question. After ten questions, speak the final score instead.","context":"{{event}}","max_steps":4}' --description "Grade a spoken answer in the timed drill session."
opal event config rule add --id timed-drill --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"math.answer"}]' --actions '["grade-answer"]'
opal listen recognition start
opal think chat "Start a timed drill of the 7 times table. Ask the first question aloud with the speak action and remember when you asked it." --session-id ses-sevens
```

#### 24. Verbal quiz

*think + say + listen.* Think asks, Say speaks, Listen transcribes the answer, and Think grades it. The session keeps score between turns.

```bash
opal think session add --title "Capitals quiz"
opal think chat "You are a quizmaster. Ask me question one about world capitals. Do not reveal the answer." --session-id ses-quiz | opal say generate - --play
opal listen recognition test-audio answer-1.wav | opal think chat "The context is a recognition result. Grade its transcript as my answer, tell me the score so far, and ask the next question." --session-id ses-quiz --context - | opal say generate - --play
```

#### 25. Math questions

*think + say + listen.* A word problem, a spoken attempt, and feedback that explains instead of just judging.

```bash
opal think session add --title "Word problems"
opal think chat "Ask me one word problem about fractions suitable for a ten-year-old. Do not give the answer." --session-id ses-math | opal say generate - --play
opal listen recognition test-audio my-answer.wav | opal think chat "The context is a recognition result. Check its transcript against the problem you asked. If it is wrong, explain the first mistake in two sentences without giving the final answer." --session-id ses-math --context - | opal say generate - --play
```

#### 26. Spelling bee

*think + say + listen.* Say pronounces the word slowly; the student spells it aloud; Think is the judge.

```bash
opal think session add --title "Spelling bee"
opal think chat "Pick one commonly misspelled English word for a twelve-year-old. Reply with the word only." --session-id ses-bee | opal say generate - --speed 0.8 --play
opal listen recognition test-audio spelling-attempt.wav | opal think chat "The context is a recognition result whose transcript is my letter-by-letter spelling of your word. Tell me whether it is correct, then spell the word properly." --session-id ses-bee --context - | opal say generate - --play
```

#### 27. Language practice

*think + say.* Translate a sentence and hear it in a native voice.

```bash
opal think ask "Translate into Spanish: Where is the library, and does it have snacks? Reply with the translation only." | opal say generate - --voice-id es-es-davefx-medium --speed 0.9 --play
```

#### 28. Read my homework to me

*look + think + say.* Photograph the worksheet, detect what is on the page, and get a hint rather than the answer.

```bash
opal look predict image --engine-id yolo --model-id yolo11n --source worksheet.jpg | opal think ask "These detections are from a homework problem. Describe what is on the page in two short sentences, then offer to explain how to approach it." --context - | opal say generate - --play
```

### Voice assistant

#### 29. Ask Opal anything

*listen + event + think + say.* The classic. A catch-all intent forwards the transcript to Think, which answers out loud.

```bash
opal listen config intent add --name assistant.ask --description "A general question for the assistant" --phrases '["i have a question","answer me this","can you tell me"]'
opal event config action add --id ask-think --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"Answer the question in this transcript in at most two sentences, and say the answer aloud with the speak action. Transcript: {{data.transcript}}","max_steps":4}' --description "Ask Think to answer a spoken question aloud."
opal event config rule add --id ask-opal --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"assistant.ask"}]' --actions '["ask-think"]'
```

#### 30. Lights, with manners

*listen + event + say.* One rule, two independent actions: the hub switches the lights and the house confirms. The `room` slot fills the URL path.

```bash
opal event config action add --id lights-on --type http --method POST --url 'http://127.0.0.1:8123/api/lights/{{data.slot_values.room}}/on' --body-mode none --description "Turn on the lights in the requested room."
opal event config action add --id confirm-lights --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Lights on in the {{data.slot_values.room}}.","--play"]' --stdin none --description "Confirm the lights aloud."
opal event config rule add --id lights-on-rule --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"lights.turn_on"},{"path":"data.slot_values.room","operator":"exists","value":true}]' --actions '["lights-on","confirm-lights"]'
```

#### 31. The dinner bell

*listen + event + say.* Say "call everyone for dinner" and let a louder voice do the shouting.

```bash
opal listen config intent add --name announce.dinner --description "Announce that dinner is ready" --phrases '["call everyone for dinner","dinner is ready","ring the dinner bell"]'
opal event config action add --id announce-dinner --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Dinner is ready. This is not a suggestion.","--volume","1.5","--play"]' --stdin none --description "Announce dinner loudly."
opal event config rule add --id dinner-bell --topic opal.listen.intent.match --conditions '[{"path":"data.intent_name","operator":"eq","value":"announce.dinner"}]' --actions '["announce-dinner"]'
```

#### 32. Morning briefing

*think + event + look + say.* One command. Think checks the porch through the `look-front-door` action from recipe 17 and reports through `speak`.

```bash
opal think ask "Give me a morning briefing. Run the look-front-door action to check the porch, then use the speak action to tell me in two sentences what is out there and wish me a good morning." --max-steps 6
```

#### 33. How is my hearing?

*listen + think + say.* A spoken verdict on the voice pipeline's latency.

```bash
opal listen performance summary --limit 50 | opal think ask "In one sentence, say whether this voice pipeline is fast or slow and which stage takes the longest." --context - | opal say generate - --play
```

#### 34. Goodnight mode

*say + listen + look.* Three profile switches: a quiet voice, a short list of night-time intents, and a night-time detection setup.

```bash
opal say config profile activate 2
opal listen config profile activate 3
opal look config profile activate 2
```

### Home automation

#### 35. The doorbell

*event + say + look.* Any device that can publish an event becomes a doorbell that announces itself and takes a picture. It reuses `capture-front` from recipe 16.

```bash
opal event config action add --id announce-doorbell --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Someone is at the {{data.door}} door.","--play"]' --stdin none --description "Announce which doorbell was pressed."
opal event config rule add --id doorbell --topic home.doorbell.pressed --conditions '[]' --actions '["announce-doorbell","capture-front"]'
opal event publish --topic home.doorbell.pressed --data '{"door":"front"}'
```

#### 36. Welcome home

*look + event + say.* A person appears on the hallway camera; the house says hello.

```bash
opal look stream watch str-hallway | opal event publish --topic hallway.detection --source opal-look --data -
opal event config action add --id welcome-home --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Welcome home. The dog has been told you were gone for years.","--play"]' --stdin none --description "Greet someone arriving home."
opal event config rule add --id greet-arrival --topic hallway.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' --actions '["welcome-home"]'
```

#### 37. Thirsty tomatoes

*event + think + say.* A moisture sensor publishes a reading. Below 20 percent, Think turns the number into a reminder and speaks it.

```bash
opal event config action add --id water-reminder --type http --method POST --url http://127.0.0.1:8083/api/v1/task/ --body-mode template --body '{"prompt":"A garden sensor reports low soil moisture. The reading is in the context. Use the speak action to give a one-sentence watering reminder that names the bed and the moisture percentage.","context":"{{event}}","max_steps":3}' --description "Ask Think to speak a watering reminder."
opal event config rule add --id thirsty-plants --topic 'garden.*' --conditions '[{"path":"data.moisture_pct","operator":"lt","value":20}]' --actions '["water-reminder"]'
opal event publish --topic garden.soil.moisture --source greenhouse-pi --data '{"bed":"tomatoes","moisture_pct":14.2}'
```

#### 38. Leak alarm

*event + say + look.* A water sensor trips: announce it and grab a frame of the basement for the insurance claim. This needs a running `str-basement` stream.

```bash
opal event config action add --id announce-leak --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Water detected in the {{data.location}}. This is not the fun kind of indoor pool.","--volume","1.5","--play"]' --stdin none --description "Announce a water leak."
opal event config action add --id snapshot-basement --type shell --mode exec --executable /usr/local/bin/opal --args '["look","stream","snapshot","str-basement","--out","/tmp/leak.jpg"]' --stdin none --description "Snapshot the basement camera to a file."
opal event config rule add --id leak-response --topic home.leak.detected --conditions '[]' --actions '["announce-leak","snapshot-basement"]'
```

#### 39. Workshop safety officer

*look + event + say.* A person shows up on the workshop camera and gets reminded about their eyes.

```bash
opal look stream watch str-workshop | opal event publish --topic workshop.detection --source opal-look --data -
opal event config action add --id safety-reminder --type shell --mode exec --executable /usr/local/bin/opal --args '["say","generate","Safety glasses. You only get two eyes, and no, the warranty has expired.","--play"]' --stdin none --description "Remind the woodworker about safety glasses."
opal event config rule add --id saw-safety --topic workshop.detection --conditions '[{"path":"data.detections[0].class_name","operator":"eq","value":"person"}]' --actions '["safety-reminder"]'
```

### Office and computer

#### 40. The build finished

*event + say.* Any script that can publish an event can talk. The `speak` action reads `data.text`.

```bash
opal event config rule add --id ci-announcer --topic 'ci.*' --conditions '[{"path":"data.text","operator":"exists","value":true}]' --actions '["speak"]'
opal event publish --topic ci.build.finished --source jenkins --data '{"text":"The build passed. You may now exhale."}'
```

#### 41. Log triage

*look + think + say.* Let Think read the log tail so you do not have to.

```bash
opal look service log --lines 50 | opal think ask "This is a service log tail. Name the most serious problem in one sentence, or say that it looks healthy." --context - | opal say generate - --play
```

#### 42. Your laptop left without you

*look + think + say.* Check whether the laptop is still on the desk, and hear about it if it is not.

```bash
opal look stream snapshot str-desk --out desk.jpg
opal look predict image --engine-id yolo --model-id yolo11n --source desk.jpg | opal think ask "These detections are of a desk. If no laptop appears, reply with one sentence announcing the laptop has left the desk; otherwise reply with exactly the word still-here." --context - | opal say generate - --play
```

#### 43. Stand-up digest

*event + think + say.* Yesterday's events, in three sentences, before the meeting that should have been an email.

```bash
opal event data event list --from 2026-11-09T00:00:00Z --to 2026-11-10T00:00:00Z --limit 200 | opal think ask "Summarize these events in three short sentences for a team stand-up. Group them by topic." --context - | opal say generate - --play
```

#### 44. Dock activity review

*look + event + think.* Republish a loading-dock detection stream, then ask for the highlights.

```bash
opal look stream watch str-dock | opal event publish --topic dock.detection --source opal-look --data -
opal event data event list --topic dock.detection --limit 200 | opal think ask "Summarize this loading-dock activity in three sentences: what appeared, when, and anything unusual." --context -
```

#### 45. Why didn't that work?

*event + think + say.* Hand a failed execution record to Think for a diagnosis.

```bash
opal event data execution list --status failed --limit 5
opal event data execution show exe-41 | opal think ask "This is a failed action execution record. Explain the most likely cause in one sentence and suggest one fix." --context - | opal say generate - --play
```

### Fleet operations

#### 46. Readiness roll call

*say + listen + look + think + event.* Five probes, then a spoken all-clear.

```bash
opal say info ready
opal listen info ready
opal look info ready
opal think info ready
opal event info ready
opal say generate "All five services report ready. Suspiciously ready." --play
```

#### 47. Back up everything

*say + listen + look + think + event.* A server-side snapshot of every service's configuration, with a receipt you can hear.

```bash
opal say backup create
opal listen backup create
opal look backup create
opal think backup create
opal event backup create
opal say generate "All five configurations are backed up. You may now break things." --play
```

#### 48. Configuration audit

*event + look + think.* Export two configurations and ask Think to find loose ends.

```bash
opal event backup export | opal think ask "This is an event service configuration export. List any rule that references an action ID that is not defined, or say there are none." --context -
opal look backup export | opal think ask "This is a vision service configuration export. List any profile or setting that references an engine or model that is not defined, or say there are none." --context -
```

#### 49. Rehearsal without hardware

*listen + event + say.* Prove the whole chain without a microphone or a camera: Listen matches the text, Event dry-runs the rule, and `speak` is fired by hand.

```bash
opal listen recognition test-text --text "call everyone for dinner"
opal event config rule test dinner-bell --event '{"topic":"opal.listen.intent.match","data":{"intent_name":"announce.dinner","transcript":"call everyone for dinner"}}'
opal event config action execute speak --event '{"topic":"manual.test","data":{"text":"This is a rehearsal. Dinner is not actually ready."}}' --wait
```

#### 50. Lights out

*say + listen + look + think + event.* A dignified sign-off, a marker in the event history, and five clean stops. Event goes last so it can record the others leaving.

```bash
opal say generate "All OPAL services are standing down for maintenance. Goodnight." --play
opal event publish --topic ops.fleet.shutdown --source cli --data '{"reason":"scheduled maintenance"}'
opal look service stop
opal listen service stop
opal think service stop
opal say service stop
opal event service stop
```
