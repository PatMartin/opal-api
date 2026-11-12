# OPAL Devices — Typer CLI Reference

**Status:** Proposed interface, not implemented. **Source of truth:** [`openapi/opal_device.yaml`](../openapi/opal_device.yaml), OpenAPI 3.1.0, contract v1.7.1 (OPAL SUITE STANDARD v1.2), which mounts the devices domain surface from [`openapi/shared/opal_device_kernel.yaml`](../openapi/shared/opal_device_kernel.yaml) and the standard route families from [`openapi/shared/opal_kernel.yaml`](../openapi/shared/opal_kernel.yaml). **CLI root:** `opal device` (also suitable as a standalone `opal-device` entry point).

This document follows the REST-first method used for the other OPAL services and the YOLO, RF-DETR, RT-DETR and D-FINE CLI designs. Every CLI leaf is mapped to an OpenAPI operation; examples describe target behavior, not commands that have been executed. Device management here means **identity, inventory, discovery, capabilities, preferred defaults and availability**, never taking over input/output streams, capturing audio, or scheduling GPU jobs.

## Architectural decisions (ratified)

| Decision | Ratified behavior |
|---|---|
| 12.1 | Optional registry; standalone consumers retain native device access |
| 12.2 | Audio, video and compute devices |
| 12.3 | Discovery/metadata only; consuming services operate devices |
| 12.4 | Independent registries with optional federation |
| 12.5 | Manual peers and mDNS; automatic peer discovery disabled by default |
| 12.6 | Stable UUIDs plus human-readable host-qualified names |
| 12.7 | Persistent inventory: available, unavailable, unknown, stale |
| 12.8 | Cached remote inventory + periodic refresh + on-demand sync |
| 12.9 | Registry holds capabilities/preferred defaults; consumers choose runtime configuration |
| 12.10 | Policy-based metadata sharing; open by default **to authenticated trusted peers** |
| 12.11 | Native SSE; optional opal-event publishing disabled by default |
| 12.12 | Built-in and third-party discovery backends share plugin interface |
| 12.13 | Common portable schema with namespaced extensible capabilities |
| 12.14 | Explicit, automatic and capability-based selection assistance |
| 12.15 | Static and dynamic groups (metadata-only) |
| 12.16 | Simple tags and structured key-value labels |
| 12.17 | YAML for human-authored config; SQLite for operational and federation cache |

## Complete Typer command tree

```text
opal device
├── info
│   ├── health
│   ├── live
│   ├── ready
│   ├── version
│   └── ping
├── catalog
├── list
├── add
├── show
├── update
├── remove
├── capabilities
├── status
├── test
├── discover
├── watch
├── event
│   └── list
├── default
│   ├── list
│   ├── set
│   └── remove
├── label
│   ├── list
│   ├── set
│   └── remove
├── tag
│   ├── list
│   ├── add
│   └── remove
├── group
│   ├── list
│   ├── add
│   ├── show
│   ├── update
│   ├── remove
│   └── member
│       ├── list
│       ├── add
│       └── remove
├── peer
│   ├── list
│   ├── add
│   ├── show
│   ├── update
│   ├── remove
│   ├── status
│   ├── sync
│   └── discover
├── sharing
│   ├── list
│   ├── add        (aliases: allow, deny)
│   └── remove
├── plugin
│   ├── list
│   ├── show
│   ├── enable
│   ├── disable
│   ├── test
│   └── discover
├── federation
│   ├── inventory
│   └── registry
├── config
│   ├── setting
│   │   ├── list
│   │   ├── show
│   │   ├── update
│   │   └── remove
│   └── profile
│       ├── list
│       ├── add
│       ├── show
│       ├── update
│       ├── remove
│       └── activate
├── backup
│   ├── list
│   ├── create
│   ├── download
│   ├── restore
│   ├── remove
│   ├── export
│   ├── import
│   └── validate
└── service
    ├── start
    ├── stop
    └── log
```

The `info`, `config`, `backup` and `service` subtrees are the standard OPAL kernel route families, spelled identically to the other suite services. The two `federation` commands are peer-facing diagnostic/admin clients, not ordinary application operations. `sharing allow` and `sharing deny` are aliases of `sharing add`; each calls the same policy-creation operation with a different `effect`. `peer sync` supports an optional peer argument: without one it synchronizes all trusted peers.

