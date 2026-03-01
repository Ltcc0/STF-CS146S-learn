"""
A minimal MCP server over stdio, backed by local SQLite and local Ollama.

Run:
    python mcp_sqlite_server.py
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "local_data.db"
OLLAMA_MODEL = "llama3.1:8b"
SERVER_NAME = "local-sqlite-mcp"
SERVER_VERSION = "1.0.0"


def _run_query(sql: str) -> list[dict[str, Any]]:
    """Execute a read-only SQL query and return rows as dictionaries."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}. Run init_db.py first.")

    safe_sql = sql.strip().rstrip(";")
    if not re.match(r"(?is)^select\b", safe_sql):
        raise ValueError("Only SELECT statements are allowed.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(safe_sql)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _get_schema_text() -> str:
    """Read schema info so the LLM can generate valid SQL."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        schema_rows = cur.fetchall()
    finally:
        conn.close()
    return "\n\n".join(f"{name}: {ddl}" for name, ddl in schema_rows)


def query_sqlite(sql: str) -> str:
    """MCP tool: execute read-only SQL and return JSON rows."""
    rows = _run_query(sql)
    return json.dumps(rows, ensure_ascii=False, indent=2)


def ask_database(question: str) -> str:
    """MCP tool: use local Ollama to turn natural language into SQL and query."""
    try:
        from ollama import chat
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency 'ollama'. Install with: pip install ollama"
        ) from exc

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}. Run init_db.py first.")

    schema = _get_schema_text()
    prompt = f"""
You are a SQLite expert.
Translate the user question into exactly one SQLite SELECT statement.
Rules:
1) Output SQL only. No markdown and no explanation.
2) Use only this schema:
{schema}
3) SQL must start with SELECT.

Question: {question}
"""
    response = chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
    sql = response["message"]["content"].strip().strip("`")
    rows = _run_query(sql)
    return json.dumps({"sql": sql, "rows": rows}, ensure_ascii=False, indent=2)


def _read_message() -> dict[str, Any] | None:
    """Read one MCP/JSON-RPC message framed with Content-Length headers."""
    content_length: int | None = None

    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        header = line.decode("utf-8", errors="replace").strip()
        if header.lower().startswith("content-length:"):
            content_length = int(header.split(":", 1)[1].strip())

    if content_length is None:
        return None

    body = sys.stdin.buffer.read(content_length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    """Write one framed MCP/JSON-RPC message to stdout."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8"))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _success_response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error_response(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def _handle_request(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    message_id = msg.get("id")
    params = msg.get("params", {})

    # Notifications do not require responses.
    if message_id is None:
        return None

    if method == "initialize":
        return _success_response(
            message_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    if method == "tools/list":
        return _success_response(
            message_id,
            {
                "tools": [
                    {
                        "name": "query_sqlite",
                        "description": "Run a read-only SELECT SQL query on local SQLite.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"sql": {"type": "string"}},
                            "required": ["sql"],
                        },
                    },
                    {
                        "name": "ask_database",
                        "description": "Use local Ollama to convert question to SQL and query SQLite.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"question": {"type": "string"}},
                            "required": ["question"],
                        },
                    },
                ]
            },
        )

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        try:
            if tool_name == "query_sqlite":
                result_text = query_sqlite(arguments["sql"])
            elif tool_name == "ask_database":
                result_text = ask_database(arguments["question"])
            else:
                return _error_response(message_id, -32601, f"Unknown tool: {tool_name}")
        except Exception as exc:
            return _error_response(message_id, -32000, str(exc))

        return _success_response(message_id, {"content": [{"type": "text", "text": result_text}]})

    if method == "ping":
        return _success_response(message_id, {})

    return _error_response(message_id, -32601, f"Method not found: {method}")


def main() -> None:
    """Main server loop."""
    while True:
        msg = _read_message()
        if msg is None:
            break
        response = _handle_request(msg)
        if response is not None:
            _write_message(response)


if __name__ == "__main__":
    main()
