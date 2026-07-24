import os, sys
import time
from flask import Flask, request, jsonify
from cassandra.cluster import Cluster
from cassandra.query import ConsistencyLevel

app = Flask(__name__)

project = os.environ.get("PROJECT", "p6")
nodes = [f"{project}-cassandra-1", f"{project}-cassandra-2", f"{project}-cassandra-3"]
session = None

# TODO: endpoints

if __name__ == "__main__":
    for _ in range(30):
        try:
            cluster = Cluster(nodes)
            session = cluster.connect()
            break
        except Exception as ex:
            print(ex)
            time.sleep(2)
    else:
        print("Failed to connect to Cassandra after 30 attempts")
        sys.exit(1)

    # TODO: use session to create tables

    app.run(host="0.0.0.0", port=5000, debug=True)
