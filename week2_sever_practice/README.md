# Local SQLite MCP Server (Python)

## 1) Install dependencies

`ollama` Python package is already in this project dependencies.
If your current interpreter cannot import it, run:

```bash
pip install ollama
```

Also ensure Ollama is installed locally and a free model is pulled:

```bash
ollama pull llama3.1:8b
```

## 2) Initialize SQLite database

```bash
cd practice
python init_db.py
```

This will create:

- `practice/database/local_data.db`

## 3) Run MCP server

```bash
cd practice
python mcp_sqlite_server.py
```

The server communicates via MCP stdio (JSON-RPC + `Content-Length` framing).

## 4) Exposed MCP tools

- `query_sqlite(sql: str)`:
  Execute read-only `SELECT` SQL and return JSON rows.
- `ask_database(question: str)`:
  Use local Ollama model to convert question -> SQL -> query SQLite, then return SQL + rows.

## 5) Example MCP client config

```json
{
  "mcpServers": {
    "local-sqlite": {
      "command": "python",
      "args": ["f:/stf-CS146S/modern-software-dev-assignments/practice/mcp_sqlite_server.py"]
    }
  }
}
```
