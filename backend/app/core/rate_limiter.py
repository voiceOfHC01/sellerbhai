import time
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter for security hardening.
    Protects login endpoints against brute force, webhooks against CPU exhaustion,
    and chat endpoints against volumetric token drain.
    """
    def __init__(self, app):
        super().__init__(app)
        # Store map: (ip, route_type) -> list of timestamp floats
        self.request_history: Dict[Tuple[str, str], List[float]] = {}
        # Route rate limits: (prefix, max_requests, window_seconds)
        self.limits = [
            ("/api/auth/login", 10, 60),      # 10 attempts per minute
            ("/api/webhooks/meta", 600, 60),  # 600 webhook events per minute (protects against Meta burst drops)
            ("/api/chat/message", 40, 60),    # 40 messages per minute
            ("/api/", 200, 60),               # 200 general requests per minute
        ]

    async def dispatch(self, request: Request, call_next):
        # Allow health checks and static files freely
        path = request.url.path
        if path == "/health" or not path.startswith("/api/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        # Find matching rate limit rule
        rule_prefix = "/api/"
        max_requests = 200
        window_seconds = 60

        for prefix, limit, window in self.limits:
            if path.startswith(prefix):
                rule_prefix = prefix
                max_requests = limit
                window_seconds = window
                break

        key = (client_ip, rule_prefix)
        history = self.request_history.get(key, [])

        # Filter out timestamps older than the window
        valid_history = [t for t in history if now - t < window_seconds]

        if len(valid_history) >= max_requests:
            retry_after = int(window_seconds - (now - valid_history[0]))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded for {rule_prefix}. Please wait {retry_after} seconds before retrying.",
                    "error": "RATE_LIMIT_EXCEEDED",
                    "retry_after_seconds": max(1, retry_after)
                },
                headers={"Retry-After": str(max(1, retry_after))}
            )

        valid_history.append(now)
        self.request_history[key] = valid_history

        # Occasional cleanup to avoid unbounded memory growth
        if len(self.request_history) > 5000:
            cleaned = {}
            for k, timestamps in self.request_history.items():
                v = [t for t in timestamps if now - t < 120]
                if v:
                    cleaned[k] = v
            self.request_history = cleaned

        return await call_next(request)
