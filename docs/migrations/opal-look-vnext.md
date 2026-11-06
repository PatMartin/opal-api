# OPAL Look — 1.4.0 → vNext Migration Guide

**Status:** proposal only. `openapi/proposals/opal_look.vnext.yaml` is `x-opal-stage: draft`, version `2.0.0-draft.1`. The published `openapi/opal_look.yaml` 1.4.0 contract is **unchanged** and remains the stable API.

Companion automated diff: [`opal-look-vnext-diff.md`](./opal-look-vnext-diff.md) (regenerate via `python tools_diff_look_vnext.py`).

---

## 1. Architecture change summary

| 1.4.0 | vNext | Status |
|---|---|---|
| Sessions own live view + observation scoping | Connection-scoped live streams on `sources`/`monitors`; no `/sessions/` | **Changed** — sessions removed entirely |
| Profiles own inference presets (`/profiles/` + `activate`) | `Pipeline` owns reusable inference + processing configuration | **Changed** — profile CRUD removed |
| Zones as standalone resources (`/zones/`) | Zones are fields inside `Source` (`SourceZone`) | **Changed** — zone CRUD removed |
| Rules as standalone resources (`/rules/`) | `Monitor` owns persistent observation conditions | **Changed** — rule CRUD removed |
| Captures + artifacts as separate surfaces | `Media` unifies uploads, captures, generated artifacts | **Changed** — two surfaces folded into one |
| `GET /sources/{id}/stream` (SSE) | same + `GET /sources/{id}/observations/stream` + `GET /monitors/{id}/observations/stream` | **Extended** |

`/api/v1` route prefix is retained in the draft. A `/api/v2/` or namespaced publication decision is deferred to §6.

---

## 2. Removed / changed endpoints

### Sessions (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `POST /sessions/` | `GET /sources/{id}/stream` — open a connection directly on the source; no admission step | drop session creation + 202 polling; connect to the source stream with `Idempotency-Key`-free GET | `look session create` → `look source stream SOURCE_ID` |
| `GET /sessions/{id}` | `GET /sources/{id}/status` | query the source's own state | `look session show` → `look source status` |
| `POST /sessions/{id}/stop` | close the stream connection | the transport is the lifecycle | `look session stop` → disconnect |
| `GET /sessions/{id}/stream` | `GET /sources/{id}/stream` or `GET /monitors/{id}/observations/stream` | pick the scope that owns the stream | `look session stream` → `look source stream` / `look monitor stream` |
| `GET /sessions/{id}/preview` | `GET /sources/{id}/stream` with `presentation_filter`/quality params | same MJPEG surface, no session indirection | `look session preview` → `look source stream --presentation …` |
| `GET /sessions/{id}/observations/` | `GET /observations/` filtered by `source_id`/`monitor_id` | query the retained surface, not a session | `look session observations` → `look observation list --source-id …` |

**Preservation:** the live-view capability survives; the *session-as-resource* abstraction does not. A session is now a transport connection, not an addressable object.

### Profiles (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `GET/POST /profiles/`, `GET/PATCH/DELETE /profiles/{id}`, `POST /profiles/{id}/activate` | `GET/POST /pipelines/`, `PATCH/DELETE /pipelines/{id}`, `POST /pipelines/validate` | pipelines are the configuration unit; select via `pipeline_id` on sources/streams/analyze — no "activate" step | `look profile create/activate` → `look pipeline add` + `--pipeline` |

**Preservation:** named inference presets survive as pipelines; the *activate/selected-profile* indirection is gone. `PipelinePatch` accepts the same engine/model/option fields.

### Zones (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `GET/POST /zones/`, `GET/PATCH/DELETE /zones/{id}` | zones live inside `Source` (`SourceZone`) — set via `POST /sources/` or `PATCH /sources/{id}` | zones are source configuration, not resources | `look zone add` → `look source update --zones '[…]'` |

**Preservation:** zone geometry/masking survives; the standalone zone CRUD surface does not.

### Rules (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `GET/POST /rules/`, `GET/PATCH/DELETE /rules/{id}` | `Monitor` owns persistent observation conditions (`POST /monitors/` with `MonitorCondition`) | conditions are monitor-scoped | `look rule add` → `look monitor add` |

**Preservation:** persistent-condition dispatch survives as monitors; the generic rule resource is gone. `MonitorCondition` carries the same filter + action intent.

### Captures (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `GET /captures/`, `GET/DELETE /captures/{id}`, `GET /captures/{id}/content`, `POST /sources/{id}/captures/` | `POST /sources/{id}/capture` (immediate still) + `GET /media/`/`GET /media/{id}`/`GET /media/{id}/content` | captures are media of `kind: capture` | `look capture list/get` → `look media list --kind capture` |

