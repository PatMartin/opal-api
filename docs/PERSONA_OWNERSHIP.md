# OPAL Persona Ownership and Resolution

Status: accepted. Contract work: `extract shared persona identity components`,
`publish portable OPAL persona contract`; implementation work lands per service.

## Decision

**OPAL Think is the authoritative persona writer.** When OPAL services are
deployed together, the persona registry hosted by OPAL Think at
`GET/POST /api/v1/persona/` is canonical: cross-service personas are authored
there once and consumed by reference everywhere else.

Two facts make Think the right owner rather than any other service:

- A persona is an *identity with service bindings*. Think is the service whose
  binding surface is richest (model selection plus instructions/settings) and
  the one a standalone suite always runs.
- Say's persona surface is a voice-binding convenience, not an identity
  registry — its `PersonaCreate` cannot even express a persona without a
  `voice_id`, so it cannot host personas that have no voice.

**Every service can still define personas locally.** The kernel carries the
shared persona identity schema and CRUD path items, so a standalone service
keeps full local CRUD and works with no other service running. "Authoritative"
only matters when a consumer is configured to reach Think (see Sync below):
on conflict between a local record and the owner record for the same
`persona_id`, **the owner record wins**.

## Model

A persona has a kernel-owned **identity** and zero or more
**service bindings**:

| part | fields | owner |
|---|---|---|
| identity | `persona_id`, `name`, `description`, `enabled`, `created_at`, `updated_at` | kernel (authoritative copy at Think) |
| Say binding | `voice_id` | field shared; **value validated by OPAL Say** |
| Think binding | model / instructions settings (service-local fields) | OPAL Think |
| other consumers | reference `persona` / `persona_id` only | kernel |

`voice_id` lives on the shared identity shape because multiple services
reference it, but it is a *binding*, not part of identity: OPAL Say requires it
(`voice_id` is required on Say `PersonaCreate`), everyone else treats it as an
optional, nullable cross-service reference they do not validate.

## Resolution order

When a request names a persona, each service resolves fields it needs in this
order — first match wins, independently per field:

1. **Explicit request field** — always wins (e.g. `voice_id` on a Say request).
2. **Persona binding** — the field the persona supplies for that service
   (Say: `voice_id`; Think: model/instructions settings).
3. **Profile** — the caller's or active profile's settings.
4. **Service default** — built-in defaults.

## Standalone obtain / refresh

A consumer resolves `persona: <id>` like this:

1. Look up `<id>` in the local persona store.
2. If absent and `persona.owner_url` is configured, fetch
   `GET {owner_url}/api/v1/persona/<id>` from OPAL Think, store it marked
   `origin: owner`, and cache it with its ETag for refresh
   (`If-None-Match` revalidation on use, or on a TTL per service settings).
3. If absent everywhere → `404`/`422` unknown persona at use time; persona is
   never silently invented.

Local personas created without an owner are `origin: local` and continue to
work standalone. When `owner_url` is configured, owner records shadow local
records for the same `persona_id` (local record retained, not deleted).

## Validation ownership

- **Identity shape** (id pattern, name/description bounds, `enabled`): kernel
  schema — every service enforces it identically.
- **Binding resolvability**: each service validates only the binding it
  consumes. Say checks `voice_id` resolves to a registered voice; Think checks
  its model/instructions binding resolves; other consumers check nothing.
- `POST /api/v1/persona/{persona_id}/validate` therefore reports *that
  service's* binding resolvability — it is not a suite-wide verdict.

## Missing or invalid bindings

- Persona resolves but its binding target is gone (e.g. voice deleted in Say):
  use of the persona fails `422` (`persona_binding_unresolvable`);
  `/validate` reports the broken binding without deleting the persona record.
- Persona record absent → `404` on read, `422` when referenced by a request.
- `enabled: false` → `422`/`409` on use (`persona_disabled`); the record and
  its bindings remain readable.

## Worked example: `amy`

Authored once at Think:

```yaml
persona_id: amy
name: Amy
description: Ops assistant persona.
enabled: true
voice_id: en-gb-alan-low        # Say binding
# Think-local binding fields (model + instructions) live in Think's record.
```

- `POST /api/v1/task/ {persona: "amy"}` on Think → resolves model +
  instructions from the persona; explicit `model_id` in the request would win.
- `POST /api/v1/generate {persona: "amy"}` on Say → resolves
  `voice_id: en-gb-alan-low`; explicit `voice_id` in the request wins;
  profile then service defaults fill the rest.
- A standalone Look with no `owner_url` uses only its local `amy` record.

## Migration from service-local CRUD

Additive — no route removal:

1. Kernel gains the shared persona identity components (P12) and the portable
   contract (P13); service schemas $ref them, wire-identical where they
   already agree.
2. Existing `/api/v1/persona/` CRUD stays callable on every service. Services
   deployed together mark it non-authoritative for `persona_id`s that exist at
   the owner; contract docs note the precedence.
3. `origin` (`local`|`owner`) is additive metadata; existing records migrate
   in place — nothing needs re-creation. Say keeps requiring `voice_id`
   (service-local constraint, unchanged).
4. Removal of duplicated writes, if ever wanted, is a separate future
   deprecation — not part of this contract.