## Global CLI conventions

```bash
opal device --help
opal device --api-url http://127.0.0.1:8080 --output json list
opal device --token-env OPAL_DEVICES_TOKEN peer list
opal device --timeout 10 --output table list
```

Global options (CLI transport convention; not REST parameters): `--api-url`, `--token-env`, `--timeout`, `--output table|json|yaml`, `--verbose`. A host-qualified name such as `pi5/usb-mic` should be resolved by the CLI to a UUID before calling a device detail endpoint (or percent-encoded in the URL). JSON is default for piping; table may be the default for interactive shells.

Naming rules: hyphenated CLI flags, snake_case serialized JSON/YAML keys, verbs `list/add/show/update/remove`, read-only filtering via options, explicit identity for mutable operations. No mandatory access to `opal-event`, other OPAL services or a remote peer.

## Command ↔ REST operation matrix (complete)

Devices domain operations (mounted from `openapi/shared/opal_device_kernel.yaml`):

| CLI | Method | Path | operationId | Notes |
|---|---|---|---|---|
| `opal device catalog` | `GET` | `/api/v1/catalog` | `opal_devices_catalog_get` | Discover device types, discovery backends and event names |
| `opal device list` | `GET` | `/api/v1/device/` | `opal_devices_device_list` | List and filter local and federated device inventory |
| `opal device add` | `POST` | `/api/v1/device/` | `opal_devices_device_add` | Register user-managed device |
| `opal device show <device>` | `GET` | `/api/v1/device/{device_id}` | `opal_devices_device_get` | Show device metadata |
| `opal device update <device>` | `PATCH` | `/api/v1/device/{device_id}` | `opal_devices_device_update` | Update editable device metadata |
| `opal device remove <device>` | `DELETE` | `/api/v1/device/{device_id}` | `opal_devices_device_remove` | Remove registered device |
| `opal device capabilities <device>` | `GET` | `/api/v1/device/{device_id}/capabilities` | `opal_devices_device_capabilities` | Show device capabilities |
| `opal device status <device>` | `GET` | `/api/v1/device/{device_id}/status` | `opal_devices_device_status` | Show device availability |
| `opal device test <device>` | `POST` | `/api/v1/device/{device_id}/test` | `opal_devices_device_test` | Perform safe non-invasive checks |
| `opal device discover` | `POST` | `/api/v1/discovery/scan` | `opal_devices_discovery_scan` | Discover local devices without operating them |
| `opal device default list` | `GET` | `/api/v1/default/` | `opal_devices_default_list` | List preferred defaults |
| `opal device default set <scope> <target>` | `PUT` | `/api/v1/default/{scope}/{target}` | `opal_devices_default_set` | Set preferred defaults for device, type, host or global scope |
| `opal device default remove <scope> <target>` | `DELETE` | `/api/v1/default/{scope}/{target}` | `opal_devices_default_remove` | Remove preferred defaults |
| `opal device label list <device>` | `GET` | `/api/v1/device/{device_id}/label` | `opal_devices_label_list` | List device labels |
| `opal device label set <device> <key>` | `PUT` | `/api/v1/device/{device_id}/label/{key}` | `opal_devices_label_set` | Set key-value device label |
| `opal device label remove <device> <key>` | `DELETE` | `/api/v1/device/{device_id}/label/{key}` | `opal_devices_label_remove` | Remove device label |
| `opal device tag list <device>` | `GET` | `/api/v1/device/{device_id}/tag` | `opal_devices_tag_list` | List device tags |
| `opal device tag add <device> <tag>` | `POST` | `/api/v1/device/{device_id}/tag` | `opal_devices_tag_add` | Add device tag |
| `opal device tag remove <device> <tag>` | `DELETE` | `/api/v1/device/{device_id}/tag/{tag}` | `opal_devices_tag_remove` | Remove device tag |
| `opal device group list` | `GET` | `/api/v1/group/` | `opal_devices_group_list` | List device groups |
| `opal device group add` | `POST` | `/api/v1/group/` | `opal_devices_group_add` | Create static or dynamic group |
| `opal device group show <group>` | `GET` | `/api/v1/group/{group_id}` | `opal_devices_group_get` | Show group definition |
| `opal device group update <group>` | `PATCH` | `/api/v1/group/{group_id}` | `opal_devices_group_update` | Update group definition |
| `opal device group remove <group>` | `DELETE` | `/api/v1/group/{group_id}` | `opal_devices_group_remove` | Remove group |
| `opal device group member list <group>` | `GET` | `/api/v1/group/{group_id}/member` | `opal_devices_group_member_list` | List group members |
| `opal device group member add <group> <device>` | `PUT` | `/api/v1/group/{group_id}/member/{device_id}` | `opal_devices_group_member_add` | Add device to static group |
| `opal device group member remove <group> <device>` | `DELETE` | `/api/v1/group/{group_id}/member/{device_id}` | `opal_devices_group_member_remove` | Remove device from static group |
| `opal device peer list` | `GET` | `/api/v1/peer/` | `opal_devices_peer_list` | List federation peers |
| `opal device peer add` | `POST` | `/api/v1/peer/` | `opal_devices_peer_add` | Register an explicit peer |
| `opal device peer show <peer>` | `GET` | `/api/v1/peer/{peer_id}` | `opal_devices_peer_get` | Show peer |
| `opal device peer update <peer>` | `PATCH` | `/api/v1/peer/{peer_id}` | `opal_devices_peer_update` | Update peer metadata or trust |
| `opal device peer remove <peer>` | `DELETE` | `/api/v1/peer/{peer_id}` | `opal_devices_peer_remove` | Remove peer |
| `opal device peer status <peer>` | `GET` | `/api/v1/peer/{peer_id}/status` | `opal_devices_peer_status` | Check peer health and synchronization freshness |
| `opal device peer sync <peer>` | `POST` | `/api/v1/peer/{peer_id}/sync` | `opal_devices_peer_sync` | Refresh one peer cache now |
| `opal device peer sync` | `POST` | `/api/v1/peer/sync` | `opal_devices_peers_sync` | Refresh all trusted peer caches now |
| `opal device peer discover` | `POST` | `/api/v1/peer/discover` | `opal_devices_peers_discover` | Discover untrusted peer candidates using mDNS when enabled |
| `opal device sharing list` | `GET` | `/api/v1/sharing/policy/` | `opal_devices_sharing_policy_list` | List metadata visibility policies |
| `opal device sharing add` (aliases `allow`, `deny`) | `POST` | `/api/v1/sharing/policy/` | `opal_devices_sharing_policy_add` | Create allow or deny inventory visibility rule |
| `opal device sharing remove <policy_id>` | `DELETE` | `/api/v1/sharing/policy/{policy_id}` | `opal_devices_sharing_policy_remove` | Remove sharing policy |
| `opal device plugin list` | `GET` | `/api/v1/plugin/` | `opal_devices_plugin_list` | List installed discovery plugins |
| `opal device plugin show <plugin>` | `GET` | `/api/v1/plugin/{plugin_id}` | `opal_devices_plugin_get` | Show plugin metadata |
| `opal device plugin enable <plugin>` | `POST` | `/api/v1/plugin/{plugin_id}/enable` | `opal_devices_plugin_enable` | Enable an installed plugin |
| `opal device plugin disable <plugin>` | `POST` | `/api/v1/plugin/{plugin_id}/disable` | `opal_devices_plugin_disable` | Disable plugin |
| `opal device plugin test <plugin>` | `POST` | `/api/v1/plugin/{plugin_id}/test` | `opal_devices_plugin_test` | Test plugin requirements and discovery capability safely |
| `opal device plugin discover <plugin>` | `POST` | `/api/v1/plugin/{plugin_id}/discover` | `opal_devices_plugin_discover` | Discover local devices through one plugin |
| `opal device event list` | `GET` | `/api/v1/event/` | `opal_devices_event_list` | Browse recent device and peer event history |
| `opal device watch` | `GET` | `/api/v1/event/stream` | `opal_devices_event_stream` | Subscribe to native SSE device and peer events |
| `opal device federation inventory` | `GET` | `/api/v1/federation/inventory` | `opal_devices_federation_inventory` | Read filtered inventory as a trusted peer |
| `opal device federation registry` | `GET` | `/api/v1/federation/registry` | `opal_devices_federation_registry` | Read local registry identity and federation metadata |

