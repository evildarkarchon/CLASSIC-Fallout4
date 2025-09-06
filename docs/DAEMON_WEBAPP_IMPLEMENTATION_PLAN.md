# CLASSIC Daemon & Web Application Implementation Plan (Simplified)

## Executive Summary

This document outlines a flexible implementation plan for extending CLASSIC with a daemon service and web application. The architecture supports multiple deployment modes - from a full web application to a lightweight API-only service for container-to-container communication. It focuses on ease of deployment with Docker Compose, minimal dependencies, and leveraging CLASSIC's existing async infrastructure. The system can run with or without persistence, with or without a web UI, and can be deployed with a single `docker-compose up -d` command or scaled horizontally in a microservices architecture.

## Architecture Overview

### Flexible Architecture (Web + API-Only Modes)

```
┌─────────────────────────────────────────────────────────────┐
│         External Applications (Discord Bot, etc.)            │
│                  Container-to-Container                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (Direct)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                         Web Browser                          │
│                    (Optional HTML/JS Frontend)               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WebSocket (Optional)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Web Server                        │
│                  (Single Python Process)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • REST API for log submission (Always Available)    │   │
│  │  • API-Only Mode (No Web UI)                        │   │
│  │  • WebSocket for real-time updates (Optional)       │   │
│  │  • Static file serving for frontend (Togglable)     │   │
│  │  • Built-in background task processing               │   │
│  │  • API Key Authentication                           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ In-Process Queue
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              CLASSIC Daemon (Background Tasks)               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  • AsyncIO task queue (no external dependencies)     │   │
│  │  • Existing CLASSIC OrchestratorCore                 │   │
│  │  • File system monitoring with watchdog (Optional)   │   │
│  │  • SQLite with aiosqlite (Optional Persistence)      │   │
│  │  • Stateless Processing Mode                        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage Layer (Optional)                        │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  SQLite/Memory  │  │  Temp Store  │  │   Reports    │   │
│  │   (Optional)    │  │  (Optional)  │  │  (Optional)  │   │
│  └─────────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Core Implementation

### 1. Single FastAPI Application with Async Database (`app.py`)

```python
"""
Simplified CLASSIC Web Service - All-in-one daemon and web server.
Uses async patterns consistent with CLASSIC codebase.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, Any
from uuid import uuid4
from datetime import datetime
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, UploadFile, WebSocket, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.FileIOCore import FileIOCore
from ClassicLib.Logger import logger


class DatabasePool:
    """
    Async SQLite connection pool following CLASSIC's AsyncDatabasePool pattern.
    """

    def __init__(self, db_path: str = "classic.db", max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: list[aiosqlite.Connection] = []
        self._used: set[aiosqlite.Connection] = set()
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Initialize the database and connection pool."""
        if self._initialized:
            return

        # Create database schema
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_size INTEGER,
                    file_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    error_message TEXT,
                    metadata JSON
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    report_id TEXT PRIMARY KEY,
                    log_id TEXT NOT NULL,
                    content JSON,
                    format TEXT DEFAULT 'json',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (log_id) REFERENCES logs (log_id)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status);
                CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
                CREATE INDEX IF NOT EXISTS idx_reports_log_id ON reports(log_id);
            """)

            await db.commit()

        # Pre-create connections for the pool
        for _ in range(min(2, self.max_connections)):
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            self._pool.append(conn)

        self._initialized = True
        logger.info(f"Database pool initialized with {len(self._pool)} connections")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        async with self._lock:
            # Try to get an existing connection
            while self._pool:
                conn = self._pool.pop()
                if await self._is_alive(conn):
                    self._used.add(conn)
                    break
                else:
                    await conn.close()
            else:
                # Create new connection if under limit
                if len(self._used) < self.max_connections:
                    conn = await aiosqlite.connect(self.db_path)
                    conn.row_factory = aiosqlite.Row
                    self._used.add(conn)
                else:
                    # Wait for a connection to be released
                    while not self._pool:
                        await asyncio.sleep(0.1)
                    conn = self._pool.pop()
                    self._used.add(conn)

        try:
            yield conn
        finally:
            async with self._lock:
                self._used.discard(conn)
                if await self._is_alive(conn):
                    self._pool.append(conn)
                else:
                    await conn.close()

    async def _is_alive(self, conn: aiosqlite.Connection) -> bool:
        """Check if a connection is still alive."""
        try:
            await conn.execute("SELECT 1")
            return True
        except:
            return False

    async def close(self):
        """Close all connections in the pool."""
        async with self._lock:
            for conn in self._pool + list(self._used):
                try:
                    await conn.close()
                except:
                    pass
            self._pool.clear()
            self._used.clear()
            self._initialized = False


# Global database pool
db_pool = DatabasePool()

# Application with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await db_pool.initialize()
    asyncio.create_task(process_queue_worker())

    # Start file system watcher if configured
    if Path("config.yaml").exists():
        start_filesystem_watcher()

    yield

    # Shutdown
    await db_pool.close()


app = FastAPI(title="CLASSIC Web Service", lifespan=lifespan)

# Simple in-memory queue and results cache
processing_queue = asyncio.Queue()
processing_results = {}
active_websockets = []

# Mount static files for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


class LogProcessor:
    """Handles crash log processing using CLASSIC core."""

    def __init__(self):
        self.io_core = FileIOCore()
        self.yamldata = ClassicScanLogsInfo()
        self.crashlogs = ThreadSafeLogCache()

    async def process_log(self, log_path: Path, log_id: str) -> dict:
        """Process a single crash log."""
        try:
            # Update status in database
            await update_log_status(log_id, "processing")
            processing_results[log_id] = {"status": "processing", "progress": 0}
            await notify_clients(log_id, "processing")

            # Use existing CLASSIC orchestrator
            orchestrator = OrchestratorCore(
                yamldata=self.yamldata,
                crashlogs=self.crashlogs,
                fcx_mode=False,
                show_formid_values=True,
                formid_db_exists=True
            )

            # Process the log
            content = await self.io_core.read_file(log_path)
            result = await orchestrator.process_crash_log(content)

            # Generate report
            report = {
                "log_id": log_id,
                "status": "completed",
                "findings": result.get("findings", []),
                "summary": result.get("summary", ""),
                "timestamp": datetime.now().isoformat()
            }

            # Save report to database
            await save_report(log_id, report)

            # Update status
            await update_log_status(log_id, "completed")
            processing_results[log_id] = report
            await notify_clients(log_id, "completed", report)

            return report

        except Exception as e:
            logger.error(f"Error processing log {log_id}: {e}")
            error_result = {
                "log_id": log_id,
                "status": "failed",
                "error": str(e)
            }

            await update_log_status(log_id, "failed", str(e))
            processing_results[log_id] = error_result
            await notify_clients(log_id, "failed", error_result)
            return error_result


# Database helper functions using async patterns

async def store_log_metadata(log_id: str, filename: str, file_size: int, file_hash: str = None):
    """Store log metadata in database using connection pool."""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO logs (log_id, filename, file_size, file_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (log_id, filename, file_size, file_hash, datetime.now())
        )
        await conn.commit()


async def update_log_status(log_id: str, status: str, error: str = None):
    """Update log processing status."""
    async with db_pool.acquire() as conn:
        if status == "completed":
            await conn.execute(
                "UPDATE logs SET status = ?, processed_at = ? WHERE log_id = ?",
                (status, datetime.now(), log_id)
            )
        elif status == "failed":
            await conn.execute(
                "UPDATE logs SET status = ?, error_message = ? WHERE log_id = ?",
                (status, error, log_id)
            )
        else:
            await conn.execute(
                "UPDATE logs SET status = ? WHERE log_id = ?",
                (status, log_id)
            )
        await conn.commit()


async def get_log_metadata(log_id: str) -> Optional[dict]:
    """Get log metadata from database."""
    async with db_pool.acquire() as conn:
        async with conn.execute(
            "SELECT * FROM logs WHERE log_id = ?", (log_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def save_report(log_id: str, report: dict):
    """Save report to database."""
    report_id = str(uuid4())
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO reports (report_id, log_id, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (report_id, log_id, json.dumps(report), datetime.now())
        )
        await conn.commit()

    # Also save to file for redundancy
    report_path = Path(f"reports/{log_id}.json")
    report_path.parent.mkdir(exist_ok=True)
    await FileIOCore().write_file(report_path, json.dumps(report, indent=2))


async def get_report(log_id: str) -> Optional[dict]:
    """Get report from database or file system."""
    # Try database first
    async with db_pool.acquire() as conn:
        async with conn.execute(
            "SELECT content FROM reports WHERE log_id = ? ORDER BY created_at DESC LIMIT 1",
            (log_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row["content"])

    # Fallback to file system
    report_path = Path(f"reports/{log_id}.json")
    if report_path.exists():
        content = await FileIOCore().read_file(report_path)
        return json.loads(content)

    return None


async def get_recent_logs(limit: int = 20, offset: int = 0) -> list[dict]:
    """Get recent logs with pagination."""
    async with db_pool.acquire() as conn:
        async with conn.execute(
            """
            SELECT * FROM logs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Background worker for processing queue
