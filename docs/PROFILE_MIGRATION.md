# Profile model migration: flat union → namespaced compartments (v3.0.0)

Authorized breaking contract migration with a clean cutover. There is no wire
compatibility layer: `2.0.0` flat profile fields are replaced everywhere by the
namespaced document, and runtime implementations convert stored flat records
deterministically on migration (below).

## What changed

| Area | v2.x | v3.0.0 |
| --- | --- | --- |
| Profile shape | One open object unioning every service's fields | Closed envelope `{id, name, description, is_active, created_at, updated_at, shared, modules}` |
| Operational fields | Top-level on the profile | Inside `modules.<module-id>` compartments; each module's fields declared by its own closed schema in `openapi/shared/opal_profiles.yaml` |
| Ownership declaration | `x-opal-profile-fields` (flat field list per service) | `x-opal-profile-namespace` (compartment key + schema refs) |
| Field defaults on create | JSON Schema `default:` annotations stored literal values | Every compartment field is an optional override; omission means *inherit* (shared → service default). No create-time defaults inside compartments |
| Engine coverage | `opal-look-yolo` had no profile surface | Same six profile operations mounted as every runtime module; explicit empty `opal-look-yolo` compartment |
| Versions | kernel + services `2.0.0`, yolo `2.1.0-mvp-plus` | kernel + services `3.0.0`, yolo `3.0.0-mvp-plus` |

The compartment catalog (`OpalProfileModules`) is keyed by canonical module
identity (`x-opal-snapshot.module`): `opal-event`, `opal-listen`, `opal-look`,
`opal-look-yolo`, `opal-say`, `opal-think`. All six are registered — modules with
no profile-specific defaults use an explicit empty closed schema
(`additionalProperties: false`), so their compartment exists, validates, and
round-trips without silently accepting fields.

## Old field → new path

| v2 flat field | v3 path | Owner / status |
| --- | --- | --- |
| `id` | `id` | Envelope (readOnly on records) |
| `name` | `name` | Envelope |
| `description` | `description` | Envelope |
| `is_active` | `is_active` | Envelope; local projection of the receiving service's selection |
| `created_at` / `updated_at` | same | Envelope (readOnly) |
| `voice_id` | `modules["opal-say"].voice_id` | opal-say |
| `speed` | `modules["opal-say"].speed` | opal-say (0.25–4.0) |
| `volume` | `modules["opal-say"].volume` | opal-say (0.0–2.0) |
| `output_format` | `modules["opal-say"].output_format` | opal-say |
| `sample_rate` | `modules["opal-say"].sample_rate` | opal-say (8000–192000 or null = service chooses) |
| `engine_options` | `modules["opal-say"].engine_options` | opal-say |
| `wakeword_names` | `modules["opal-listen"].wakeword_names` | opal-listen |
| `confidence_thresholds` | `modules["opal-listen"].confidence_thresholds` | opal-listen |
| `vad_settings` | `modules["opal-listen"].vad_settings` | opal-listen |
| `enabled_intents` | `modules["opal-listen"].enabled_intents` | opal-listen |
| `enabled_slots` | `modules["opal-listen"].enabled_slots` | opal-listen |
| `model_paths` | `modules["opal-listen"].model_paths` | opal-listen |
| `pipeline_id` | — | **Unowned, dropped.** No module's `x-opal-profile-fields` declared it; ambiguous ownership reported rather than guessed. Persisted flat values are lost unless a service claims them — flag at migration time. |
| `inference` | — | **Unowned, dropped.** Same as above. |
| `retention` | — | **Unowned, dropped.** Same as above. |

Deterministic conversion for stored v2 records: copy each declared flat field
into its owning compartment, preserve `id`/`name`/`description`/`is_active`
and timestamps, normalize missing `shared`/`modules` to `{}`. If a stored
record contains an unowned field (`pipeline_id`, `inference`, `retention`) the
migration MUST report it explicitly — name the field and the profile — rather
than silently dropping or guessing an owner. If two candidate owners could
claim a field (not possible with the current field set), the migration MUST
report the collision and refuse to pick.

## Resolution precedence

Per field, highest first:

```text
explicit request field > persona binding > selected profile's module override
> selected profile's shared value > service default
```

The selected profile is the explicitly named `profile_id` when present, else
the active profile when one exists. "Service default" keeps the existing
environment > dotenv > persisted > registered-default precedence wherever those
layers already form a setting's effective value. Profile values supply defaults
for supported operation inputs; a field omitted at every level falls to the
service default. Explicit `null` behaves per the field's own schema (e.g.
`modules["opal-say"].sample_rate: null` means "the service chooses"; a nullable
persona `voice_id` is an absent binding).

`shared` currently declares no fields — no current contract field has the same
meaning across multiple modules. A field is promoted to `shared` only when two
or more module contracts already accept it with identical name, type and
semantics; the promotion records consumers, units, accepted values and the
module-override mapping here.

