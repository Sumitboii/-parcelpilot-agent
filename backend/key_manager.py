"""
key_manager.py — High-Performance Multi-Key Pool & Health Checker for Groq API.

Features:
  1. Multi-Key Discovery: Discovers keys from GROQ_API_KEY, GROQ_API_KEYS,
     GROQ_API_KEY_1..N, BACKUP_GROQ_API_KEYS, etc.
  2. Zero-Latency Selection: In-memory O(1) selection using Least-Recently-Used (LRU)
     and Round-Robin to distribute load across all available keys without adding
     any network overhead to AI queries.
  3. Step Function / Dynamic Failover: Automatically marks rate-limited (429) keys
     with cooldown and immediately steps to the next available healthy key.
  4. Concurrent Background Health Prober: Probes keys in parallel to verify health
     and automatically recovers rate-limited keys once their cooldown expires.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv, dotenv_values
from groq import AsyncGroq, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)

# Default cooldown duration in seconds when a 429 rate limit is encountered
DEFAULT_RATE_LIMIT_COOLDOWN = 60.0
# Timeout for background health probe pings
PROBE_TIMEOUT_SECONDS = 6.0


@dataclass
class KeyHealthInfo:
    api_key: str
    key_index: int
    masked_key: str
    client: AsyncGroq = field(repr=False)
    status: str = "HEALTHY"  # "HEALTHY" | "RATE_LIMITED" | "ERROR"
    rate_limit_reset_at: float = 0.0
    last_used_at: float = 0.0
    last_checked_at: float = 0.0
    last_latency_ms: float = 0.0
    consecutive_errors: int = 0
    total_requests: int = 0
    last_error_message: str | None = None

    @property
    def is_available(self) -> bool:
        """Returns True if the key is ready for requests."""
        now = time.time()
        if self.status == "RATE_LIMITED":
            if now >= self.rate_limit_reset_at:
                return True  # Cooldown passed, candidate for recovery
            return False
        return self.status != "ERROR" or self.consecutive_errors < 3

    def to_dict(self) -> dict[str, Any]:
        now = time.time()
        cooldown_remaining = max(0.0, self.rate_limit_reset_at - now) if self.status == "RATE_LIMITED" else 0.0
        return {
            "key_index": self.key_index,
            "masked_key": self.masked_key,
            "status": "HEALTHY" if (self.status == "RATE_LIMITED" and cooldown_remaining == 0) else self.status,
            "is_available": self.is_available,
            "cooldown_remaining_sec": round(cooldown_remaining, 1),
            "total_requests": self.total_requests,
            "consecutive_errors": self.consecutive_errors,
            "last_latency_ms": round(self.last_latency_ms, 2),
            "last_used_seconds_ago": round(now - self.last_used_at, 1) if self.last_used_at > 0 else None,
            "last_error": self.last_error_message,
        }


class GroqKeyPoolManager:
    """
    Manages a pool of Groq API keys, monitoring health and providing instant,
    zero-latency selection of the best healthy key for incoming queries.
    """

    def __init__(self, explicit_keys: list[str] | None = None) -> None:
        self._keys: list[KeyHealthInfo] = []
        self._lock = asyncio.Lock()
        self._round_robin_idx = 0
        self._bg_task: asyncio.Task | None = None
        self.reload_keys(explicit_keys=explicit_keys)

    def _mask_key(self, key: str) -> str:
        if len(key) <= 12:
            return f"***{key[-4:]}"
        return f"{key[:7]}...{key[-4:]}"

    def reload_keys(self, explicit_keys: list[str] | None = None) -> list[str]:
        """
        Scan environment variables and .env file for all Groq API keys.
        Supports:
          - GROQ_API_KEY
          - GROQ_API_KEYS (comma or newline separated)
          - GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3...
          - BACKUP_GROQ_API_KEYS
          - Any env var matching GROQ_.*KEY.*
        """
        if explicit_keys is not None:
            found_keys = [k for k in explicit_keys if k and k.startswith("gsk_")]
        else:
            # Ensure latest .env is loaded
            load_dotenv(override=True)

            found_keys = []


        def add_key_candidates(val: str | None) -> None:
            if not val:
                return
            for raw in re.split(r"[,;\n\s]+", str(val)):
                k = raw.strip().strip("'\"")
                if k and k.startswith("gsk_") and "your_groq_api_key_here" not in k:
                    if k not in found_keys:
                        found_keys.append(k)

        # Check explicit env vars
        add_key_candidates(os.environ.get("GROQ_API_KEY"))
        add_key_candidates(os.environ.get("GROQ_API_KEYS"))
        add_key_candidates(os.environ.get("BACKUP_GROQ_API_KEYS"))

        # Scan for numbered keys (GROQ_API_KEY_1..50) and regex matches in os.environ
        for var_name, var_val in os.environ.items():
            if re.match(r"^GROQ_API_KEY_\d+$", var_name, re.IGNORECASE) or (
                "GROQ" in var_name.upper() and "KEY" in var_name.upper()
            ):
                add_key_candidates(var_val)

        # Also inspect .env file directly if available in current or parent dirs
        for env_path in [".env", "parcelpilot-agent/.env", "../.env", "D:/Project/CalQuity.AI/.env", "D:/Project/CalQuity.AI/parcelpilot-agent/.env"]:
            if os.path.exists(env_path):
                env_dict = dotenv_values(env_path)
                for k, v in env_dict.items():
                    if "GROQ" in k.upper() and "KEY" in k.upper():
                        add_key_candidates(v)

        # Reconcile with existing pool
        existing_by_key = {item.api_key: item for item in self._keys}
        new_pool: list[KeyHealthInfo] = []

        for idx, key_str in enumerate(found_keys):
            if key_str in existing_by_key:
                info = existing_by_key[key_str]
                info.key_index = idx + 1
                new_pool.append(info)
            else:
                client = AsyncGroq(api_key=key_str, max_retries=0, timeout=30.0)
                info = KeyHealthInfo(
                    api_key=key_str,
                    key_index=idx + 1,
                    masked_key=self._mask_key(key_str),
                    client=client,
                )
                new_pool.append(info)

        self._keys = new_pool
        logger.info("🔑 GroqKeyPoolManager loaded %d Groq API key(s)", len(self._keys))
        return found_keys

    @property
    def total_keys(self) -> int:
        return len(self._keys)

    def get_healthy_client(self, exclude_keys: set[str] | None = None) -> tuple[AsyncGroq, KeyHealthInfo]:
        """
        Zero-latency step function to select the optimal healthy API key.
        Strategy:
          1. Check for keys whose rate limit cooldown has expired -> auto-restore to HEALTHY.
          2. Filter available keys (not rate limited, errors < 3, not excluded).
          3. Pick via Least-Recently-Used (LRU) / Round-Robin among healthy keys to spread rate limits.
          4. If all keys are rate limited, pick the key closest to cooldown expiry.
        """
        if not self._keys:
            self.reload_keys()
            if not self._keys:
                raise RuntimeError("No Groq API keys configured in .env or environment")

        now = time.time()
        excluded = exclude_keys or set()

        # Step 1: Auto-restore keys whose cooldown has expired
        for k in self._keys:
            if k.status == "RATE_LIMITED" and now >= k.rate_limit_reset_at:
                k.status = "HEALTHY"
                k.consecutive_errors = 0
                k.last_error_message = None
                logger.info("🟢 Groq key #%d (%s) rate-limit cooldown expired, restored to HEALTHY", k.key_index, k.masked_key)

        # Step 2: Find all available candidates
        available_candidates = [
            k for k in self._keys
            if k.api_key not in excluded and k.is_available
        ]

        if not available_candidates:
            # Fallback 1: Available keys including previously excluded
            available_candidates = [k for k in self._keys if k.is_available]

        if available_candidates:
            # Load balance by Least-Recently-Used to distribute RPM/TPM across all 5+ keys
            available_candidates.sort(key=lambda k: k.last_used_at)
            selected = available_candidates[0]
        else:
            # Fallback 2: All keys are rate limited — select the one closest to cooldown recovery
            logger.warning("⚠️ All %d Groq API keys are currently rate-limited or degraded! Selecting earliest recovery key.", len(self._keys))
            sorted_by_reset = sorted(self._keys, key=lambda k: k.rate_limit_reset_at)
            selected = sorted_by_reset[0]

        selected.last_used_at = now
        selected.total_requests += 1
        return selected.client, selected

    def mark_rate_limited(self, api_key: str, cooldown_seconds: float = DEFAULT_RATE_LIMIT_COOLDOWN, error_msg: str | None = None) -> None:
        """Mark a key as rate limited (HTTP 429) with a cooldown period."""
        now = time.time()
        for k in self._keys:
            if k.api_key == api_key:
                k.status = "RATE_LIMITED"
                k.rate_limit_reset_at = now + cooldown_seconds
                k.last_error_message = error_msg or "HTTP 429 Rate Limit Exceeded"
                k.consecutive_errors += 1
                logger.warning(
                    "🔄 Groq Key #%d (%s) RATE LIMITED. Cooldown: %.1fs (Pool: %d total keys)",
                    k.key_index, k.masked_key, cooldown_seconds, len(self._keys)
                )
                break

    def mark_success(self, api_key: str, latency_ms: float = 0.0) -> None:
        """Record a successful response on the key."""
        for k in self._keys:
            if k.api_key == api_key:
                if k.status != "HEALTHY":
                    k.status = "HEALTHY"
                k.consecutive_errors = 0
                k.last_error_message = None
                if latency_ms > 0:
                    k.last_latency_ms = latency_ms
                break

    def mark_error(self, api_key: str, error_msg: str) -> None:
        """Record a non-429 error on the key."""
        for k in self._keys:
            if k.api_key == api_key:
                k.consecutive_errors += 1
                k.last_error_message = error_msg
                if k.consecutive_errors >= 3:
                    k.status = "ERROR"
                    logger.error("❌ Groq Key #%d (%s) marked ERROR after %d consecutive failures", k.key_index, k.masked_key, k.consecutive_errors)
                break

    async def probe_single_key(self, info: KeyHealthInfo) -> dict[str, Any]:
        """
        Fast health check for a single key using a lightweight models.list call.
        Does not block query execution and returns latency and health status.
        """
        t0 = time.perf_counter()
        try:
            # Fast lightweight ping to check authentication & rate limit status
            await asyncio.wait_for(info.client.models.list(), timeout=PROBE_TIMEOUT_SECONDS)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            info.last_latency_ms = latency_ms
            info.last_checked_at = time.time()
            info.status = "HEALTHY"
            info.consecutive_errors = 0
            info.last_error_message = None
            return {"key_index": info.key_index, "masked_key": info.masked_key, "status": "HEALTHY", "latency_ms": round(latency_ms, 2)}
        except RateLimitError as rle:
            info.status = "RATE_LIMITED"
            info.rate_limit_reset_at = time.time() + DEFAULT_RATE_LIMIT_COOLDOWN
            info.last_error_message = str(rle)
            info.last_checked_at = time.time()
            return {"key_index": info.key_index, "masked_key": info.masked_key, "status": "RATE_LIMITED", "error": "Rate limited (429)"}
        except APIStatusError as ase:
            info.status = "ERROR"
            info.last_error_message = str(ase)
            info.last_checked_at = time.time()
            return {"key_index": info.key_index, "masked_key": info.masked_key, "status": "ERROR", "error": f"API error: {ase.status_code}"}
        except Exception as exc:
            info.status = "ERROR"
            info.last_error_message = str(exc)
            info.last_checked_at = time.time()
            return {"key_index": info.key_index, "masked_key": info.masked_key, "status": "ERROR", "error": str(exc)}

    async def check_all_keys_health(self) -> list[dict[str, Any]]:
        """
        Execute concurrent health checks across all keys in the pool in parallel.
        Ultra-fast execution using asyncio.gather.
        """
        if not self._keys:
            self.reload_keys()
        tasks = [self.probe_single_key(k) for k in self._keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        formatted: list[dict[str, Any]] = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                k = self._keys[idx]
                k.status = "ERROR"
                k.last_error_message = str(res)
                formatted.append({"key_index": k.key_index, "masked_key": k.masked_key, "status": "ERROR", "error": str(res)})
            else:
                formatted.append(res)
        return formatted

    def get_status_report(self) -> dict[str, Any]:
        """Return comprehensive status overview of all keys."""
        now = time.time()
        # auto restore expired rate limits
        for k in self._keys:
            if k.status == "RATE_LIMITED" and now >= k.rate_limit_reset_at:
                k.status = "HEALTHY"
                k.consecutive_errors = 0

        healthy_count = sum(1 for k in self._keys if k.status == "HEALTHY")
        rate_limited_count = sum(1 for k in self._keys if k.status == "RATE_LIMITED")
        error_count = sum(1 for k in self._keys if k.status == "ERROR")

        return {
            "total_keys": len(self._keys),
            "healthy_keys": healthy_count,
            "rate_limited_keys": rate_limited_count,
            "error_keys": error_count,
            "keys": [k.to_dict() for k in self._keys],
        }

    async def start_background_monitor(self, interval_seconds: float = 30.0) -> None:
        """Background health worker that periodically validates and recovers rate-limited keys."""
        logger.info("🚀 Starting Groq API Key background health monitor (interval: %ds)", interval_seconds)
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                # Only probe keys that are currently rate-limited or in error to conserve quota
                degraded = [k for k in self._keys if k.status in ("RATE_LIMITED", "ERROR") or (k.rate_limit_reset_at > 0 and time.time() >= k.rate_limit_reset_at)]
                if degraded:
                    await asyncio.gather(*[self.probe_single_key(k) for k in degraded], return_exceptions=True)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Groq key background health monitor: %s", e)


# Global singleton instance
key_pool = GroqKeyPoolManager()
