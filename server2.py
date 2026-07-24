import os, sys
import time
from datetime import date, datetime
from flask import Flask, request, jsonify
from cassandra.cluster import Cluster
from cassandra.query import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider # Included for completeness, not used by default

app = Flask(__name__)

project = os.environ.get("PROJECT", "p6")
nodes = [f"{project}-cassandra-1", f"{project}-cassandra-2", f"{project}-cassandra-3"]
session = None

# Sentinel date for company information (to avoid returning it in stock record queries)
COMPANY_INFO_DATE = date(1970, 1, 1)

def create_keyspace_and_table(session_obj, keyspace_name):
    print(f"Creating keyspace {keyspace_name}...")
    session_obj.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {keyspace_name}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '3'}}
    """)
    print(f"Keyspace {keyspace_name} created.")

    print(f"Creating table {keyspace_name}.stocks_by_ticker...")
    session_obj.execute(f"""
        CREATE TABLE IF NOT EXISTS {keyspace_name}.stocks_by_ticker (
            ticker text,
            date date,
            name text static,
            sector text static,
            high double,
            low double,
            PRIMARY KEY (ticker, date)
        )
    """)
    print(f"Table {keyspace_name}.stocks_by_ticker created.")

# -------------------------
# POST /api/companies/<ticker>
# Body: {name, sector}
# Creates or renames a company
# -------------------------
@app.route("/<db>/api/companies/<ticker>", methods=["POST"])
def add_company(db, ticker):
    data   = request.get_json()
    name   = data.get("name")
    sector = data.get("sector")

    if not all([name, sector]):
        return jsonify({"error": "name and sector are required"}), 400

    # Insert/update static columns. Use a sentinel date to satisfy the primary key.
    # This row will be filtered out by GET requests for stock records.
    query = f"""
        INSERT INTO {db}.stocks_by_ticker (ticker, date, name, sector)
        VALUES (%s, %s, %s, %s)
    """
    session.execute(query, (ticker, COMPANY_INFO_DATE, name, sector))

    return jsonify({"ticker": ticker, "name": name, "sector": sector}), 201


# -------------------------
# POST /api/companies/<ticker>/records/<date>
# Body: {high, low}
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/<date_str>", methods=["POST"])
def add_stock(db, ticker, date_str):
    data = request.get_json()
    high = data.get("high")
    low  = data.get("low")

    if any(v is None for v in [high, low]):
        return jsonify({"error": "high and low are required"}), 400

    try:
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    query = f"""
        INSERT INTO {db}.stocks_by_ticker (ticker, date, high, low)
        VALUES (%s, %s, %s, %s)
    """
    session.execute(query, (ticker, record_date, high, low))

    return jsonify({"ticker": ticker, "date": date_str}), 201


# -------------------------
# GET /api/stocks/<ticker>
# Returns all rows for a ticker, joined with company info
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records", methods=["GET"])
def get_stocks(db, ticker):
    query = f"""
        SELECT ticker, name, sector, date, high, low
        FROM {db}.stocks_by_ticker
        WHERE ticker = %s AND date > %s
        ORDER BY date
    """
    rows = session.execute(query, (ticker, COMPANY_INFO_DATE))

    result = []
    for row in rows:
        # Filter out rows where high or low are None (e.g., if only static columns were set)
        if row.high is not None and row.low is not None:
            result.append({
                "ticker": row.ticker,
                "name": row.name,
                "sector": row.sector,
                "date": str(row.date),
                "high": row.high,
                "low": row.low,
            })

    if not result:
        return jsonify({"error": "not found"}), 404

    return jsonify(result)


# -------------------------
# GET /api/stocks/<ticker>/<date>
# Returns a single row
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/<date_str>", methods=["GET"])
def get_stock_date(db, ticker, date_str):
    try:
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    query = f"""
        SELECT ticker, name, sector, date, high, low
        FROM {db}.stocks_by_ticker
        WHERE ticker = %s AND date = %s
    """
    row = session.execute(query, (ticker, record_date)).one()

    if row is None or row.high is None or row.low is None: # Also check high/low to ensure it's a valid stock record
        return jsonify({"error": "not found"}), 404

    result = {
        "ticker": row.ticker,
        "name": row.name,
        "sector": row.sector,
        "date": str(row.date),
        "high": row.high,
        "low": row.low,
    }
    return jsonify(result)


# -------------------------
# GET /api/stocks/<ticker>/range?start=YYYY-MM-DD&end=YYYY-MM-DD
# Returns rows in a date range, ordered by date
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/range", methods=["GET"])
def get_stock_range(db, ticker):
    start_str = request.args.get("start")
    end_str   = request.args.get("end")

    if not start_str or not end_str:
        return jsonify({"error": "start and end query params are required"}), 400

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    query = f"""
        SELECT ticker, name, sector, date, high, low
        FROM {db}.stocks_by_ticker
        WHERE ticker = %s AND date >= %s AND date <= %s
        ORDER BY date
    """
    rows = session.execute(query, (ticker, start_date, end_date))

    result = []
    for row in rows:
        if row.high is not None and row.low is not None:
            result.append({
                "ticker": row.ticker,
                "name": row.name,
                "sector": row.sector,
                "date": str(row.date),
                "high": row.high,
                "low": row.low,
            })

    if not result:
        return jsonify({"error": "not found"}), 404

    return jsonify(result)


# -------------------------
# GET /api/stocks/<ticker>/monthly
# Returns average close price per month, ordered by month
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/monthly", methods=["GET"])
def get_stock_monthly(db, ticker):
    # Fetch all relevant stock records for the ticker
    query = f"""
        SELECT date, high
        FROM {db}.stocks_by_ticker
        WHERE ticker = %s AND date > %s
        ORDER BY date
    """
    rows = session.execute(query, (ticker, COMPANY_INFO_DATE))

    monthly_data = {} # Key: YYYY-MM, Value: list of high prices
    for row in rows:
        if row.high is not None:
            month_key = str(row.date)[:7]
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(row.high)

    if not monthly_data:
        return jsonify({"error": "not found"}), 404

    result = []
    for month_key in sorted(monthly_data.keys()):
        avg_high = sum(monthly_data[month_key]) / len(monthly_data[month_key])
        result.append({
            "month": month_key,
            "avg_high": round(avg_high, 4)
        })

    return jsonify(result)


if __name__ == "__main__":
    for _ in range(30):
        try:
            # No authentication specified, but PlainTextAuthProvider is available if needed.
            # Example: auth_provider = PlainTextAuthProvider(username='cassandra', password='cassandra')
            cluster = Cluster(nodes) # , auth_provider=auth_provider)
            session = cluster.connect()
            session.default_consistency_level = ConsistencyLevel.TWO
            break
        except Exception as ex:
            print(f"Cassandra connection failed: {ex}", file=sys.stderr)
            time.sleep(2)
    else:
        print("Failed to connect to Cassandra after 30 attempts", file=sys.stderr)
        sys.exit(1)

    # Create keyspaces and tables
    create_keyspace_and_table(session, "prod")
    create_keyspace_and_table(session, "test")

    app.run(host="0.0.0.0", port=5000, debug=True)