Standard kernel route families (mounted from `openapi/shared/opal_kernel.yaml`):

| CLI | Method | Path | operationId | Notes |
|---|---|---|---|---|
| `opal device info health` | `GET` | `/api/v1/health/` | `opal_health_get` | Aggregate service health |
| `opal device info live` | `GET` | `/api/v1/health/live` | `opal_health_live_get` | Liveness probe |
| `opal device info ready` | `GET` | `/api/v1/health/ready` | `opal_health_ready_get` | Readiness probe |
| `opal device info version` | `GET` | `/api/v1/info/` | `opal_info_get` | Service identity and contract version |
| `opal device info ping` | `GET` | `/api/v1/info/ping` | `opal_info_ping` | Cheap reachability probe |
| `opal device config setting list` | `GET` | `/api/v1/setting/` | `opal_setting_list` | Whole setting map |
| `opal device config setting update` | `PATCH` | `/api/v1/setting/` | `opal_setting_patch` | Atomic multi-key update |
| `opal device config setting show <key>` | `GET` | `/api/v1/setting/{key}` | `opal_setting_get` | One setting key |
| `opal device config setting update <key>` | `PUT` | `/api/v1/setting/{key}` | `opal_setting_put` | Set one setting key |
| `opal device config setting remove <key>` | `DELETE` | `/api/v1/setting/{key}` | `opal_setting_delete` | Reset one key to its default |
| `opal device backup list` | `GET` | `/api/v1/backup/list` | `opal_backup_list` | List managed backups |
| `opal device backup create` | `POST` | `/api/v1/backup/create` | `opal_backup_create` | Snapshot configuration |
| `opal device backup download <fn>` | `GET` | `/api/v1/backup/download/{filename}` | `opal_backup_download` | Download a backup archive |
| `opal device backup restore <fn>` | `POST` | `/api/v1/backup/restore/{filename}` | `opal_backup_restore` | Restore a backup archive |
| `opal device backup remove <fn>` | `DELETE` | `/api/v1/backup/{filename}` | `opal_backup_delete` | Delete a backup archive |
| `opal device backup export` | `GET` | `/api/v1/backup/export` | `opal_backup_export` | Portable configuration export |
| `opal device backup import` | `POST` | `/api/v1/backup/import` | `opal_backup_import` | Import configuration |
| `opal device backup validate` | `POST`/`GET` | `/api/v1/backup/validate` | `opal_backup_validate` / `opal_backup_validate_stored` | Validate candidate or stored configuration |
| `opal device config profile list` | `GET` | `/api/v1/profile/` | `opal_profile_list` | List configuration profiles |
| `opal device config profile add` | `POST` | `/api/v1/profile/` | `opal_profile_create` | Create a profile |
| `opal device config profile show <id>` | `GET` | `/api/v1/profile/{profile_id}` | `opal_profile_get` | Show a profile |
| `opal device config profile update <id>` | `PATCH` | `/api/v1/profile/{profile_id}` | `opal_profile_patch` | Update a profile |
| `opal device config profile remove <id>` | `DELETE` | `/api/v1/profile/{profile_id}` | `opal_profile_delete` | Remove a profile |
| `opal device config profile activate <id>` | `POST` | `/api/v1/profile/{profile_id}/activate` | `opal_profile_activate` | Make one profile the only active profile |
| `opal device service start` | `POST` | `/api/v1/service/start` | `opal_service_start` | Start the service process |
| `opal device service stop` | `POST` | `/api/v1/service/stop` | `opal_service_stop` | Stop the service process |
| `opal device service log` | `GET` | `/api/v1/service/log` | `opal_service_log` | Tail service logs |

