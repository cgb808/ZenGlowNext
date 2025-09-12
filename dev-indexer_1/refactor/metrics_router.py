"""
WebSocket metrics streaming endpoint for real-time dashboard monitoring.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ..health.health_router import get_model_registry, get_query_stats_snapshot
from ..health.system_metrics import get_system_metrics

metrics_router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast metrics data to all connected clients."""
        message = json.dumps(data)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)


manager = ConnectionManager()


@metrics_router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket, interval: int = 5):
    """WebSocket endpoint for streaming real-time metrics.

    Query Parameters:
        interval: seconds between updates (min 1 / max 30)
    """
    # Clamp interval for safety
    update_interval = max(1, min(30, int(interval)))
    await manager.connect(websocket)

    try:
        while True:
            metrics_data = {
                "timestamp": time.time(),
                "query_stats": get_query_stats_snapshot(),
                "models": get_model_registry(),
                "system": get_system_metrics(),
                "type": "metrics_update",
                "interval": update_interval,
            }
            await websocket.send_text(json.dumps(metrics_data))
            await asyncio.sleep(update_interval)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@metrics_router.get("/ws/metrics/status")
def websocket_status() -> Dict[str, Any]:
    """Get current WebSocket connection status."""
    return {
        "active_connections": len(manager.active_connections),
        "endpoint": "/ws/metrics",
        "update_interval_seconds": 5,
    }