async def process_queue_worker():
    """Background worker that processes logs from the queue."""
    processor = LogProcessor()

    while True:
        try:
            # Get next item from queue
            log_id, log_path = await processing_queue.get()

            # Process the log
            await processor.process_log(log_path, log_id)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)


# API Endpoints

@app.get("/")
async def root():
    """Serve the main web interface."""
    return HTMLResponse(content=open("static/index.html").read())


@app.post("/api/logs/upload")
async def upload_log(file: UploadFile):
    """Upload a crash log for processing."""
    # Validate file
    if not file.filename.endswith(('.log', '.txt')):
        return {"error": "Invalid file type. Only .log and .txt files are accepted."}

    # Generate unique ID
    log_id = str(uuid4())

    # Save uploaded file
    upload_path = Path(f"uploads/{log_id}_{file.filename}")
    upload_path.parent.mkdir(exist_ok=True)

    content = await file.read()

    # Calculate file hash for deduplication
    import hashlib
    file_hash = hashlib.sha256(content).hexdigest()

    # Check if we've already processed this file
    async with db_pool.acquire() as conn:
        async with conn.execute(
            "SELECT log_id, status FROM logs WHERE file_hash = ?", (file_hash,)
        ) as cursor:
            existing = await cursor.fetchone()
            if existing:
                return {
                    "log_id": existing["log_id"],
                    "status": existing["status"],
                    "filename": file.filename,
                    "duplicate": True
                }

    # Save file
    await FileIOCore().write_file(upload_path, content.decode('utf-8', errors='ignore'))

    # Store metadata
    await store_log_metadata(log_id, file.filename, len(content), file_hash)

    # Add to processing queue
    await processing_queue.put((log_id, upload_path))

    return {
        "log_id": log_id,
        "status": "queued",
        "filename": file.filename,
        "queue_position": processing_queue.qsize()
    }


@app.get("/api/logs/{log_id}/status")
async def get_log_status(log_id: str):
    """Get the processing status of a log."""
    # Check in-memory cache first
    if log_id in processing_results:
        return processing_results[log_id]

    # Check database
    metadata = await get_log_metadata(log_id)
    if metadata:
        return {
            "log_id": log_id,
            "status": metadata.get("status", "unknown"),
            "filename": metadata.get("filename"),
            "created_at": metadata.get("created_at"),
            "processed_at": metadata.get("processed_at")
        }

    return {"error": "Log not found"}


@app.get("/api/reports/{log_id}")
async def get_report_endpoint(log_id: str):
    """Get the report for a processed log."""
    report = await get_report(log_id)
    if report:
        return report

    # Check if still processing
    if log_id in processing_results:
        return processing_results[log_id]

    return {"error": "Report not found"}


