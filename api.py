import json
"""
KING ZARRY AI - WEB API
WEB ONLY - Secure Neon authentication and web chat

- Uses Neon PostgreSQL via DATABASE_URL
- Never touches Telegram SQLite databases
- Never instantiates Memory() for web requests
- Uses secure scrypt password hashing
- Uses hashed session tokens in web_sessions
- Uses HttpOnly session cookies
- Protects /api/chat with authentication
- Uses a web-only memory adapter for AIEngine
- NEW: Injects live market data for BTC/ETH/SOL/XAU/UNI
- NEW: Supports image upload via base64 in /api/chat
- FIXED: WebMemoryAdapter.add_message now writes to web_messages (matches get_history)
"""

import os
import re
import hmac
import base64
import hashlib
import secrets
import asyncio
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
import uvicorn
