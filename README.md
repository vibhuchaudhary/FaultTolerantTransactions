
# Distributed Banking System

The Distributed Banking System is a web-based application built using Streamlit, SQLite, and Python. This system simulates a banking environment with support for multiple nodes in a distributed setting. Nodes can operate as leaders or followers, and failure recovery mechanisms are provided for fault tolerance.


## Features

- Account Management: Create accounts, view balances, and perform deposit/withdraw operations.
- Fund Transfers: Transfer money between accounts with validation.
- Transaction Logs: View detailed transaction logs.
- Node Control: Simulate node failure, recover nodes, and elect leaders in the distributed system.
## Installation
Install dependencies
```bash
pip install streamlit sqlite3

```
Run the application
```bash
streamlit run main.py
```

## Tech Stack

**Programming Language:** Python 3.7+

**Frameworks:** Streamlit (User Interface)

**Database:** SQLite3