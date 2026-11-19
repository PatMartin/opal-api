# Info surface consolidation — `GET /api/v1/health/` is the single report

All OPAL modules now expose **one** service information surface: `GET /api/v1/health/`,
operation `opal_health_get`, mounted from the kernel Path Item `health`
(`openapi/shared/opal_kernel.yaml`). The CLI binds it as the only `info`
command: `opal <module> info health`.

## Retired routes and commands

| Removed | Replacement |
| --- | --- |
| `GET /api/v1/info/` (ServiceInfo) | `GET /api/v1/health/` — `name`, `version`, `api_version` |
| `GET /api/v1/info/ping` (LivenessRead) | `GET /api/v1/health/live` (machine probe) or `live` in the report |
| `GET /api/v1/stats/` (opal-event) | `details.stats` in the health report |
| `GET /api/v1/health/audio_devices` (opal-listen) | `details.audio_devices` in the health report |
| `opal <m> info version` / `info show` / `info get` | `opal <m> info health` — `name`, `version`, `api_version` fields |
| `opal <m> info ping` | `GET /api/v1/health/live` (HTTP-only) or `.live` field |
| `opal <m> info live`, `info health --live` | `GET /api/v1/health/live` (HTTP-only) or `.live` field |
| `opal <m> info ready`, `info health --ready` | `GET /api/v1/health/ready` (HTTP-only) or `.ready` field |
| `opal <m> info stats` (event) | `opal event info health` — `.details.stats` |
| `opal <m> info audio-devices` (listen) | `opal listen info health` — `.details.audio_devices` |

`GET /api/v1/health/live` and `GET /api/v1/health/ready` are preserved as
HTTP-only machine probes (`OpalHealthProbe` = `status` + `ready`, 200/503).
`/health/live` is the documented replacement for machine callers of
`/info/ping`.

## Normalized report

`OpalHealthReport` (kernel) requires `name`, `version`, `api_version`,
`status`, `live`, `ready`, `details`. Overall `status` is `ok` | `degraded` |
`error`. HTTP 200 whenever a report is available — including `ready: false`;
the standard 503 `OpalError` applies only when no report can be produced.

Module-specific diagnostics live in `details` and are declared per module via
`x-opal-health-details.members` (schema refs): opal-event `stats` (`Stats`),
opal-listen `audio_devices` (`AudioDevice[]`), opal-look/think/say/yolo declare
their existing diagnostics members. Named response examples on the health Path
Item cover healthy, live-but-unready, event counters, listen audio devices, and
minimal reports.

## Adopter obligations

- **Runtimes**: implement `opal_health_get` returning the normalized shape;
  map former ServiceInfo fields into `name`/`version`/`api_version`; map
  former stats/audio_devices payloads into `details`; keep 200-vs-503 rule;
  drop the four retired routes.
- **CLI**: generate only `info health`; remove the legacy commands and
  `--live`/`--ready` selectors; machine monitoring moves to the HTTP probes.
- **SPA/clients**: poll `GET /api/v1/health/` (or `/health/live`,
  `/health/ready` for probes); read `details.<member>` per
  `x-opal-health-details`; treat `status == "degraded"` and `ready == false`
  as reportable states, not transport errors.

Version: modules `3.x` → `4.0.0`; opal-look-yolo `3.0.0-mvp-plus` →
`4.0.0-mvp-plus`.
