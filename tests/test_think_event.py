"""Contract-level interoperability tests for OPAL Think <-> EVENT v1.5.0.

Verifies the THINK principal's declared integration surface against the
versioned EVENT contract's authorization model and action schemas — without
requiring a running service.
"""
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_util  # noqa: E402
THINK = os.path.join(ROOT, "openapi", "opal_think.yaml")
EVENT = os.path.join(ROOT, "openapi", "opal_event.yaml")

failures = 0


def check(ok, name, detail=""):
    global failures
    print(("PASS" if ok else "FAIL"), name, detail if detail else "")
    failures += 0 if ok else 1


def main():
    think = spec_util.load(THINK)
    event = spec_util.load(EVENT)
    integ = think.get("x-opal-event-integration", {})
    auth = event.get("x-opal-authorization", {})

    # THINK principal: exactly the declared scopes, no more
    think_scopes = auth["principals"]["think"]["scopes"]
    think_denied = auth["principals"]["think"]["denied"]
    check(sorted(integ["required_event_permissions"]) == sorted(think_scopes),
          "THINK declares exactly its principal's scopes")
    check(sorted(integ["forbidden_event_permissions"]) == sorted(think_denied),
          "THINK declares exactly its principal's denied scopes")

    # Every permission THINK uses is granted; none of its denied scopes appear.
    req = set(integ["required_event_permissions"])
    fb = set(integ["forbidden_event_permissions"])
    check(req <= set(think_scopes) and not (fb & set(think_scopes)),
          "THINK never needs a denied scope")
    check(fb <= set(think_denied), "THINK's denied set is a subset of EVENT's denials")

    # THINK's integration routes map to real EVENT endpoints + scopes.
    scope_routes = {scope: set(body.get("permits", []))
                    for scope, body in auth["scopes"].items()}
    for key, route in (
        ("actions_discovery", "GET /api/v1/actions/"),
        ("action_lookup", "GET /api/v1/actions/{action_id}"),
        ("execute", "POST /api/v1/actions/{action_id}/execute"),
        ("execution_read", "GET /api/v1/executions/{execution_id}"),
    ):
        declared = integ.get(key, "")
        check(declared == route or (key == "actions_discovery" and
              declared in ("GET /api/v1/actions/", "GET /api/v1/actions/{action_id}")),
              f"{key}: route declared")
        owning = [s for s, rts in scope_routes.items() if route in rts]
        check(len(owning) == 1 and owning[0] in think_scopes,
              f"{key}: covered by a THINK scope ({owning})")

    # EVENT is the execution + authorization authority; 202 = admission only.
    ex = event["paths"]["/api/v1/actions/{action_id}/execute"]["post"]
    check("202" in ex["responses"] and "200" not in ex["responses"],
          "execute admits via 202, never 200 (admission != execution)")
    check("422" in ex["responses"], "execute can synchronously reject invalid input (422)")

    # Terminal vs non-terminal execution statuses are distinct.
    statuses = set(event["components"]["schemas"]["Execution"]["properties"]["status"]["enum"])
    check(statuses == {"queued", "running", "succeeded", "failed", "timed_out", "dropped"},
          "Execution.status has all six distinct outcomes")
    terminal = {"succeeded", "failed", "timed_out", "dropped"}
    check(terminal <= statuses and not (terminal & {"queued", "running"}),
          "terminal statuses distinct from in-flight")

    # Correlation headers propagate on the ops THINK calls.
    for route_op in (event["paths"]["/api/v1/actions/{action_id}/execute"]["post"],
                     event["paths"]["/api/v1/executions/{execution_id}"]["get"]):
        hdrs = str(route_op.get("responses", {})) + str(route_op.get("parameters", []))
        check("X-Opal-Session-Id" in hdrs or "OpalSessionIdHeader" in hdrs,
              "correlation headers on a THINK-facing op")
        break

    # Task input must validate against an action's input_schema (EventInput.data).
    check("EventInput" in event["components"]["schemas"] and
          "data" in event["components"]["schemas"]["EventInput"]["properties"],
          "EventInput.data exists for THINK to populate")
    check("ActionInputSchema" in event["components"]["schemas"],
          "ActionInputSchema exists for THINK to read")

    # No second executor/admin surface inside THINK.
    think_paths = set(think["paths"])
    check(not any(p.rstrip("/").endswith("/actions") or "/actions/" in p for p in think_paths),
          "THINK hosts no second action registry")
    check(not any("/executions" in p for p in think_paths),
          "THINK hosts no second execution record surface")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