## Local storage, selection and ownership

- Each service stores its own local profile records — the complete document
  including compartments it does not honor. Copying or loading a document
  transfers an explicit snapshot into that service's local configuration;
  edits then affect only the receiving service's record. Propagating to
  another service requires explicitly transferring the updated configuration
  (config save on the source, config load on the target).
- Active selection is local runtime/configuration state: at most one active
  profile per service; an empty local catalog is legal. `is_active` on
  responses is a local projection, not portable payload; it is stored so
  config save/load restores the selection coherently.
- On selection, the service applies `shared` plus its own compartment;
  missing compartments contribute no overrides.
- Profile edits apply to newly admitted work; already-admitted work keeps the
  values it resolved at admission, consistent with existing lifecycle
  guarantees.
- Deleting a local record deletes that service's copy only.

## Update semantics

`PATCH /api/v1/profile/{profile_id}` with `OpalProfilePatch`:

- Omitted properties stay unchanged (`minProperties: 1`).
- A supplied `modules.<key>` merges field-wise over the stored compartment;
  sibling fields and all other compartments are preserved. Arrays replace as
  whole values.
- `modules` may contain only the receiving service's own compartment key;
  attempting another module's compartment is rejected `422` and its stored
  contents are preserved. (Schema-level: all declared keys validate; the
  own-compartment restriction is a runtime rule.)
- Explicit `null` on a compartment field removes that override and restores
  inheritance — distinct from `null` values a field declares as meaningful
  (`sample_rate` treats both identically). `null` on a non-nullable field or
  on a compartment itself is rejected.
- Mutations are atomic: nothing partial persists; If-Match/412/428 and the
  OpalError envelope apply as elsewhere.

## Validation and portability

- `shared` and every declared compartment validate structurally against the
  closed `opal_profiles.yaml` schemas (misspelled fields in a recognized
  compartment are rejected).
- The receiving service additionally validates its own compartment's local
  references semantically (e.g. opal-say checks `voice_id` resolvability).
  Foreign voice/model/pipeline references are portable references — they are
  not resolvable by non-owning services and are not a validation error.
- Compartments for unrecognized module ids may carry any well-formed object;
  they are preserved verbatim through reads, own-compartment edits, and
  config save/load, and reported as *unverified* where a reporting surface
  exists.

## CLI mapping

Uniform subtree everywhere: `opal <service> profile
list|add|show|update|remove|activate`. Per-method `x-opal-cli` descriptors are
declared on each mount. Structured compartment input uses the established
file conventions (`local_in`, `yaml_or_json_file`):

| New option | Replaces (v2) | Binds |
| --- | --- | --- |
| `--in FILE` | — | whole request body (portable document / patch document) |
| `--name NAME`, `--description TEXT`, `--is-active/--no-is-active` | same | body fields |
| `--shared FILE` | — | `shared` object |
| `--module FILE` | per-field flags (`--voice-id`, `--speed`, `--wakeword-names`, …) | `modules.<own>` compartment; partial merges preserve unmentioned compartments |

CLI partial edits (`profile update --module partial.yaml`) send a patch
document; the service merges it, so compartments the file never mentions are
preserved.

## Snapshot integration

`resources.profiles` in each module's config snapshot carries complete
namespaced profile documents — all stored compartments plus the `is_active`
local selection — and foreign compartments are preserved verbatim through
save/load. `opal-look-yolo` gained the `profiles` section. Secret handling and
provenance rules are unchanged.

## Runtime implementation obligations (affected consumers)

| Consumer | Required work |
| --- | --- |
| Every OPAL service runtime | Store full namespaced documents; read `shared` + own compartment only; preserve foreign compartments byte-for-byte; implement merge+null-removal patch semantics; reject foreign-compartment edits 422; keep ≤1 local active profile; migrate stored flat records per the table above and report unowned-field drops and ownership collisions explicitly |
| opal-say | Semantic `voice_id` resolvability on its compartment; engine_options shallow-merge unchanged |
| opal-listen | Semantic validation of wakeword/intent/slot references in its compartment |
| opal-look-yolo | New profile CRUD + activation surface (kernel-mounted contract); empty compartment accepted |
| CLIs (`opal <service>`) | Implement `--in/--shared/--module` local_in parsing (YAML/JSON by extension); keep implicit If-Match fetch |
| Snapshot tooling | Round-trip `resources.profiles` including foreign compartments and `is_active` |
| External clients | Rewrite flat payloads to namespaced documents; consume `modules.<service>` for defaults |

## Superseded contract assertions

`x-opal-profile-fields` is retired; open-union profile schemas
(`additionalProperties: true` with the flat field list) are replaced by the
closed envelope — the documented exception to the kernel's open-union
convention. Test assertions pinning `info.version` to `2.0.0` were updated to
`3.0.0` for this requirement change.
