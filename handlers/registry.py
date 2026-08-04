from __future__ import annotations
import logging
from typing import Any, Awaitable, Callable, Dict, Optional
from fastapi import WebSocket
from models import SessionData

logger = logging.getLogger("smartschool.handlers")

ActionHandler = Callable[
    [WebSocket, Dict[str, Any], Optional[SessionData]],
    Awaitable[None],
]

_handlers: Dict[str, ActionHandler] = {}


def ws_action(name: str):
    def decorator(func: ActionHandler) -> ActionHandler:
        _handlers[name] = func
        logger.debug("Registered WS handler: %s", name)
        return func
    return decorator


def get_handler(action: str) -> Optional[ActionHandler]:
    return _handlers.get(action)