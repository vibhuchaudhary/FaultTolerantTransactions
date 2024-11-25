import streamlit as st
import sqlite3
import threading

# Database file
DB_NAME = "banking_system.db"

# Initialize threading lock
lock = threading.Lock()

# Initialize session state variables
if "state" not in st.session_state:
    st.session_state.state = "follower"  # Possible states: leader, follower, candidate, failed
if "current_leader" not in st.session_state:
    st.session_state.current_leader = None

# Database initialization
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')

    # Create logs table
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

# Main application function
def main():
    st.title("Distributed Banking System")
    
    # Sidebar Node State Display
    st.sidebar.header("Node State")
    st.sidebar.markdown(f"**Current State**: {st.session_state.state.upper()}")
    if st.session_state.state == "leader":
        st.sidebar.markdown(f"**Leader**: {st.session_state.current_leader}")

    # Sidebar Menu
    menu = st.sidebar.radio("Menu", ["Accounts", "Transfer Funds", "Transaction Logs"])

    # Sidebar Node Control Buttons
    st.sidebar.header("Node Control")
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("Simulate Failure"):
            simulate_failure()
    with col2:
        if st.button("Recover Node"):
            recover_node()
    with col3:
        if st.button("Elect Leader"):
            simulate_leader_election()

    # Page rendering based on menu selection
    if menu == "Accounts":
        render_accounts_page()
    elif menu == "Transfer Funds":
        render_transfer_page()
    elif menu == "Transaction Logs":
        render_logs_page()

# Render Accounts Page
def render_accounts_page():
    st.header("Account Management")
    
    # Account Creation Form
    with st.form("create_account"):
        account_id = st.text_input("Account ID")
        initial_balance = st.number_input("Initial Balance", min_value=0)
        submit = st.form_submit_button("Create Account")
        
        if submit:
            if account_id:
                create_account(account_id, initial_balance)
            else:
                st.error("Account ID cannot be empty")

    # Deposit and Withdraw Money
    st.subheader("Deposit and Withdraw Money")
    with st.form("deposit_withdraw"):
        account_id = st.text_input("Account ID for Transaction")
        transaction_type = st.selectbox("Transaction Type", ["Deposit", "Withdraw"])
        amount = st.number_input("Amount", min_value=0)
        submit = st.form_submit_button("Submit Transaction")
        
        if submit:
            if account_id:
                if transaction_type == "Deposit":
                    deposit_money(account_id, amount)
                elif transaction_type == "Withdraw":
                    withdraw_money(account_id, amount)
            else:
                st.error("Account ID cannot be empty")

    # Display Existing Accounts
    accounts = get_all_accounts()
    if accounts:
        st.subheader("Current Accounts")
        for account_id, balance in accounts:
            st.write(f"**{account_id}**: ${balance}")
    else:
        st.info("No accounts exist")

# Render Fund Transfer Page
def render_transfer_page():
    st.header("Fund Transfer")
    
    # Prevent fund transfers in failed state
    if st.session_state.state == "failed":
        st.error("Node is in FAILED state. Cannot process transactions.")
        return

    # Prevent transfers in follower state without a leader
    if st.session_state.state == "follower" and st.session_state.current_leader is None:
        st.error("No active leader. Cannot process transactions.")
        return

    # Fund Transfer Form
    with st.form("transfer_funds"):
        source_account = st.text_input("Source Account")
        target_account = st.text_input("Target Account")
        amount = st.number_input("Transfer Amount", min_value=0)
        submit = st.form_submit_button("Transfer Funds")

        if submit:
            result = transfer_funds(source_account, target_account, amount)
            if result == "success":
                st.success("Transfer completed successfully!")
            else:
                st.error(result)

# Render Transaction Logs Page
def render_logs_page():
    st.header("Transaction Logs")
    logs = get_logs()
    
    if logs:
        for log in logs:
            st.write(f"**Action**: {log[1]} | **From**: {log[2]} | **To**: {log[4]} | "
                     f"**Amount**: ${log[3]} | **Status**: {log[5]} | **Time**: {log[6]}")
    else:
        st.info("No transaction logs")

# Database operations
def create_account(account_id, initial_balance):
    try:
        with lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO accounts (account_id, balance) VALUES (?, ?)",
                           (account_id, initial_balance))
            conn.commit()
            conn.close()
        st.success(f"Account '{account_id}' created successfully")
    except Exception as e:
        st.error(f"Error creating account: {e}")

def get_all_accounts():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, balance FROM accounts")
        accounts = cursor.fetchall()
        conn.close()
        return accounts
    except Exception as e:
        st.error(f"Error fetching accounts: {e}")
        return []

def deposit_money(account_id, amount):
    if amount <= 0:
        st.error("Amount must be greater than zero")
        return
    
    try:
        with lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_id = ?", (amount, account_id))
            conn.commit()
            conn.close()
        st.success(f"Deposited ${amount} into account '{account_id}' successfully")
    except Exception as e:
        st.error(f"Error during deposit: {e}")

def withdraw_money(account_id, amount):
    if amount <= 0:
        st.error("Amount must be greater than zero")
        return
    
    try:
        with lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Check balance before withdrawing
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (account_id,))
            account = cursor.fetchone()
            if not account or account[0] < amount:
                st.error("Insufficient funds or account not found")
                return

            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_id = ?", (amount, account_id))
            conn.commit()
            conn.close()
        st.success(f"Withdrew ${amount} from account '{account_id}' successfully")
    except Exception as e:
        st.error(f"Error during withdrawal: {e}")

def transfer_funds(source_account, target_account, amount):
    if not source_account or not target_account or amount <= 0:
        return "Invalid transfer details"

    try:
        with lock:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Validate source account
            cursor.execute("SELECT balance FROM accounts WHERE account_id = ?", (source_account,))
            source = cursor.fetchone()
            if not source or source[0] < amount:
                return "Insufficient funds or source account not found"

            # Validate target account
            cursor.execute("SELECT account_id FROM accounts WHERE account_id = ?", (target_account,))
            if not cursor.fetchone():
                return "Target account not found"

            # Perform transfer
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE account_id = ?", (amount, source_account))
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE account_id = ?", (amount, target_account))

            # Log transaction
            cursor.execute('''
                INSERT INTO logs (action, account_id, amount, target_account, status, timestamp)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', ("transfer", source_account, amount, target_account, "completed"))

            conn.commit()
            conn.close()
            return "success"
    except Exception as e:
        return f"Transfer error: {e}"

def get_logs():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        conn.close()
        return logs
    except Exception as e:
        st.error(f"Error fetching logs: {e}")
        return []

# Node control functions
def simulate_failure():
    st.session_state.state = "failed"
    st.session_state.current_leader = None
    st.warning("Node state set to FAILED. Transactions are blocked.")

def recover_node():
    st.session_state.state = "follower"
    st.session_state.current_leader = None
    st.success("Node recovered to FOLLOWER state.")

def simulate_leader_election():
    st.session_state.state = "leader"
    st.session_state.current_leader = "LocalNode"
    st.success("Node elected as LEADER. All transactions can be processed.")

if __name__ == "__main__":
    main()
