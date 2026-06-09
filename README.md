# MT5 Account Orchestrator

The MT5 Account Orchestrator is a continuous background daemon that manages MetaTrader 5 worker processes for active user subscriptions. It communicates with the Bhionex API to dynamically spin up new terminals, update configurations on credentials change, monitor worker health, and shut down terminals for expired/cancelled accounts.

---

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill out the variables in `.env`:
   - `API_BASE_URL` and `BOT_API_KEY` (Bhionex API endpoint and key)
   - `MASTER_MT5_DIR` (Path to your master template MT5 installation folder)
   - `CLIENTS_DIR` (Target folder where cloned user instances will be managed)
   - `ORCHESTRATOR_INTERVAL` (Polling interval in seconds, default: 60)

3. Make sure `example.ini` is in the same directory (acts as the configuration template for the cloned `config.ini`).
4. Install dependencies listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

### Linux Setup (via Wine)
Because MetaTrader 5 and its Python package are Windows-only, you must run the entire orchestrator inside Wine on Linux:
1. Install Wine on your Linux server.
2. Install the MT5 terminal inside your Wine prefix.
3. Install **Windows Python** (e.g., Python 3.9+) inside Wine.
4. Open a Wine CMD or terminal and install dependencies using the Wine Python:
   ```bash
   wine python.exe -m pip install -r requirements.txt
   ```
5. Run the orchestrator and all scripts using the Wine Python:
   ```bash
   wine python.exe orchestrator.py
   ```

---

## How to Run

### Starting the Orchestrator Daemon
To run the background management loop (polls API and spawns/updates workers):
```bash
python orchestrator.py
```
You can override the synchronization interval on the CLI:
```bash
python orchestrator.py --interval 30
```

### Stopping Running Workers & Terminals
To stop all active Python workers and terminal processes:
```bash
python stop_workers.py
```

### Purging Clone Directories
To permanently delete all generated clone directories in `CLIENTS_DIR` (asks for confirmation):
```bash
python purge_clones.py
```

### Local Development / Testing with Mock Server
To test the complete workflow locally:
1. Start the mock server:
   ```bash
   python mock_server.py
   ```
2. Configure your local `.env` to point to the mock server:
   ```env
   API_BASE_URL=http://localhost:5000
   BOT_API_KEY=any_mock_key
   ```
3. Run the orchestrator:
   ```bash
   python orchestrator.py
   ```

---

## Architecture

### Orchestrator Daemon (`orchestrator.py`)
- Runs continuously and performs a global cleanup of existing workers on startup.
- Periodically polls the Bhionex API for active subscriptions.
- If a new account is subscription-active, clones the template directory (if not already existing) and spawns an isolated worker process.
- If an active account credentials/configuration changes, kills the old worker/terminal processes and spawns a new one with the updated configuration.
- If a subscription goes inactive, gracefully terminates the corresponding worker and cloned MT5 processes.

### MT5 Account Worker (`worker.py`)
Each active MT5 account runs its own isolated background process managed by `worker.py`:
1. **Autonomously Populates Directory**: If files are missing, duplicates the master directory structure.
2. **Generates Config**: Automatically generates a case-preserved `config.ini` using credentials.
3. **Clears Default Charts**: Removes all open charts (`.chr` files) in both `MQL5/Profiles/Charts/` and `Profiles/Charts/` to start the terminal with an empty screen.
4. **Launches MT5**: Starts `terminal64.exe` in portable mode (`/portable`).
5. **Connects via API**: Initializes connection via python `MetaTrader5` package.
6. **Syncs Closed Trades**: Polls history deals and reports closed positions to `POST /api/bot/trades`. Already-synced ticket IDs are persisted locally in `reported_tickets.json` to prevent duplicates.
7. **Syncs Summary**: Reports balance, equity, and connectivity status to `POST /api/bot/trading-summary`.
8. **Monitors Health**: Restarts the terminal process if connection or health checks fail multiple times consecutively.