@app.get("/api/logs")
async def list_logs(limit: int = 20, offset: int = 0):
    """List recent logs with pagination."""
    logs = await get_recent_logs(limit, offset)
    return {
        "logs": logs,
        "limit": limit,
        "offset": offset
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await websocket.accept()
    active_websockets.append(websocket)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Could handle client commands here if needed
    except:
        active_websockets.remove(websocket)


async def notify_clients(log_id: str, status: str, data: dict = None):
    """Send updates to all connected WebSocket clients."""
    message = {
        "log_id": log_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }

    # Remove disconnected clients
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)

    for ws in disconnected:
        active_websockets.remove(ws)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    try:
        # Check database connection
        async with db_pool.acquire() as conn:
            await conn.execute("SELECT 1")

        return {
            "status": "healthy",
            "queue_size": processing_queue.qsize(),
            "active_websockets": len(active_websockets),
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# File system watcher for automatic processing

class LogFileHandler(FileSystemEventHandler):
    """Watches for new crash logs in configured directories."""

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.log', '.txt')):
            asyncio.create_task(self.process_new_log(event.src_path))

    async def process_new_log(self, file_path: str):
        """Process newly detected log file."""
        log_id = str(uuid4())
        path = Path(file_path)

        # Calculate hash to check for duplicates
        import hashlib
        content = path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()

        # Check if already processed
        async with db_pool.acquire() as conn:
            async with conn.execute(
                "SELECT log_id FROM logs WHERE file_hash = ?", (file_hash,)
            ) as cursor:
                if await cursor.fetchone():
                    logger.info(f"Skipping duplicate file: {file_path}")
                    return

        # Store metadata and queue for processing
        await store_log_metadata(log_id, path.name, path.stat().st_size, file_hash)
        await processing_queue.put((log_id, path))
        logger.info(f"Queued new log file: {file_path}")


def start_filesystem_watcher():
    """Start watching configured directories for new logs."""
    watch_path = Path("./watch")  # Configure in config.yaml
    if watch_path.exists():
        observer = Observer()
        observer.schedule(LogFileHandler(), str(watch_path), recursive=True)
        observer.start()
        logger.info(f"Started file system watcher on {watch_path}")
```

### 2. Simple Frontend (`static/index.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CLASSIC Web Service</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .upload-zone {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-zone:hover {
            border-color: #4CAF50;
            background: #f0f8ff;
        }
        .upload-zone.dragover {
            border-color: #4CAF50;
            background: #e8f5e9;
        }
        .status-list {
            margin-top: 20px;
        }
        .status-item {
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            background: #f9f9f9;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .status-pending { border-left: 4px solid #ff9800; }
        .status-queued { border-left: 4px solid #9c27b0; }
        .status-processing {
            border-left: 4px solid #2196F3;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        .status-completed { border-left: 4px solid #4CAF50; }
        .status-failed { border-left: 4px solid #f44336; }
        .report-viewer {
            margin-top: 20px;
            padding: 20px;
            background: #f5f5f5;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            max-height: 500px;
            overflow-y: auto;
        }
        .duplicate-badge {
            background: #ffc107;
            color: #000;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 10px;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #45a049;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        #fileInput {
            display: none;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            flex: 1;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 CLASSIC Crash Log Analyzer</h1>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="queueSize">0</div>
                <div class="stat-label">Queue Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="activeConnections">0</div>
                <div class="stat-label">Active Connections</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="processedToday">0</div>
                <div class="stat-label">Processed Today</div>
            </div>
        </div>

        <div class="upload-zone" id="uploadZone">
            <p>📁 Drag and drop crash logs here or click to browse</p>
            <p style="font-size: 12px; color: #666;">Accepts .log and .txt files (max 100MB)</p>
            <input type="file" id="fileInput" accept=".log,.txt" multiple>
        </div>

        <div class="status-list" id="statusList">
            <h2>Processing Status</h2>
            <div id="statusItems"></div>
        </div>

        <div class="report-viewer" id="reportViewer" style="display: none;">
            <h2>Report</h2>
            <pre id="reportContent"></pre>
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        let ws = null;
        let reconnectTimer = null;

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onopen = () => {
                console.log('WebSocket connected');
                updateConnectionStatus(true);
                if (reconnectTimer) {
                    clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateStatus(data.log_id, data.status, data.data);
                updateStats();
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
                // Reconnect after 3 seconds
                reconnectTimer = setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function updateConnectionStatus(connected) {
            const connections = document.getElementById('activeConnections');
            connections.textContent = connected ? '1' : '0';
            connections.style.color = connected ? '#4CAF50' : '#f44336';
        }

        // Initialize WebSocket connection
        connectWebSocket();

        // File upload handling
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');
        const statusItems = document.getElementById('statusItems');
        const reportViewer = document.getElementById('reportViewer');
        const reportContent = document.getElementById('reportContent');

        // Drag and drop
        uploadZone.addEventListener('click', () => fileInput.click());

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        // File upload function
        async function handleFiles(files) {
            for (const file of files) {
                // Validate file size (100MB max)
                if (file.size > 100 * 1024 * 1024) {
                    alert(`${file.name} is too large (max 100MB)`);
                    continue;
                }

                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/api/logs/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.error) {
                        alert(`Error uploading ${file.name}: ${result.error}`);
                    } else {
                        addStatusItem(result.log_id, file.name, result.status, result.duplicate);
                        updateQueueSize(result.queue_position || 0);
                    }

                } catch (error) {
                    console.error('Upload failed:', error);
                    alert(`Failed to upload ${file.name}`);
                }
            }
        }

        // Status management
        const statusMap = new Map();

        function addStatusItem(logId, filename, status, isDuplicate) {
            // Don't add if already exists
            if (document.getElementById(`status-${logId}`)) {
                updateStatus(logId, status);
                return;
            }

            const item = document.createElement('div');
            item.className = `status-item status-${status}`;
            item.id = `status-${logId}`;
            item.innerHTML = `
                <div>
                    <strong>${filename}</strong>
                    ${isDuplicate ? '<span class="duplicate-badge">DUPLICATE</span>' : ''}
                    <div><small>ID: ${logId}</small></div>
                    <div class="status-text">Status: ${status}</div>
                </div>
                <button onclick="viewReport('${logId}')" style="display: none;" id="btn-${logId}">
                    View Report
                </button>
            `;
            statusItems.insertBefore(item, statusItems.firstChild);
            statusMap.set(logId, { filename, status });

            // If duplicate and completed, show button immediately
            if (isDuplicate && status === 'completed') {
                document.getElementById(`btn-${logId}`).style.display = 'block';
            }
        }

        function updateStatus(logId, status, data) {
            const item = document.getElementById(`status-${logId}`);
            if (item) {
                item.className = `status-item status-${status}`;
                item.querySelector('.status-text').textContent = `Status: ${status}`;

                if (status === 'completed') {
                    const btn = document.getElementById(`btn-${logId}`);
                    if (btn) btn.style.display = 'block';
                    incrementProcessedToday();
                }
            }
        }

        function updateQueueSize(size) {
            document.getElementById('queueSize').textContent = size;
        }

        function incrementProcessedToday() {
            const counter = document.getElementById('processedToday');
            counter.textContent = parseInt(counter.textContent) + 1;
        }

        async function viewReport(logId) {
            try {
                const response = await fetch(`/api/reports/${logId}`);
                const report = await response.json();

                if (report.error) {
                    alert(`Error: ${report.error}`);
                    return;
                }

                // Format the report for display
                let formatted = `Report for Log ID: ${logId}\n`;
                formatted += `Status: ${report.status}\n`;
                formatted += `Timestamp: ${report.timestamp}\n\n`;

                if (report.summary) {
                    formatted += `Summary:\n${report.summary}\n\n`;
                }

                if (report.findings && report.findings.length > 0) {
                    formatted += `Findings:\n`;
                    report.findings.forEach((finding, i) => {
                        formatted += `${i + 1}. ${finding}\n`;
                    });
                }

                reportContent.textContent = formatted;
                reportViewer.style.display = 'block';
                reportViewer.scrollIntoView({ behavior: 'smooth' });

            } catch (error) {
                console.error('Failed to load report:', error);
                alert('Failed to load report');
            }
        }

        // Update stats periodically
        async function updateStats() {
            try {
                const response = await fetch('/health');
                const health = await response.json();

                if (health.queue_size !== undefined) {
                    updateQueueSize(health.queue_size);
                }
            } catch (error) {
                console.error('Failed to update stats:', error);
            }
        }

        // Update stats every 5 seconds
        setInterval(updateStats, 5000);

        // Load recent logs on page load
        async function loadRecentLogs() {
            try {
                const response = await fetch('/api/logs?limit=10');
                const data = await response.json();

                if (data.logs) {
                    data.logs.forEach(log => {
                        addStatusItem(log.log_id, log.filename, log.status, false);
                    });
                }
            } catch (error) {
                console.error('Failed to load recent logs:', error);
            }
        }

        // Load recent logs on startup
        loadRecentLogs();
        updateStats();
    </script>
</body>
</html>
```

### 3. Docker Configuration

#### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CLASSIC library and application code
COPY ClassicLib ./ClassicLib
COPY app.py .
COPY static ./static

# Create necessary directories
RUN mkdir -p uploads reports watch "CLASSIC Data"

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`

```yaml
version: '3.8'

services:
  classic-web:
    build: .
    container_name: classic-web
    ports:
      - "8000:8000"
    volumes:
      # Mount directories for persistence
      - ./uploads:/app/uploads
      - ./reports:/app/reports
      - ./watch:/app/watch
      - ./classic.db:/app/classic.db
      # Mount CLASSIC Data for YAML configs
      - ./CLASSIC Data:/app/CLASSIC Data
    environment:
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### `requirements.txt`

```
# Web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Async database
aiosqlite==0.19.0

# File watching
watchdog==3.0.0

# Async file operations
aiofiles==23.2.1

# WebSocket support
websockets==12.0

# Existing CLASSIC dependencies
pyyaml==6.0.1
packaging==23.2
structlog==23.2.0

# Optional: Rate limiting
slowapi==0.1.9
```

## Key Improvements with Async Database Patterns

### 1. Connection Pooling
- Implements proper connection pooling similar to `AsyncDatabasePool` in the CLASSIC codebase
- Reuses connections efficiently instead of creating new ones for each query
- Handles connection lifecycle and health checks

### 2. Async Database Operations
- All database operations use `async/await` with `aiosqlite`
- No blocking I/O operations that could slow down the web server
- Consistent with CLASSIC's async-first architecture

### 3. Transaction Management
- Proper use of context managers for database connections
- Automatic cleanup on errors
- Connection recycling to the pool

### 4. Performance Features
- In-memory result caching for frequently accessed data
- File hash-based deduplication to avoid reprocessing
- Database indexes for common queries
- Batch operations where applicable

### 5. Error Handling
- Graceful degradation with file system fallback
- Connection health checks
- Automatic reconnection on connection loss

## Deployment Instructions

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/classic-web.git
cd classic-web

# Copy your CLASSIC library
cp -r /path/to/CLASSIC-Fallout4/ClassicLib .

# Start the service
docker-compose up -d

# Service is now running at http://localhost:8000
```

### Production Deployment

For production, add these environment variables to `docker-compose.yml`:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - LOG_LEVEL=INFO
  - MAX_CONNECTIONS=10  # Database pool size
  - MAX_UPLOAD_SIZE_MB=100
  - CLEANUP_DAYS=30  # Auto-cleanup old files
```

## Monitoring

The system provides built-in monitoring through the `/health` endpoint:

```bash
# Check health status
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "queue_size": 2,
  "active_websockets": 5,
  "database": "connected"
}
```

## API-Only Mode & External Integrations

### Configuration for API-Only Mode

The service can run in API-only mode for container-to-container communication and external integrations. This mode disables the web UI and focuses purely on API endpoints.

#### Environment Variables

```yaml
# docker-compose.yml for API-only mode
environment:
  - API_ONLY_MODE=true           # Disable web UI
  - ENABLE_LOG_PERSISTENCE=false # Don't store logs/reports (stateless processing)
  - ENABLE_AUTH_PERSISTENCE=true # ALWAYS persist API keys (required)
  - ENABLE_WEBSOCKET=false       # Optional: Disable WebSocket
  - API_KEY_REQUIRED=true        # Require API authentication
  - API_KEY_STORAGE=volume       # Options: volume, file, env
  - CORS_ORIGINS=*               # Configure CORS for external access
```

#### Important: API Key Persistence Strategy

Even in "stateless" mode, API keys MUST persist across container restarts. The system uses a hybrid approach:

1. **Authentication Data** (Always Persistent):
   - API keys stored in Docker volume or mounted file
   - Survives container restarts
   - Critical for maintaining service continuity

2. **Processing Data** (Optional Persistence):
   - Crash logs and reports can be ephemeral
   - Reduces storage requirements
   - Suitable for high-volume processing

#### Modified Application Startup (`app.py`)

```python
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import json

# Configuration from environment
API_ONLY_MODE = os.getenv("API_ONLY_MODE", "false").lower() == "true"
ENABLE_LOG_PERSISTENCE = os.getenv("ENABLE_LOG_PERSISTENCE", "true").lower() == "true"
ENABLE_AUTH_PERSISTENCE = os.getenv("ENABLE_AUTH_PERSISTENCE", "true").lower() == "true"
ENABLE_WEBSOCKET = os.getenv("ENABLE_WEBSOCKET", "true").lower() == "true"
API_KEY_REQUIRED = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
API_KEY_STORAGE = os.getenv("API_KEY_STORAGE", "volume")  # volume, file, or env

# API Key Storage Implementation
class APIKeyStore:
    """Manages API key persistence across different storage backends."""

    def __init__(self, storage_type: str = "volume"):
        self.storage_type = storage_type
        self.keys = {}

        if storage_type == "volume":
            # Docker volume mount point
            self.storage_path = Path("/data/api_keys.json")
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        elif storage_type == "file":
            # Local file storage
            self.storage_path = Path("./api_keys.json")
        elif storage_type == "env":
            # Environment variables (less secure, not recommended for production)
            self.keys = self._load_from_env()

        if storage_type in ["volume", "file"]:
            self.load_keys()

    def _load_from_env(self) -> dict:
        """Load API keys from environment variables."""
        keys = {}
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            for key in api_keys_str.split(","):
                if key.strip():
                    keys[key.strip()] = {
                        "name": "env_key",
                        "permissions": ["read", "write"],
                        "active": True
                    }
        return keys

    def load_keys(self):
        """Load API keys from persistent storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    self.keys = json.load(f)
                logger.info(f"Loaded {len(self.keys)} API keys from {self.storage_path}")
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")
                self.keys = {}
        else:
            # Initialize with default key on first run
            self._initialize_default_keys()

    def _initialize_default_keys(self):
        """Create initial API keys on first run."""
        import secrets

        # Generate admin key
        admin_key = secrets.token_urlsafe(32)
        self.keys[admin_key] = {
            "name": "admin",
            "permissions": ["*"],
            "created_at": datetime.now().isoformat(),
            "active": True
        }

        # Save to persistent storage
        self.save_keys()

        # Display the key (only on first run)
        print("=" * 60)
        print("INITIAL ADMIN API KEY GENERATED")
        print(f"Key: {admin_key}")
        print("SAVE THIS KEY - It won't be shown again!")
        print("=" * 60)

    def save_keys(self):
        """Save API keys to persistent storage."""
        if self.storage_type in ["volume", "file"]:
            try:
                with open(self.storage_path, 'w') as f:
                    json.dump(self.keys, f, indent=2)
                logger.info(f"Saved {len(self.keys)} API keys to {self.storage_path}")
            except Exception as e:
                logger.error(f"Failed to save API keys: {e}")

    def add_key(self, key: str, metadata: dict):
        """Add a new API key."""
        self.keys[key] = metadata
        self.save_keys()

    def revoke_key(self, key: str):
        """Revoke an API key."""
        if key in self.keys:
            self.keys[key]["active"] = False
            self.save_keys()

    def verify_key(self, key: str) -> dict:
        """Verify an API key and return its metadata."""
        return self.keys.get(key)

# Initialize API key store
api_key_store = APIKeyStore(storage_type=API_KEY_STORAGE)

app = FastAPI(
    title="CLASSIC API Service",
    description="Crash Log Analysis Service" if API_ONLY_MODE else "CLASSIC Web Service",
    docs_url="/api/docs" if not API_ONLY_MODE else "/docs",
    redoc_url="/api/redoc" if not API_ONLY_MODE else "/redoc"
)

# CORS configuration for external access
if API_ONLY_MODE:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# API Key Authentication
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for protected endpoints."""
    if not API_KEY_REQUIRED:
        return True
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True

# Conditional mounting of static files
if not API_ONLY_MODE:
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def root():
        """Serve the main web interface."""
        return HTMLResponse(content=open("static/index.html").read())

# Stateless processing option
class StatelessLogProcessor:
    """Handles crash log processing without persistence."""

    async def process_log_direct(self, content: str) -> dict:
        """Process log content directly without storing."""
        orchestrator = OrchestratorCore(
            yamldata=self.yamldata,
            crashlogs=self.crashlogs,
            fcx_mode=False,
            show_formid_values=True,
            formid_db_exists=True
        )

        result = await orchestrator.process_crash_log(content)

        return {
            "status": "completed",
            "findings": result.get("findings", []),
            "summary": result.get("summary", ""),
            "timestamp": datetime.now().isoformat()
        }
```

### API Endpoints for External Applications

#### Synchronous Processing Endpoint

```python
@app.post("/api/v1/analyze", dependencies=[Depends(verify_api_key)])
async def analyze_log_sync(
    file: UploadFile,
    wait_for_result: bool = True,
    timeout: int = 30
):
    """
    Analyze a crash log synchronously.
    Perfect for Discord bots and other integrations that need immediate results.
    """
    content = await file.read()

    if not ENABLE_PERSISTENCE or wait_for_result:
        # Direct processing without persistence
        processor = StatelessLogProcessor()
        result = await processor.process_log_direct(
            content.decode('utf-8', errors='ignore')
        )
        return result
    else:
        # Queue for async processing
        log_id = str(uuid4())
        await processing_queue.put((log_id, content))
        return {
            "log_id": log_id,
            "status": "queued",
            "message": "Use /api/v1/status/{log_id} to check progress"
        }

@app.post("/api/v1/analyze/text", dependencies=[Depends(verify_api_key)])
async def analyze_log_text(request: dict):
    """
    Analyze crash log from text content (no file upload).
    Useful for integrations that have the log content in memory.
    """
    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")

    processor = StatelessLogProcessor()
    result = await processor.process_log_direct(content)
    return result
```

#### Webhook Support for Async Processing

```python
@app.post("/api/v1/analyze/webhook", dependencies=[Depends(verify_api_key)])
async def analyze_with_webhook(
    file: UploadFile,
    webhook_url: str,
    webhook_headers: dict = None
):
    """
    Process log asynchronously and send results to webhook.
    Perfect for Discord bots that can wait for webhook responses.
    """
    content = await file.read()
    log_id = str(uuid4())

    # Store webhook info for callback
    webhook_callbacks[log_id] = {
        "url": webhook_url,
        "headers": webhook_headers or {}
    }

    await processing_queue.put((log_id, content))

    return {
        "log_id": log_id,
        "status": "processing",
        "webhook": webhook_url
    }

async def send_webhook(log_id: str, result: dict):
    """Send processing results to registered webhook."""
    if log_id in webhook_callbacks:
        webhook = webhook_callbacks[log_id]
        async with aiohttp.ClientSession() as session:
            await session.post(
                webhook["url"],
                json=result,
                headers=webhook["headers"]
            )
        del webhook_callbacks[log_id]
```

### Discord Bot Integration Example

```python
# discord_bot.py - Example Discord bot integration
import discord
from discord.ext import commands
import aiohttp
import io

bot = commands.Bot(command_prefix='!')
CLASSIC_API_URL = "http://classic-api:8000"  # Container name in docker-compose
API_KEY = "your-api-key-here"

@bot.command(name='analyze')
async def analyze_crash_log(ctx):
    """Analyze attached crash log files."""
    if not ctx.message.attachments:
        await ctx.send("Please attach a crash log file.")
        return

    attachment = ctx.message.attachments[0]

    # Download the file
    file_content = await attachment.read()

    # Send to CLASSIC API
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('file',
                      file_content,
                      filename=attachment.filename,
                      content_type='text/plain')

        headers = {"X-API-Key": API_KEY}

        async with session.post(
            f"{CLASSIC_API_URL}/api/v1/analyze",
            data=data,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()

                # Format and send results
                embed = discord.Embed(
                    title="Crash Log Analysis",
                    color=0x00ff00 if result["status"] == "completed" else 0xff0000
                )

                if result.get("summary"):
                    embed.add_field(
                        name="Summary",
                        value=result["summary"][:1024],
                        inline=False
                    )

                if result.get("findings"):
                    findings_text = "\n".join(result["findings"][:5])
                    embed.add_field(
                        name="Top Findings",
                        value=findings_text[:1024],
                        inline=False
                    )

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Error analyzing log: {response.status}")

@bot.command(name='analyze_webhook')
async def analyze_with_webhook(ctx):
    """Analyze using webhook for async processing."""
    if not ctx.message.attachments:
        await ctx.send("Please attach a crash log file.")
        return

    attachment = ctx.message.attachments[0]
    file_content = await attachment.read()

    # Create webhook for response
    webhook = await ctx.channel.create_webhook(name="CLASSIC-Report")

    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=attachment.filename)
        data.add_field('webhook_url', webhook.url)

        headers = {"X-API-Key": API_KEY}

        async with session.post(
            f"{CLASSIC_API_URL}/api/v1/analyze/webhook",
            data=data,
            headers=headers
        ) as response:
            if response.status == 200:
                await ctx.send("Processing... Results will appear when ready.")
            else:
                await ctx.send(f"Error: {response.status}")

    # Webhook will automatically post results when ready

bot.run('YOUR_DISCORD_BOT_TOKEN')
```

### Container-to-Container Docker Compose

```yaml
# docker-compose.yml for multi-container setup
version: '3.8'

services:
  # CLASSIC API Service (API-only mode)
  classic-api:
    build: ./classic-api
    container_name: classic-api
    environment:
      - API_ONLY_MODE=true
      - ENABLE_LOG_PERSISTENCE=false  # No log/report storage
      - ENABLE_AUTH_PERSISTENCE=true  # ALWAYS persist API keys
      - API_KEY_STORAGE=volume        # Use Docker volume for keys
      - API_KEY_REQUIRED=true
    volumes:
      # Persistent volume for API keys - survives container restarts
      - api_keys_data:/data
      # Optional: Mount local file for key backup
      # - ./api_keys_backup.json:/data/api_keys.json
    ports:
      - "8000:8000"  # Only expose if needed externally
    networks:
      - app-network
    restart: unless-stopped

volumes:
  # Named volume for API key persistence
  api_keys_data:
    driver: local

  # Discord Bot Container
  discord-bot:
    build: ./discord-bot
    container_name: discord-bot
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - CLASSIC_API_URL=http://classic-api:8000
      - CLASSIC_API_KEY=${CLASSIC_API_KEY}
    depends_on:
      - classic-api
    networks:
      - app-network
    restart: unless-stopped

  # Optional: Web UI Container (separate)
  classic-web:
    build: ./classic-web
    container_name: classic-web
    ports:
      - "3000:3000"
    environment:
      - API_BASE_URL=http://classic-api:8000
    depends_on:
      - classic-api
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
```

### OpenAPI Documentation

The API automatically generates OpenAPI/Swagger documentation:

```python
from fastapi import FastAPI
from pydantic import BaseModel

class LogAnalysisRequest(BaseModel):
    content: str
    options: dict = {}

class LogAnalysisResponse(BaseModel):
    status: str
    findings: list[str]
    summary: str
    timestamp: str
    metadata: dict = {}

@app.post(
    "/api/v1/analyze/text",
    response_model=LogAnalysisResponse,
    summary="Analyze crash log from text",
    description="Process crash log content directly without file upload",
    tags=["Analysis"]
)
async def analyze_log_text(request: LogAnalysisRequest):
    """Full documentation is auto-generated at /docs"""
    pass
```

### Rate Limiting for API Mode

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Different limits for different endpoints
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/analyze")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def analyze_log_sync(file: UploadFile):
    pass

@app.post("/api/v1/analyze/batch")
@limiter.limit("5/hour")  # 5 batch requests per hour
async def analyze_batch(files: list[UploadFile]):
    pass
```

### Stateless Scaling with Docker Swarm

```yaml
# docker-stack.yml for Docker Swarm deployment
version: '3.8'

services:
  classic-api:
    image: classic-api:latest
    deploy:
      replicas: 3  # Scale to 3 instances
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    environment:
      - API_ONLY_MODE=true
      - ENABLE_PERSISTENCE=false  # Stateless for scaling
    ports:
      - "8000:8000"
    networks:
      - classic-network

networks:
  classic-network:
    driver: overlay
```

### API Key Management

**CRITICAL**: API keys MUST persist even in "stateless" processing mode. The system separates authentication persistence from log/report persistence.

#### Persistence Architecture

```yaml
# Persistence is separated into two concerns:
persistence:
  authentication:  # ALWAYS PERSISTENT
    - api_keys     # Must survive restarts
    - admin_tokens # Must survive restarts
    - rate_limits  # Can be ephemeral

  processing:      # OPTIONALLY PERSISTENT
    - crash_logs   # Can be ephemeral
    - reports      # Can be ephemeral
    - queue_state  # Can be ephemeral
```

#### Docker Volume Strategy

```yaml
# Recommended docker-compose.yml setup
services:
  classic-api:
    volumes:
      # Critical: API keys always persist
      - api_keys:/data/auth        # Named volume (survives container removal)
      # Optional: Processing data
      - ./temp:/tmp/processing     # Bind mount (can be tmpfs)
    environment:
      - API_KEY_STORAGE=volume      # Use Docker volume
      - API_KEY_PATH=/data/auth     # Persistent path

volumes:
  api_keys:  # This volume persists even if container is removed
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /secure/location/api_keys  # Secure host location
```

Server operators have multiple options for generating and managing API keys:

#### 1. Environment Variable Method (Simple)

```bash
# Generate random API keys using command line
openssl rand -hex 32
# or
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env file
echo "API_KEYS=key1_here,key2_here,key3_here" >> .env

# Or set in docker-compose.yml
environment:
  - API_KEYS=${API_KEYS:-default_key_for_dev}
```

#### 2. CLI Management Tool

```python
# manage_api_keys.py - API Key management CLI
import click
import secrets
import json
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite

@click.group()
def cli():
    """CLASSIC API Key Management"""
    pass

@cli.command()
@click.option('--name', required=True, help='Name/description for the key')
@click.option('--expires-days', default=365, help='Days until expiration')
def generate(name: str, expires_days: int):
    """Generate a new API key."""
    key = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=expires_days)

    # Store in keys.json or database
    keys_file = Path("api_keys.json")
    if keys_file.exists():
        keys = json.loads(keys_file.read_text())
    else:
        keys = {}

    keys[key] = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "active": True
    }

    keys_file.write_text(json.dumps(keys, indent=2))

    click.echo(f"Generated API Key for '{name}':")
    click.echo(f"Key: {key}")
    click.echo(f"Expires: {expires_at}")

@cli.command()
def list():
    """List all API keys."""
    keys_file = Path("api_keys.json")
    if not keys_file.exists():
        click.echo("No API keys found.")
        return

    keys = json.loads(keys_file.read_text())
    for key, info in keys.items():
        status = "Active" if info["active"] else "Revoked"
        click.echo(f"{info['name']}: {key[:8]}... [{status}] Expires: {info['expires_at']}")

@cli.command()
@click.argument('key_prefix')
def revoke(key_prefix: str):
    """Revoke an API key."""
    keys_file = Path("api_keys.json")
    keys = json.loads(keys_file.read_text())

    for key in keys:
        if key.startswith(key_prefix):
            keys[key]["active"] = False
            keys_file.write_text(json.dumps(keys, indent=2))
            click.echo(f"Revoked key: {key[:8]}...")
            return

    click.echo("Key not found.")

if __name__ == "__main__":
    cli()
```

#### 3. Admin API Endpoints (With Authentication)

```python
from fastapi import Depends, HTTPException
from datetime import datetime, timedelta
import secrets

# Admin authentication
async def verify_admin(admin_token: str = Header(None)):
    """Verify admin access for key management."""
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    if not ADMIN_TOKEN or admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True

@app.post("/admin/api-keys/generate", dependencies=[Depends(verify_admin)])
async def generate_api_key(
    name: str,
    expires_days: int = 365,
    permissions: list[str] = ["read", "write"]
):
    """Generate a new API key (admin only)."""
    key = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=expires_days)

    # Store in database
    if ENABLE_PERSISTENCE:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO api_keys (key, name, permissions, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, name, json.dumps(permissions), expires_at, datetime.now()))
            await conn.commit()
    else:
        # Store in memory or config file
        API_KEYS_STORE[key] = {
            "name": name,
            "permissions": permissions,
            "expires_at": expires_at
        }

    return {
        "key": key,
        "name": name,
        "expires_at": expires_at.isoformat(),
        "permissions": permissions
    }

@app.get("/admin/api-keys", dependencies=[Depends(verify_admin)])
async def list_api_keys():
    """List all API keys (admin only)."""
    if ENABLE_PERSISTENCE:
        async with db_pool.acquire() as conn:
            async with conn.execute("""
                SELECT key, name, created_at, expires_at, last_used, active
                FROM api_keys
                ORDER BY created_at DESC
            """) as cursor:
                keys = []
                async for row in cursor:
                    keys.append({
                        "key": row[0][:8] + "...",  # Show only prefix
                        "name": row[1],
                        "created_at": row[2],
                        "expires_at": row[3],
                        "last_used": row[4],
                        "active": row[5]
                    })
                return keys
    else:
        return [{"key": k[:8] + "...", **v} for k, v in API_KEYS_STORE.items()]

@app.delete("/admin/api-keys/{key_prefix}", dependencies=[Depends(verify_admin)])
async def revoke_api_key(key_prefix: str):
    """Revoke an API key by prefix (admin only)."""
    # Implementation similar to CLI revoke
    pass
```

#### 4. Database Schema for API Keys

```sql
-- Add to database initialization
CREATE TABLE IF NOT EXISTS api_keys (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    permissions JSON DEFAULT '["read"]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    metadata JSON
);

CREATE INDEX idx_api_keys_active ON api_keys(active);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at);
```

#### 5. Enhanced API Key Verification

```python
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=100)
async def get_api_key_info(api_key: str) -> dict:
    """Get API key information with caching."""
    if ENABLE_PERSISTENCE:
        async with db_pool.acquire() as conn:
            async with conn.execute(
                "SELECT * FROM api_keys WHERE key = ? AND active = TRUE",
                (api_key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
    else:
        return API_KEYS_STORE.get(api_key)
    return None

async def verify_api_key_enhanced(x_api_key: str = Header(None)):
    """Enhanced API key verification with expiration and permissions."""
    if not API_KEY_REQUIRED:
        return {"permissions": ["*"]}

    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_info = await get_api_key_info(x_api_key)

    if not key_info:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Check expiration
    if key_info.get("expires_at"):
        expires = datetime.fromisoformat(key_info["expires_at"])
        if datetime.now() > expires:
            raise HTTPException(status_code=403, detail="API key expired")

    # Update usage statistics
    if ENABLE_PERSISTENCE:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE api_keys SET last_used = ?, usage_count = usage_count + 1 WHERE key = ?",
                (datetime.now(), x_api_key)
            )
            await conn.commit()

    return key_info
```

#### 6. Docker Startup Script for Key Generation

```bash
#!/bin/bash
# startup.sh - Generate API keys on first run

if [ ! -f /app/api_keys.json ]; then
    echo "Generating initial API keys..."

    # Generate default admin key
    ADMIN_KEY=$(openssl rand -hex 32)
    echo "Admin API Key: $ADMIN_KEY"
    echo "SAVE THIS KEY - it won't be shown again!"

    # Generate service keys
    SERVICE_KEY=$(openssl rand -hex 32)

    # Create initial keys file
    cat > /app/api_keys.json <<EOF
{
  "$ADMIN_KEY": {
    "name": "admin",
    "permissions": ["*"],
    "created_at": "$(date -Iseconds)"
  },
  "$SERVICE_KEY": {
    "name": "service",
    "permissions": ["read", "write"],
    "created_at": "$(date -Iseconds)"
  }
}
EOF
fi

# Start the application
exec uvicorn app:app --host 0.0.0.0 --port 8000
```

#### 7. Web UI for Key Management (Optional)

```html
<!-- admin.html - Simple admin interface -->
<!DOCTYPE html>
<html>
<head>
    <title>API Key Management</title>
</head>
<body>
    <h1>API Key Management</h1>

    <div id="generateKey">
        <h2>Generate New Key</h2>
        <input type="text" id="keyName" placeholder="Key name/description">
        <input type="number" id="expireDays" value="365" placeholder="Days until expiration">
        <button onclick="generateKey()">Generate</button>
    </div>

    <div id="keyList">
        <h2>Active Keys</h2>
        <table id="keysTable">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Key (prefix)</th>
                    <th>Created</th>
                    <th>Expires</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
    </div>

    <script>
        const ADMIN_TOKEN = prompt("Enter admin token:");

        async function generateKey() {
            const name = document.getElementById('keyName').value;
            const days = document.getElementById('expireDays').value;

            const response = await fetch('/admin/api-keys/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Admin-Token': ADMIN_TOKEN
                },
                body: JSON.stringify({
                    name: name,
                    expires_days: parseInt(days)
                })
            });

            const result = await response.json();
            if (response.ok) {
                alert(`Generated key: ${result.key}\n\nSAVE THIS KEY - it won't be shown again!`);
                loadKeys();
            }
        }

        async function loadKeys() {
            const response = await fetch('/admin/api-keys', {
                headers: {'Admin-Token': ADMIN_TOKEN}
            });
            const keys = await response.json();

            const tbody = document.querySelector('#keysTable tbody');
            tbody.innerHTML = keys.map(key => `
                <tr>
                    <td>${key.name}</td>
                    <td>${key.key}</td>
                    <td>${key.created_at}</td>
                    <td>${key.expires_at || 'Never'}</td>
                    <td><button onclick="revokeKey('${key.key}')">Revoke</button></td>
                </tr>
            `).join('');
        }

        loadKeys();
    </script>
</body>
</html>
```

### API Client Libraries

#### Python Client Example

```python
# classic_api_client.py
import aiohttp
from typing import Optional

class ClassicAPIClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}

    async def analyze_file(self, file_path: str) -> dict:
        """Analyze a crash log file."""
        async with aiohttp.ClientSession() as session:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=file_path)

                async with session.post(
                    f"{self.base_url}/api/v1/analyze",
                    data=data,
                    headers=self.headers
                ) as response:
                    return await response.json()

    async def analyze_text(self, content: str) -> dict:
        """Analyze crash log content."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/analyze/text",
                json={"content": content},
                headers=self.headers
            ) as response:
                return await response.json()

# Usage
client = ClassicAPIClient("http://localhost:8000", api_key="your-key")
result = await client.analyze_file("crash.log")
```

## Conclusion

This implementation provides a flexible, scalable solution for crash log analysis with multiple deployment options:

### Core Features

1. **Proper Async Patterns**: Uses `aiosqlite` with connection pooling, consistent with CLASSIC's architecture
2. **Simple Deployment**: Single `docker-compose up -d` command for full stack
3. **Minimal Dependencies**: SQLite instead of PostgreSQL, no external message queue required
4. **Performance**: Connection pooling, caching, and async I/O for optimal performance
5. **Reliability**: Database transactions, error handling, and fallback mechanisms
6. **Monitoring**: Built-in health checks and statistics

### API-First Features

7. **API-Only Mode**: Run without web UI for container-to-container communication
8. **Stateless Operation**: Optional persistence allows horizontal scaling
9. **External Integrations**: Ready-made examples for Discord bots and other services
10. **Authentication**: API key support for secure external access
11. **Webhook Support**: Async processing with callback notifications
12. **OpenAPI Documentation**: Auto-generated API documentation at `/docs`

### Deployment Flexibility

The system can be deployed in multiple configurations:

- **Full Stack Mode**: Web UI + API with persistence (default)
- **API-Only Mode**: Lightweight API service for integrations
- **Stateless Mode**: No persistence for easy scaling
- **Multi-Container**: Separate API, UI, and bot containers
- **Docker Swarm**: Scale horizontally with replicas

### Use Cases

Perfect for:
- **Web Users**: Drag-and-drop crash log analysis via browser
- **Discord Communities**: Bot integration for instant analysis
- **Game Launchers**: Direct API integration for crash reporting
- **Mod Managers**: Automated crash log processing
- **CI/CD Pipelines**: Automated testing of game stability
- **Microservices**: Container-to-container crash analysis

The system leverages CLASSIC's existing async infrastructure while providing maximum flexibility for different deployment scenarios and use cases.