**Coverage:** 56 paths; 77 HTTP operations; 42 devices-domain schemas in the shared base plus kernel components; 18 API tags. The operation matrix enumerates every operation in the effective contract.

## Detailed command syntax and options

### Device inventory, catalog and discovery

```bash
opal device info health
opal device info version
opal device catalog
opal device list --type microphone --status available --host pi5
opal device list --type gpu --min-memory-mb 8192 --include-stale
opal device list --type microphone --capability 'audio.sample_rates contains 48000'
opal device list --label location=front-door --tag outdoor --refresh
opal device add front-door --host-id pi5 --host-name pi5 --type camera --backend onvif --access network --resource-uri rtsp://camera.local/live
opal device show pi5/front-door
opal device update pi5/front-door --description 'Outdoor front entrance camera'
opal device capabilities pi5/front-door
opal device status pi5/front-door
opal device test pi5/front-door
opal device discover --plugin alsa --dry-run
opal device remove pi5/front-door
```
`list` maps CLI filters to query parameters. `add` sends `DeviceCreate`; `update` sends `DevicePatch`. `--description` in the example is stored under `metadata.description`. `test` performs only safe availability checks and must not grab a camera or open an audio stream. `--refresh` may attempt federation sync and should report peer failures without failing the entire listing. Pagination uses `--limit` and `--cursor`.

