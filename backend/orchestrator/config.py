"""SmartKids Autonomous Video Factory Configuration & CostGuard Gate."""
import os
import hashlib
from typing import Dict, Any

# 1. 0 TL Non-Negotiable Cost Guard
ALLOW_PAID_SERVICES = os.getenv("ALLOW_PAID_SERVICES", "false").lower() == "true"
if ALLOW_PAID_SERVICES:
    # Hard runtime defense: Crash immediately if someone attempts to allow paid services
    raise RuntimeError("CRITICAL ARCHITECTURAL CONFLICT: ALLOW_PAID_SERVICES=true is strictly forbidden by the 0 TL Constitution!")

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# Production Ready Gate (Gated until 10/10 languages are approved and verified)
PRODUCTION_READY = False

# Oracle OCI Always Free Resource Limits
ORACLE_OCPU_LIMIT = 2.0
ORACLE_RAM_MB_LIMIT = 12288
ORACLE_BLOCK_STORAGE_GB_LIMIT = 200

# Concurrency Envelope (2 OCPU Bounded)
WORKER_CONCURRENCY = 1

# YouTube Upload Constraints (1 Google Cloud Project / 100 quota units / 100 videos/day max)
MAX_DAILY_YOUTUBE_UPLOADS = int(os.getenv("MAX_DAILY_YOUTUBE_UPLOADS", "100"))
YOUTUBE_UPLOAD_CHUNK_BYTES = 4 * 1024 * 1024  # 4MB resumable chunk stream

# Database & Broker URLs
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://smartkids_admin:secure_pg_pass@postgres:5432/smartkids_production")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Approved Gemini Free-Tier Models
GEMINI_MODEL_REASONING_QA = "gemini-3.5-flash"
GEMINI_MODEL_LOCALIZATION = "gemini-3.5-flash-lite"

def compute_deterministic_seed(episode_id: str, language: str, template_version: str = "2.0.0") -> str:
    """Calculates deterministic SHA-256 seed for zero-jitter rendering & idempotency."""
    payload = f"{episode_id}:{language}:{template_version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def assert_free_service_only(service_name: str, estimated_cost_usd: float = 0.0) -> None:
    """Fails hard if any external service tries to charge money."""
    if estimated_cost_usd > 0.0 or ALLOW_PAID_SERVICES:
        raise PermissionError(f"COST GUARD HARD STOP: Attempted paid call to '{service_name}' with cost ${estimated_cost_usd}. 0 TL constitution prohibits this.")
