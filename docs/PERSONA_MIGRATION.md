# Shared persona surface — kernel-owned `persona` group

Every published runnable OPAL module — now including opal-look and
opal-look-yolo — mounts the same three Path Items from the kernel
(`openapi/shared/opal_kernel.yaml`):

| CLI under the module | HTTP | Operation ID | Kernel Path Item |
| --- | --- | --- | --- |
| `persona list` | `GET /api/v1/persona/` | `opal_persona_list` | `persona_collection` |
| `persona add` | `POST /api/v1/persona/` | `opal_persona_create` | `persona_collection` |
| `persona show` | `GET /api/v1/persona/{persona_id}` | `opal_persona_get` | `persona_item` |
| `persona update` | `PATCH /api/v1/persona/{persona_id}` | `opal_persona_patch` | `persona_item` |
| `persona remove` | `DELETE /api/v1/persona/{persona_id}` | `opal_persona_delete` | `persona_item` |
| `persona validate` | `POST /api/v1/persona/{persona_id}/validate` | `opal_persona_validate` | `persona_validate` |

Module sources mount each path as a bare `$ref`; the `x-opal-cli` descriptors
(`--enabled/--no-enabled`, `--if-match`, `--persona-id`, `--name`,
`--description`, `--voice-id`) live on the kernel operations.

## Behavior contract (unchanged)

- Bounded complete list, optional `enabled` query filter (omission =
  unfiltered; `--no-enabled` sends `enabled=false`), strong ETag on reads.
- `201` + `Location` on create; bodyless `204` on delete; partial PATCH
  (`OpalPersonaUpdate`, minProperties 1, null clears nullable fields).
- Strong `If-Match` mandatory on create/update/delete: `428` missing,
  `412` stale, atomic rejection. `409` duplicate `persona_id` on create;
  `404` on item ops and create's unresolvable binding (e.g. SAY's
  unregistered `voice_id` — modules without resolvable bindings treat the
  reference as opaque); PATCH `409` for conflicting updates (published by
  SAY).
- `persona validate` is read-only and service-local → `OpalValidationReport`;
  each service validates the bindings it understands (SAY voice/engine
  compatibility, THINK model/instruction bindings, LOOK/YOLO identity and
  enabled state), foreign bindings are opaque.
- Ownership semantics unchanged per `x-opal-persona`: OPAL Think hosts the
  authoritative registry; every module keeps local CRUD; configured owner
  wins on conflict with ETag revalidation; resolution order
  `explicit > persona binding > profile module override > shared > default`.

## What changed per contract

- **event, listen, say, think**: inline ops and local `Persona*` schema
  aliases removed; routes are now bare kernel `$ref`s. Event/listen/say gain
  spec-declared `x-opal-cli` for the first time (previously † cookbook-only);
  think's descriptors gain the documented flag bindings.
- **look, look-yolo**: new mounts + `persona` tag + `personas` in
  `x-opal-snapshot.resources` so local records round-trip through
  config save/load (snapshots without a `personas` section still load under
  existing omission rules). LOOK's MVP Plus scope now reads: persona support
  is limited to the shared management surface with identity/enabled
  validation; look-specific persona bindings remain out of scope.
- **Versions**: `4.0.0` → `5.0.0`; `4.0.0-mvp-plus` → `5.0.0-mvp-plus`.

## Downstream implementation obligations

- **LOOK / LOOK-YOLO runtimes**: must implement all six handlers — persona
  persistence, catalog CRUD, `enabled` filter, If-Match revision tracking,
  `personas` section in config snapshot save/load, and identity+enabled
  validation for `persona validate`. Previously they had none.
- **event, listen, say, think runtimes**: no new semantics — verify the
  unified responses: SAY's create-404/patch-409 now exist on every module's
  contract (services without resolvable bindings simply never emit them).
- **CLI**: generate `persona list|add|validate|show|update|remove` with the
  kernel bindings on all six modules, including look/yolo. Flags:
  `--enabled/--no-enabled` (list), `--if-match/--persona-id/--name/
  --description/--voice-id/--enabled/--no-enabled` (add/update),
  `<persona_id>` positional on item verbs.
- **SPA/clients**: persona management now exists on every module including
  engines; `404` on create signals an unresolvable binding, not a missing
  route.