### Preferred defaults

```bash
opal device default list
opal device default set device pi5/usb-mic --values '{"sample_rate":16000,"channels":1}'
opal device default set type speaker --values '{"preferred_backend":"alsa"}'
opal device default remove device pi5/usb-mic
```
The registry stores **preferences** in YAML; it does not reconfigure ALSA, PipeWire, V4L2 or CUDA. The `set` command sends a `Default` object to `PUT /api/v1/default/{scope}/{target}` with a strong `If-Match` precondition. The path target and body target must match. If a consuming service overrides a preferred default, that service is responsible for validating the operating settings against actual hardware.

### Labels and tags

```bash
opal device label list pi5/front-door
opal device label set pi5/front-door location front-door
opal device label remove pi5/front-door location
opal device tag list pi5/front-door
opal device tag add pi5/front-door outdoor
opal device tag remove pi5/front-door outdoor
```
Labels are key/value pairs; tags are simple strings. They are used in selectors but never grant hardware access. Only the owning registry may authoritatively edit a device's labels or tags; a remote registry shows federated copies read-only.

### Static and dynamic groups

```bash
opal device group add security-cameras --mode static
opal device group member add security-cameras pi5/front-door
opal device group member list security-cameras
opal device group member remove security-cameras pi5/front-door
opal device group add capable-gpus --mode dynamic --selector '{"type":"gpu","status":"available","capabilities":["compute.memory_mb>=8192"]}'
opal device group update capable-gpus --selector '{"type":"gpu","capabilities":["compute.memory_mb>=12288"]}'
opal device group show capable-gpus
opal device group list
opal device group remove capable-gpus
```
Dynamic membership is calculated from current local + cached federated inventory, never stored as an authoritative membership list. `member add/remove` applies to static groups only, returning HTTP 409 for a dynamic group. A dynamic group's `available` selector excludes `stale` items. Nested groups are out of scope.

### Federation peers and synchronization

```bash
opal device peer discover
opal device peer add gpu-server --url https://gpu-server.local:8080 --credential-ref secret://peers/gpu-server
opal device peer show gpu-server
opal device peer update gpu-server --trusted true
opal device peer status gpu-server
opal device peer sync gpu-server
opal device peer sync
opal device peer list
opal device peer remove gpu-server
opal device federation registry
opal device federation inventory --limit 100
```
`peer discover` uses mDNS only when explicitly enabled through settings; discovery results remain **untrusted candidates** until enrolled. `peer sync` refreshes cached inventories, and periodic sync intervals are configurable. A remote peer outage must not delete cached devices. The `federation` read operations require peer credentials — the same `BearerAuth` scheme as the management API, with trusted-peer status decided by enrollment and sharing policy. Non-loopback peer URLs must use TLS. The peer name is not proof of identity.

### Sharing policies: open borders within a trusted federation

```bash
opal device sharing list
opal device sharing deny --peer gpu-server --type microphone
opal device sharing deny --peer gpu-server --device pi5/office-mic
opal device sharing allow --peer gpu-server --type camera
opal device sharing remove 7df6a2d8-5dc6-4c4b-8eb8-ff7af8895a18
```
`sharing allow` and `sharing deny` are aliases of `sharing add` (`POST /api/v1/sharing/policy/`), differing only in `effect`. **Default:** `allow_trusted`. Deny has precedence over allow. These policies control **metadata visibility**, not permission to operate a device. Sensitive resource URIs, credentials, and secret references must be redacted for remote inventory clients. Untrusted/anonymous peers cannot read inventories.

