
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000/api"

# All LOT numbers and quantities below are synthetic demo data.
# They are NOT actual affected LOT numbers published by Thai FDA.

DEMO_INVENTORY = {
    "1A 29/64": [
        "DEMO-PIPROXY-RECALL-001",
        "DEMO-PIPROXY-RECALL-002",
        "DEMO-PIPROXY-RECALL-003",
        "DEMO-PIPROXY-RECALL-004",
    ],
    "1C 17/59": [
        "DEMO-NORENE-RECALL-001",
    ],
    "1A 249/52": [
        f"DEMO-PIPZOVIVIR-RECALL-{i:03d}"
        for i in range(1, 12)
    ],
}

DEMO_QUANTITY = 10
DEMO_EXPIRY = "2028-12-31"


def request_api(method, endpoint, payload=None):
    headers = {"Accept": "application/json"}
    body = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        BASE_URL + endpoint,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}

    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, raw


def get_items(endpoint):
    status, response = request_api("GET", endpoint)

    if status != 200:
        raise RuntimeError(f"GET {endpoint} failed: {status} {response}")

    if isinstance(response, list):
        return response

    if isinstance(response, dict):
        return response.get("items", [])

    raise RuntimeError(f"Unexpected response from {endpoint}")


def main():
    print("Fetching products and existing inventory...")

    products = get_items("/products?skip=0&limit=200")
    inventory = get_items("/inventory?skip=0&limit=200")

    product_by_registration = {
        str(p.get("registration_no", "")).strip().casefold(): p
        for p in products
        if p.get("registration_no")
    }

    existing_keys = {
        (
            str(item.get("product_id", "")),
            str(item.get("lot_number", "")).strip().casefold(),
        )
        for item in inventory
    }

    created = 0
    skipped = 0
    failed = 0

    for registration_no, lots in DEMO_INVENTORY.items():
        product = product_by_registration.get(
            registration_no.strip().casefold()
        )

        if not product:
            print(f"[MISSING PRODUCT] {registration_no}")
            failed += len(lots)
            continue

        product_id = product.get("id") or product.get("_id")

        if not product_id:
            print(f"[INVALID PRODUCT ID] {registration_no}")
            failed += len(lots)
            continue

        for lot in lots:
            key = (str(product_id), lot.casefold())

            if key in existing_keys:
                print(f"[SKIPPED] {lot}")
                skipped += 1
                continue

            payload = {
                "product_id": str(product_id),
                "lot_number": lot,
                "quantity": DEMO_QUANTITY,
                "expiry_date": DEMO_EXPIRY,
                "is_demo": True,
            }

            status, response = request_api(
                "POST",
                "/inventory",
                payload,
            )

            if status in (200, 201):
                print(f"[CREATED] {lot}")
                created += 1
                existing_keys.add(key)
            else:
                print(f"[FAILED] {lot}: {status} {response}")
                failed += 1

    print("\n========== INVENTORY SUMMARY ==========")
    print("Created:", created)
    print("Skipped:", skipped)
    print("Failed:", failed)
    print("Total requested:", sum(map(len, DEMO_INVENTORY.values())))

    if failed:
        print("\nResolve errors before running matching.")

    elif created or skipped:
        print("\nInventory seeding completed.")
        print("Next: run the matching engine manually.")


if __name__ == "__main__":
    main()
