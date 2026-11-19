# Shared service lifecycle surface — kernel-owned `service` group

Every published runnable OPAL module — including standalone engines such as
opal-look-yolo — mounts the same three lifecycle operations from the kernel
(`openapi/shared/opal_kernel.yaml`, `components.pathItems`):

| CLI | HTTP | Operation ID | Kernel Path Item |
| --- | --- | --- | --- |
| `service start [--append]` | `POST /api/v1/service/start` | `opal_service_start` | `service_start` |
| `service stop` | `POST /api/v1/service/stop` | `opal_service_stop` | `service_stop` |
| `service log [--lines N]` | `GET /api/v1/service/log` | `opal_service_log` | `service_log` |

Module sources mount each path as a bare `$ref`; the `x-opal-cli` descriptors
(with `--append` → body `append`, `--lines` → query `lines`) live on the kernel
operations and are the single source of truth.

## Behavior contract

- `start` launches the managed server in the background, terminates and
  replaces an already-running managed instance (`previous_pid` reports the
  replaced process), and overwrites `logs/opal_<service>.log` unless
  `append: true` is sent (`--append`).
- `stop` succeeds when the managed server is already stopped.
- `log --lines N` returns up to N trailing lines, oldest first; `lines` is a
  query parameter bounded 1–1000 with default 10. Response:
  `OpalServiceLogTail`.
- Responses: `OpalServiceStatus` (`state`, `pid`, `previous_pid`, `log_file`)
  for start/stop; standard 401/403/422 plus 500 (lifecycle ops) or 404 (log
  file absent); correlation headers on all responses.
- Readiness after launch is reported by `GET /api/v1/health/ready`, not by
  `start` itself.

## Adopter obligations

- **Runtimes** (all six modules): implement `opal_service_start`,
  `opal_service_stop`, `opal_service_log` per the behavior contract — managed
  process supervision, append/replace log semantics, idempotent stop, bounded
  tail with the documented parameter bounds.
- **LOOK-YOLO specifically**: this contract is newly mounted on the engine
  spec. Its runtime previously had no service endpoints; it must add handlers
  for all three operations and emit the `service` tag surface, or mount the
  shared supervisor implementation used by the other services.
- **CLI**: generate `service start` (with `--append`), `service stop`, and
  `service log` (with `--lines`) from the kernel bindings for every module,
  yolo included. Local cold-start and launch options stay on each module's
  existing *local* CLI path — apply local fallback only when the target is
  explicitly local; the `service` group always targets the managed remote
  process.
- **SPA/clients**: poll `GET /api/v1/health/ready` after `service start`
  rather than assuming the 200 response means serving.