### Discovery plugins

```bash
opal device plugin list
opal device plugin show alsa
opal device plugin enable alsa
opal device plugin test alsa
opal device plugin discover alsa
opal device plugin disable alsa
```
A built-in plugin and a third-party plugin implement the same Python discovery protocol; plugins may be loaded via package entry points (`opal_devices.discovery`). A plugin must advertise availability and refuse to run invasive hardware actions. Typical backends: ALSA, V4L2, CPU; optional PipeWire, ONVIF, CUDA, ROCm, OpenCL. Import errors from unavailable optional backends must degrade gracefully.

### Settings, event history and live watch

```bash
opal device config setting list
opal device config setting update federation.auto_discovery_enabled --value false
opal device config setting update federation.sync_interval_seconds --value 300
opal device config setting update events.publish_enabled --value true
opal device event list --event availability.changed --limit 100
opal device watch
opal device watch pi5/usb-mic --event availability.changed
opal device config setting remove events.publish_enabled
```
`config setting update` sends `{ "value": ... }` for the per-key `PUT` form where the value is parsed as JSON, and requires a strong `If-Match`. `config setting remove` resets one key to its declared default. `watch` opens `GET /api/v1/event/stream`, parses SSE `id/event/data` messages, reconnects with `Last-Event-ID`, and reports replay-window expiry instead of silently pretending events were not missed. Event publishing to `opal-event` is **optional and disabled by default**; failure to publish must never block inventory updates.

### Profiles, backups and service lifecycle

```bash
opal device config profile add field-kit --values '{"discovery.include_network":false}'
opal device config profile activate field-kit
opal device backup create
opal device backup export --output devices-config.tar.gz
opal device service log --lines 200
```
Profiles are named configuration snapshots shared with every OPAL service; exactly one may be active. Backup, export, import and validate cover the registry's portable configuration (YAML), never observed inventory, caches or secrets.

## REST request and response examples

### Register a microphone (POST /api/v1/device/)
```json
{
  "name": "usb-mic",
  "host_id": "pi5",
  "host_name": "pi5",
  "type": "microphone",
  "backend": "alsa",
  "access": "local",
  "resource_uri": "hw:2,0",
  "configuration": {
    "direction": "input"
  },
  "labels": {
    "room": "office"
  },
  "tags": [
    "speech"
  ]
}
```

### Example device record
```json
{
  "id": "8c2f3b91-5d42-4ab7-910e-a47f26d31105",
  "name": "usb-mic",
  "qualified_name": "pi5/usb-mic",
  "host_id": "pi5",
  "host_name": "pi5",
  "type": "microphone",
  "backend": "alsa",
  "status": "available",
  "access": "local",
  "capabilities": {
    "audio.sample_rates": [
      16000,
      44100,
      48000
    ],
    "audio.channels": [
      1,
      2
    ]
  },
  "labels": {
    "room": "office"
  },
  "tags": [
    "speech"
  ]
}
```

### Dynamic group request (POST /api/v1/group/)
```json
{
  "name": "capable-gpus",
  "mode": "dynamic",
  "selector": {
    "type": "gpu",
    "status": "available",
    "capabilities": [
      "compute.memory_mb>=8192"
    ]
  }
}
```

### Native SSE message
```text
id: 251
event: availability.changed
data: {"id":"251","event":"availability.changed","time":"2026-11-11T17:00:00Z","device_id":"8c2f3b91-5d42-4ab7-910e-a47f26d31105","data":{"old":"available","new":"stale"}}

```

## Integration examples: look, listen and say

```bash
# Registry discovery is optional for every consumer.
opal device list --type camera --status available
opal-look predict --source rtsp://camera.local/live

opal device list --type microphone --capability "audio.sample_rates contains 48000"
opal-listen listen --device auto

opal device list --type speaker --status available
opal-say speak "Hello world" --device pi5/usb-speaker
```

The `opal-look`, `opal-listen` and `opal-say` examples are **integration goals**, not confirmed commands from those services. They must remain usable with native device locators without installing or contacting `opal-device`. An inventory entry for a Pi USB microphone does not mean a separate GPU host can open the Pi-local ALSA device; federation shares metadata, not device access.

