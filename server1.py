import time
from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)


def get_db(db):
    return mysql.connector.connect(
        host="mysql",
        user="root",
        password="acid",
        database=db,
    )


# Retry connecting to MySQL on startup (it may not be ready immediately)
def wait_for_db():
    for _ in range(30):
        try:
            conn = get_db("prod")
            conn.close()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Could not connect to MySQL after retries")


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

    conn = get_db(db)
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO companies (ticker, name, sector) VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE name = VALUES(name), sector = VALUES(sector)""",
        (ticker, name, sector),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ticker": ticker, "name": name, "sector": sector}), 201


# -------------------------
# POST /api/companies/<ticker>/records/<date>
# Body: {high, low}
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/<date>", methods=["POST"])
def add_stock(db, ticker, date):
    data = request.get_json()
    high = data.get("high")
    low  = data.get("low")

    if any(v is None for v in [high, low]):
        return jsonify({"error": "high and low are required"}), 400

    conn = get_db(db)
    cur  = conn.cursor()
    cur.execute(
        """INSERT INTO stocks (ticker, date, high, low)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE high = VALUES(high), low = VALUES(low)""",
        (ticker, date, high, low),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ticker": ticker, "date": date}), 201


# -------------------------
# GET /api/stocks/<ticker>
# Returns all rows for a ticker, joined with company info
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records", methods=["GET"])
def get_stocks(db, ticker):
    conn = get_db(db)
    cur  = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT s.ticker, c.name, c.sector, s.date, s.high, s.low
           FROM stocks s JOIN companies c ON s.ticker = c.ticker
           WHERE s.ticker = %s
           ORDER BY s.date""",
        (ticker,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"error": "not found"}), 404

    for r in rows:
        r["date"] = str(r["date"])
    return jsonify(rows)


# -------------------------
# GET /api/stocks/<ticker>/<date>
# Returns a single row
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/<date>", methods=["GET"])
def get_stock_date(db, ticker, date):
    conn = get_db(db)
    cur  = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT s.ticker, c.name, c.sector, s.date, s.high, s.low
           FROM stocks s JOIN companies c ON s.ticker = c.ticker
           WHERE s.ticker = %s AND s.date = %s""",
        (ticker, date),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return jsonify({"error": "not found"}), 404

    row["date"] = str(row["date"])
    return jsonify(row)


# -------------------------
# GET /api/stocks/<ticker>/range?start=YYYY-MM-DD&end=YYYY-MM-DD
# Returns rows in a date range, ordered by date
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/range", methods=["GET"])
def get_stock_range(db, ticker):
    start = request.args.get("start")
    end   = request.args.get("end")

    if not start or not end:
        return jsonify({"error": "start and end query params are required"}), 400

    conn = get_db(db)
    cur  = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT s.ticker, c.name, c.sector, s.date, s.high, s.low
           FROM stocks s JOIN companies c ON s.ticker = c.ticker
           WHERE s.ticker = %s AND s.date BETWEEN %s AND %s
           ORDER BY s.date""",
        (ticker, start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"error": "not found"}), 404

    for r in rows:
        r["date"] = str(r["date"])
    return jsonify(rows)


# -------------------------
# GET /api/stocks/<ticker>/monthly
# Returns average close price per month, ordered by month
# -------------------------
@app.route("/<db>/api/companies/<ticker>/records/monthly", methods=["GET"])
def get_stock_monthly(db, ticker):
    conn = get_db(db)
    cur  = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT CONCAT(YEAR(s.date), '-', LPAD(MONTH(s.date), 2, '0')) AS month,
                  AVG(s.high) AS avg_high
           FROM stocks s
           WHERE s.ticker = %s
           GROUP BY month
           ORDER BY month""",
        (ticker,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"error": "not found"}), 404

    for r in rows:
        r["avg_high"] = round(float(r["avg_high"]), 4)
    return jsonify(rows)


if __name__ == "__main__":
    wait_for_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