**Preservation:** still-image capture survives — `POST /sources/{id}/capture` is the direct equivalent of `POST /sources/{id}/captures/`; retrieval via unified media.

### Artifacts (all removed)

| 1.4.0 | vNext replacement | Client change | CLI change |
|---|---|---|---|
| `GET /artifacts/`, `GET/DELETE /artifacts/{id}`, `GET /artifacts/{id}/content` | `GET /media/` filtered by `kind` + `GET /media/{id}`/`GET /media/{id}/content` | artifacts are media of `kind: export`/`job` | `look artifact list` → `look media list --kind export` |

**Preservation:** generated-artifact retrieval survives via media `kind` filtering; the separate surface is folded.

---

## 3. Added endpoints

| vNext | Purpose | 1.4.0 equivalent |
|---|---|---|
| `GET /media/{media_id}/content` | binary body for unified media | `GET /artifacts/{id}/content` + `GET /captures/{id}/content` |
| `GET /sources/{id}/observations/stream` | connection-scoped observation stream on a source | `GET /sessions/{id}/stream` |
| `GET /monitors/{id}/observations/stream` | persistent observation stream on a monitor | `GET /sessions/{id}/stream` (monitor-scoped) |
| `POST /sources/{id}/capture` | immediate still capture | `POST /sources/{id}/captures/` |

---

## 4. Schema-level differences

| 1.4.0 | vNext |
|---|---|
| `Session*` family | removed; transport is the lifecycle |
| `Profile*` family | replaced by `Pipeline*` + `PipelineStage`/`ProcessingStageOptions` |
| `Zone*` family | replaced by `SourceZone` inside `Source`/`SourceCreate`/`SourcePatch` |
| `Rule*` family | replaced by `Monitor*` + `MonitorCondition` |
| `Capture*` family | folded into `Media` (`kind: capture`) + `CaptureRequest` for the immediate op |
| `Artifact*` family | folded into `Media` (`kind: export`/`job`) |
| `JobPage`/`SessionPage`/`ObservationPage` cursor envelopes | unchanged — cursor pagination convention preserved |

`Id`, `Timestamp`, `OpalError`, `OpalHealthProbe`/`Probe`, `OpalIfMatch`, `x-opal-context-standard`, `x-opal-event-contract` — unchanged conventions.

---

## 5. Functionality that cannot be reproduced in vNext

- **Session-scoped observation history** — `/sessions/{id}/observations/` is gone; queries must be by `source_id` or `monitor_id`. A session's *exact* observation set is not reproducible.
- **Named, activatable profile presets** — the "activate" indirection is gone; pipelines carry the config but there is no global "selected profile."
- **Standalone zone/rule CRUD** — zones and conditions are nested inside sources/monitors; there is no shared zone/rule resource.
- **Session preview** — `GET /sessions/{id}/preview` (dedicated low-res MJPEG preview) is gone; `GET /sources/{id}/stream` with `presentation_filter`/`quality`/`target_fps` is the nearest equivalent but is the full stream surface, not a preview-only channel.
- **Per-session admission/ETag semantics** — no admission step exists; connection-scoped viewing has no precondition handshake.

---

## 6. Release / version strategy

**Recommendation:** publish vNext as a **new major contract** (`info.version: 2.0.0`, `x-opal-stage: published`) — never as a compatible 1.4.x bump.

- **Coexistence window:** run 1.4.0 and 2.0.0 side-by-side for a defined migration window; the 1.4.0 surface stays live while clients migrate. `/api/v1` stays bound to 1.4.0 during coexistence; the draft may be exposed under `/api/v2/` or a namespaced mount.
- **No in-place replacement:** do not point `/api/v1` at the 2.0.0 schema — the 32 removed ops make it a breaking change.
- **Rollback:** keeping `opal_look.yaml` 1.4.0 intact (as this commit does) is the rollback — if vNext is retracted, the published contract is untouched.
- **Client migration order:** sessions→streams, profiles→pipelines, zones→source fields, rules→monitors, captures+artifacts→media.
- **EVENT boundary:** external automation stays with EVENT; Look emits `data.metadata` correlation on its two-frame envelope — unchanged.

## 7. Client migration checklist

1. Replace `/sessions/*` flows with `GET /sources/{id}/stream` / `GET /monitors/{id}/observations/stream`.
2. Replace `/profiles/*` + `activate` with `POST /pipelines/` + `pipeline_id` selection.
3. Move zone config into `POST /sources/` / `PATCH /sources/{id}` `SourceZone` fields.
4. Replace `/rules/*` with `POST /monitors/` `MonitorCondition`.
5. Replace `/captures/*` + `/artifacts/*` retrieval with `GET /media/` filtered by `kind`.
6. Re-point SSE clients at `/sources/{id}/stream` or `/monitors/{id}/observations/stream`.
7. Update CLI invocations per §2's `look` command column.
