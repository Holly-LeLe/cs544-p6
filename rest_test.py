import requests
import random
import string

BASE = "http://localhost:5000/test/api"

def random_ticker():
    return "".join(random.choices(string.ascii_uppercase, k=8))

def test_add_and_get_company():
    # use random tickers so tests don't interfere with data from previous runs
    ticker = random_ticker()

    # Create a company
    r = requests.post(f"{BASE}/companies/{ticker}",
                      json={"name": "MegaCorp", "sector": "Everything"})
    assert r.status_code == 201
    data = r.json()
    assert data["ticker"] == ticker
    assert data["name"] == "MegaCorp"
    assert data["sector"] == "Everything"

    # Update the same company (upsert)
    r = requests.post(f"{BASE}/companies/{ticker}",
                      json={"name": "Mega Corp", "sector": "All The Things"})
    assert r.status_code == 201
    data = r.json()
    assert data["ticker"] == ticker
    assert data["name"] == "Mega Corp"
    assert data["sector"] == "All The Things"