## Error handling, identity and trust

| HTTP status | CLI treatment |
|---|---|
| `401` | Missing/invalid credentials; do not retry anonymously |
| `403` | Authenticated but not permitted (untrusted peer or denied visibility) |
| `404` | Unknown device, group, peer, policy or plugin |
| `409` | Duplicate identity or unsupported operation for a dynamic group |
| `410` | SSE replay window expired; re-list current state |
| `412` | Stale `If-Match` ETag; re-read the resource and retry |
| `422` | Invalid flags, selector syntax, weak/wildcard ETag or disallowed setting |
| `428` | `If-Match` precondition missing on a configuration mutation |
| `503` | Unavailable backend/peer; retain last cached inventory where appropriate |

Device UUIDs are immutable registry identities; display names are changeable. Host-qualified names are for humans and can be ambiguous after host rename, so prefer UUIDs in persistent automation. Federation must not reveal unredacted secret-bearing URLs. Trust is explicit; mDNS presence is not sufficient. For local reads in a single-host setup, the implementation may support loopback-only unauthenticated use; network-facing APIs should require authentication and TLS.

## Storage and synchronization model

```text
config/
  devices.yaml       # human-created registrations/config
  defaults.yaml      # preferred settings
  peers.yaml         # known peers and trust; secret references only
  groups.yaml        # static memberships + dynamic selectors
  policies.yaml      # inventory visibility rules
data/
  devices.db         # observed inventory, status, cached remote snapshots
```

Each field has one authoritative owner. YAML is user-authored configuration; SQLite is observed/cache state. Remote registries publish snapshots through REST, not by sharing SQLite files. Periodic sync refreshes cached devices; manual sync is available. Device records persist across disconnection and transition through `available`, `unavailable`, `unknown`, and `stale`.

## Proposed CLI implementation approach

1. Parse and validate `openapi/opal_device.yaml` (with `openapi/shared/opal_device_kernel.yaml` and `openapi/shared/opal_kernel.yaml` refs resolved, e.g. via `redocly bundle`) and generate a typed API client with stable `operationId` methods.
2. Implement Typer command groups from the matrix; keep command handlers as thin client wrappers.
3. Create schema validation and consistent error translation. Do not bury non-contract requests in the CLI.
4. Implement core local inventory/discovery with YAML + SQLite and plugin-based backends.
5. Add optional peer federation, identity, trust, redaction and hybrid sync.
6. Add native SSE watching and optional outbound `opal-event` integration behind a disabled-by-default setting.
7. Test the CLI against a mock REST server and actual service implementation; keep built-in plugins safe to probe.

### Contract-to-CLI conformance checks

- [ ] Every OpenAPI `operationId` appears exactly once in the CLI operation matrix.
- [ ] All CLI leaf commands map to a documented HTTP operation.
- [ ] `--help` exists for every command and documents flags/argument types.
- [ ] All write request bodies validate against OpenAPI schemas.
- [ ] Device IDs and host-qualified aliases resolve consistently.
- [ ] Unsupported capability selectors return actionable 422 responses, not empty results.
- [ ] Offline peers preserve cached inventory, with `stale` status and timestamps.
- [ ] mDNS discovery never auto-trusts peers.
- [ ] Deny policies override open-to-trusted defaults.
- [ ] Device test/discovery never captures audio/video or runs accelerator tasks.
- [ ] Services function without registry or federation.
- [ ] SSE resume, reconnect, optional outbound publication and failure isolation are exercised.
- [ ] YAML/SQLite ownership is tested on restart and migration.

## Items intentionally not included

No device locks/reservations, no capturing video or audio, no synthesized speech playback, no device stream forwarding, no GPU job scheduling, no RTSP proxying, no arbitrary remote shell commands, and no mandatory `opal-event` or OPAL kernel integration. These belong to consuming services or future separate components.

## References

- OpenAPI 3.1: https://spec.openapis.org/oas/v3.1.0
- Python packaging entry points: https://packaging.python.org/en/latest/specifications/entry-points/
- Python plugin discovery: https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
- Typer: https://typer.tiangolo.com/
