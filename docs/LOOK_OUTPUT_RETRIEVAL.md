# OPAL Look Output Retrieval Workflow

Status: accepted. Contract work: `add common Look output references`;
implementation: `implement common Look output retrieval` in opal-look.

## Lifecycle map

Clients receive four different identifiers across `media`, `capture`,
`artifact` and `recording`, but bytes are retrievable through exactly two
routes today.

| flow | id received | where bytes live | available when | retention/deletion |
|---|---|---|---|---|
| `POST /api/v1/media/` (upload) | `media_id` | input-side only — **no download route** | on upload | `expires_at` sweep or `DELETE /media/{id}` removes input |
| `POST /api/v1/source/{id}/capture` / `/frame` | `capture_id` | `GET /capture/{id}/content` (JPEG/PNG) | immediate (exact frame) | `expires_at` sweep or `DELETE /capture/{id}` removes bytes |
| job completes (pipeline/export) | `artifact_ids[]` on the job result | `GET /artifact/{id}/content` | when the producing job finishes | `expires_at` sweep or `DELETE /artifact/{id}` removes bytes |
| `POST /api/v1/recording/` … `/stop` | `recording_id`, then `artifact_id` on the finished Recording | `GET /artifact/{id}/content` | after stop/finalize | same artifact rules; recording metadata is separate |

`media` is deliberately out of scope: it is an analysis *input* (uploaded
frames for `analyze`), not a produced output. The three real output flows
are capture, job/export artifacts, and recordings finalizing to artifacts.

## Distinctions that must survive

- **Two byte routes, three output kinds.** Capture and artifact bytes live
  behind different paths even though both end at `…/content`.
- **Pending vs produced.** A running recording or job has no bytes yet;
  `artifact_id`/`artifact_ids` appear only once produced.
- **Expiring bytes.** Every output carries `expires_at`; swept bytes are
  gone even while the record still exists, so "record present" does not
  imply "bytes retrievable".

## Chosen workflow: a typed `output_ref`

All three flows expose the same optional reference so clients retrieve
bytes uniformly without kind-specific path knowledge:

```yaml
output_ref:
  type: object
  required: [kind, id, content_url]
  properties:
    kind: {enum: [capture, artifact], type: string}
    id: {type: string}            # capture_id or artifact_id
    content_url: {type: string}   # the existing …/content route
```

- `output_ref.kind: "capture"` → `content_url` = `/api/v1/capture/{id}/content`
- `output_ref.kind: "artifact"` → `content_url` = `/api/v1/artifact/{id}/content`
- `output_ref: null` (or absent while pending) → not produced yet.

**Where it is attached:** `Capture` (itself), `Recording.artifact_ref`
(next to `artifact_id`, only when finalized), and job results next to
`artifact_ids` (`output_refs[]` for multi-artifact jobs). Existing fields
and routes stay untouched — `output_ref` is additive.

## Pending / missing / expired semantics

- `output_ref` absent or `null` → output not produced yet (running
  job/recording) or this record has no retrievable bytes.
- Record exists but bytes swept (past `expires_at`) → `GET …/content`
  returns `404` (`output_expired` where the implementation can tell);
  `output_ref` may still be present — `expires_at` on the record is the
  truth source for liveness.
- Record deleted → `404` on both show and content routes.
- `output_ref` never replaces lifecycle routes: list/show/delete keep
  working on `media`, `capture`, `artifact`, `recording` as today.
