from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import threading
import os
import time

# Flask app initialization
app = Flask(__name__)

# Database file
DB_NAME = "banking_system.db"

# Initialize threading lock
lock = threading.Lock()

# Distributed nodes and state
NODES = ["5000", "5001", "5002"]
NODE_PORT = os.getenv("NODE_PORT", "5000")
state = "follower"  # States: leader, follower, candidate, failed
current_leader = None

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()

    # Create accounts table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')

    # Create logs table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            account_id TEXT,
            amount INTEGER,
            target_account TEXT,
            status TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# Node simulation routes
@app.route("/")
def home():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts")
    accounts = cursor.fetchall()
    conn.close()
    return render_template("index.html", accounts=accounts, node_port=NODE_PORT, state=state)

@app.route("/create_account", methods=["POST"])
def create_account():
    try:
        account_id = request.form["account_id"]
        initial_balance = request.form.get("initial_balance", 0)

        with lock:  # Lock to ensure thread safety
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO accounts (account_id, balance) VALUES (?, ?)", (account_id, initial_balance))
            conn.commit()
            conn.close()

        return redirect(url_for("home"))
    except Exception as e:
        return f"Error creating account: {e}", 500

@app.route("/transfer", methods=["POST"])
def transfer():
    global state
    try:
        if state == "failed":
            return "Node is unavailable. Please recover the node.", 503

        source_account = request.form["source_account"]
        target_account = request.form["target_account"]
        amount = int(request.form["amount"])

        with lock:  # Lock to ensure thread safety
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()

            # Simulate transaction delay
            time.sleep(5)

            # Check if the source account has sufficient funds
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (source_account,))
            row = cursor.fetchone()
            if not row or row[0] < amount:
                return "Insufficient funds or account not found", 400

            # Deduct from source and add to target
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_id = ?", (amount, source_account))
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_id = ?", (amount, target_account))

            # Log the transaction
            cursor.execute(''' 
                INSERT INTO logs (action, account_id, amount, target_account, status, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', ("transfer", source_account, amount, target_account, "completed"))
            
            conn.commit()
            conn.close()

        return redirect(url_for("home"))
    except Exception as e:
        return f"Error during transfer: {e}", 500

@app.route("/simulate_failure")
def simulate_failure():
    global state
    state = "failed"
    return "Node failed"

@app.route("/get_accounts", methods=["GET"])
def get_accounts():
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, balance FROM accounts")
        accounts = cursor.fetchall()
        conn.close()

        return jsonify({"accounts": accounts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/recover")
def recover():
    global state
    state = "follower"
    # Replay logs or reload data
    try:
        with lock:
            conn = sqlite3.connect(DB_NAME, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs WHERE status = 'completed'")
            for log in cursor.fetchall():
                # Replay completed transactions
                cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_id = ?", (log[2], log[1]))
                cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_id = ?", (log[2], log[3]))
            conn.commit()
            conn.close()
        return "Node recovered"
    except Exception as e:
        return f"Error during node recovery: {e}", 500

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=int(NODE_PORT))
