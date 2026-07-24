import requests
import random
import string

BASE = "http://localhost:5000/test/api"

def random_ticker():
    return "".join(random.choices(string.ascii_uppercase, k=8))

def create_company(ticker, name="MegaCorp", sector="Everything"):
    r = requests.post(
        f"{BASE}/companies/{ticker}",
        json={"name": name, "sector": sector},
    )
    assert r.status_code == 201
    return r.json()

def create_record(ticker, date, high, low):
    r = requests.post(
        f"{BASE}/companies/{ticker}/records/{date}",
        json={"high": high, "low": low},
    )
    assert r.status_code == 201
    return r.json()

def test_add_and_get_company():
    # use random tickers so tests don't interfere with data from previous runs
    ticker = random_ticker()

    # Create a company
    data = create_company(ticker)
    assert data["ticker"] == ticker
    assert data["name"] == "MegaCorp"
    assert data["sector"] == "Everything"

    # Update the same company (upsert)
    data = create_company(ticker, name="Mega Corp", sector="All The Things")
    assert data["ticker"] == ticker
    assert data["name"] == "Mega Corp"
    assert data["sector"] == "All The Things"

def test_add_stock_record():
    ticker = random_ticker()
    create_company(ticker, name="Apple Inc.", sector="Technology")

    data = create_record(ticker, "2024-01-02", 188.0, 184.0)
    assert data["ticker"] == ticker
    assert data["date"] == "2024-01-02"

def test_get_all_records():
    ticker = random_ticker()
    create_company(ticker, name="Test Co", sector="Finance")

    create_record(ticker, "2024-01-02", 100.0, 90.0)
    create_record(ticker, "2024-01-03", 110.0, 95.0)

    r = requests.get(f"{BASE}/companies/{ticker}/records")
    assert r.status_code == 200

    data = r.json()
    assert len(data) == 2
    assert data[0]["ticker"] == ticker
    assert data[0]["name"] == "Test Co"
    assert data[0]["sector"] == "Finance"
    assert data[0]["date"] == "2024-01-02"
    assert data[0]["high"] == 100.0
    assert data[0]["low"] == 90.0

    assert data[1]["date"] == "2024-01-03"
    assert data[1]["high"] == 110.0
    assert data[1]["low"] == 95.0

def test_get_one_record_by_date():
    ticker = random_ticker()
    create_company(ticker, name="Date Co", sector="Retail")

    create_record(ticker, "2024-02-01", 200.0, 180.0)
    create_record(ticker, "2024-02-02", 220.0, 190.0)

    r = requests.get(f"{BASE}/companies/{ticker}/records/2024-02-02")
    assert r.status_code == 200

    data = r.json()
    assert data["ticker"] == ticker
    assert data["name"] == "Date Co"
    assert data["sector"] == "Retail"
    assert data["date"] == "2024-02-02"
    assert data["high"] == 220.0
    assert data["low"] == 190.0

def test_get_records_in_range():
    ticker = random_ticker()
    create_company(ticker, name="Range Co", sector="Energy")

    create_record(ticker, "2024-03-01", 10.0, 5.0)
    create_record(ticker, "2024-03-15", 20.0, 10.0)
    create_record(ticker, "2024-04-01", 30.0, 15.0)

    r = requests.get(
        f"{BASE}/companies/{ticker}/records/range",
        params={"start": "2024-03-10", "end": "2024-04-01"},
    )
    assert r.status_code == 200

    data = r.json()
    assert len(data) == 2
    assert data[0]["date"] == "2024-03-15"
    assert data[0]["high"] == 20.0
    assert data[1]["date"] == "2024-04-01"
    assert data[1]["high"] == 30.0

def test_get_monthly_averages():
    ticker = random_ticker()
    create_company(ticker, name="Month Co", sector="Healthcare")

    create_record(ticker, "2024-01-02", 100.0, 80.0)
    create_record(ticker, "2024-01-20", 200.0, 150.0)
    create_record(ticker, "2024-02-01", 300.0, 250.0)

    r = requests.get(f"{BASE}/companies/{ticker}/records/monthly")
    assert r.status_code == 200

    data = r.json()
    assert len(data) == 2
    assert data[0]["month"] == "2024-01"
    assert data[0]["avg_high"] == 150.0
    assert data[1]["month"] == "2024-02"
    assert data[1]["avg_high"] == 300.0

def test_record_upsert_behavior():
    ticker = random_ticker()
    create_company(ticker, name="Upsert Co", sector="Tech")

    create_record(ticker, "2024-05-01", 50.0, 40.0)
    create_record(ticker, "2024-05-01", 60.0, 45.0)

    r = requests.get(f"{BASE}/companies/{ticker}/records/2024-05-01")
    assert r.status_code == 200

    data = r.json()
    assert data["high"] == 60.0
    assert data["low"] == 45.0
