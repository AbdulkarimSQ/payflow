"""
PayFlow Rate Limiter — Brute force protection
"""
from collections import defaultdict
import time


class RateLimiter:
    def __init__(self, max_attempts=5, window_seconds=900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)

    def is_limited(self, key):
        now = time.time()
        self.attempts[key] = [
            t for t in self.attempts[key]
            if now - t < self.window_seconds
        ]
        if not self.attempts[key]:
            del self.attempts[key]
            return False
        return len(self.attempts[key]) >= self.max_attempts

    def record(self, key):
        self.attempts[key].append(time.time())

    def reset(self, key):
        self.attempts.pop(key, None)


login_limiter = RateLimiter(max_attempts=5, window_seconds=900)