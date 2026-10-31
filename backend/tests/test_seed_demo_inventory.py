from app.seed_demo_inventory import seed_demo_inventory


def test_demo_inventory_seed_is_repeatable_and_never_creates_notices(fake_db):
    first = seed_demo_inventory(fake_db)
    second = seed_demo_inventory(fake_db)

    assert first == second
    assert fake_db["products"].count_documents({"data_origin": "demo"}) == 1
    assert fake_db["inventory_items"].count_documents({"is_demo": True}) == 1
    assert fake_db["safety_notices"].count_documents({}) == 0
