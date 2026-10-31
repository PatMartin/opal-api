# opal-api

Published OpenAPI 3.1 contracts for the OPAL suite, one file per service in
[`openapi/`](openapi/):

| File | Service |
| --- | --- |
| `openapi/opal_event.yaml` | Opal Event API |
| `openapi/opal_listen.yaml` | Opal Listen (voice intent) API |
| `openapi/opal_talk.yaml` | OPAL Talk API |
| `openapi/opal_look.yaml` | OPAL Look (vision) API |

## Validating the contracts

All checks run on every pull request and push to `main` via
[`.github/workflows/openapi-validate.yml`](.github/workflows/openapi-validate.yml).

### Prerequisites

- Node.js 20+ (CI uses Node 22)
- `npm ci` to install the pinned tool versions

### Commands

```bash
npm run validate    # structural validation + $ref resolution of every file
                    # in openapi/ (Redocly CLI, redocly.yaml)
npm run lint        # generic OpenAPI lint rules (Spectral, .spectral.yaml)
npm run lint:opal   # OPAL suite conventions (Spectral, .spectral.opal.yaml)
npm run lint:look    # OPAL Look-specific contract guarantees (.spectral.opal.look.yaml)
npm run test:lint    # regression fixtures proving the rules fire (tests/test_lint.py)
npm run check       # all of the above, same as CI
```

### What is checked

- OpenAPI 3.1 parsing and structural validity (Redocly `recommended` ruleset)
- Local `$ref` resolution (both tools fail on unresolved references; there are
  no external `$ref`s today)
- Duplicate `operationId`s (`operation-operationId-unique`)
- Path/parameter consistency (`path-params`, `operation-parameters-*`)
- Invalid examples and response schemas (`oas3-valid-*-example`,
  `oas3-schema`)
- Every file under `openapi/` — the glob `"openapi/*.yaml"` covers all
  published contracts; add new contracts there and they are checked
  automatically

### Ruleset layout

| File | Purpose |
| --- | --- |
| `redocly.yaml` | Generic structural validation. Two rules are disabled because they contradict documented OPAL conventions (`no-path-trailing-slash`) or are intentionally deferred (`security-defined`). |
| `.spectral.yaml` | Generic Spectral `oas` recommended rules. |
| `.spectral.opal.yaml` | OPAL suite conventions only (error correlation headers, standard error body, request context parameters, ETag/precondition declarations, 201 Location, item-op 404s, event-envelope compatibility). Keep OPAL-specific rules here, not in the generic ruleset. |
| `.spectral.opal.look.yaml` | Look-scoped guarantees: mandatory If-Match on configuration mutations, cursor-page structure (items/next_cursor/has_more), status+ready probe bodies on 200 and 503, and BusEvent keeping correlation metadata optional inside data.metadata. Separate file because these rules apply to Look paths only. |

Spectral fails the build on `error` severity; `warn`-level findings are
reported but non-blocking.
