import os

import httpx
import kopf

TESTAPI_URL = os.environ.get("TESTAPI_URL", "http://testapi.default.svc.cluster.local:3000")
INTERVAL = int(os.environ.get("RECONCILE_INTERVAL", "15"))

client = httpx.Client(base_url=TESTAPI_URL, timeout=5.0)


def _payload(spec):
    return {"name": spec["name"], "description": spec["description"]}


def _create(spec, patch, logger):
    r = client.post("/elements", json=_payload(spec))
    r.raise_for_status()
    eid = r.json()["id"]
    patch.status["elementId"] = eid
    logger.info(f"Created element id={eid}")
    return eid


@kopf.on.create("semds.example.com", "v1", "elements")
def on_create(spec, patch, logger, **_):
    _create(spec, patch, logger)


@kopf.on.update("semds.example.com", "v1", "elements", field="spec")
def on_update(spec, status, patch, logger, **_):
    eid = status.get("elementId")
    if eid is None:
        _create(spec, patch, logger)
        return
    r = client.put(f"/elements/{eid}", json=_payload(spec))
    if r.status_code == 404:
        _create(spec, patch, logger)
        return
    r.raise_for_status()
    logger.info(f"Updated element id={eid}")


@kopf.on.delete("semds.example.com", "v1", "elements")
def on_delete(status, logger, **_):
    eid = status.get("elementId")
    if eid is None:
        return
    r = client.delete(f"/elements/{eid}")
    if r.status_code not in (200, 204, 404):
        r.raise_for_status()
    logger.info(f"Deleted element id={eid}")


@kopf.timer("semds.example.com", "v1", "elements", interval=INTERVAL, initial_delay=INTERVAL)
def reconcile(spec, status, patch, logger, **_):
    eid = status.get("elementId")
    if eid is None:
        _create(spec, patch, logger)
        return
    r = client.get(f"/elements/{eid}")
    if r.status_code == 404:
        logger.warning(f"Element id={eid} gone upstream! Recreating ...")
        _create(spec, patch, logger)
        return
    r.raise_for_status()
    upstream = r.json()
    if upstream.get("name") != spec["name"] or upstream.get("description") != spec["description"]:
        client.put(f"/elements/{eid}", json=_payload(spec)).raise_for_status()
        logger.info(f"Drift corrected on id={eid}")
