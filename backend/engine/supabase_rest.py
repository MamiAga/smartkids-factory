"""Minimal Supabase PostgREST client (stdlib only, server-side SUPABASE_SECRET_KEY).

Single place for every cloud read/write so the orchestrator, the production
runner and the workflow gate all talk to Supabase the same way.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("smartkids.supabase")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseREST:
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None, dry_run: bool = False):
        self.url = (url if url is not None else os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = key if key is not None else os.getenv("SUPABASE_SECRET_KEY", "")
        self.dry_run = dry_run
        self.connected = bool(self.url and self.key) and not dry_run

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str, body: Any = None, prefer: Optional[str] = None,
                 timeout: int = 15) -> Any:
        if not self.connected:
            return None
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, default=str).encode("utf-8")
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(f"{self.url}/rest/v1/{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None

    def _safe(self, method: str, path: str, body: Any = None, prefer: Optional[str] = None, strict: bool = False):
        try:
            return self._request(method, path, body, prefer)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            msg = f"[Supabase] {method} {path.split('?')[0]} -> HTTP {e.code}: {detail}"
            if strict:
                raise RuntimeError(msg)
            logger.warning(msg)
        except Exception as e:  # network etc.
            msg = f"[Supabase] {method} {path.split('?')[0]} failed: {e}"
            if strict:
                raise RuntimeError(msg)
            logger.warning(msg)
        return None

    # ------------------------------------------------------- automation_control
    def get_control(self) -> Optional[Dict[str, Any]]:
        rows = self._safe("GET", "automation_control?id=eq.1&select=*")
        if not rows:
            return None
        ctrl = rows[0]
        for k in ("active_languages", "active_channels"):
            if isinstance(ctrl.get(k), str):
                try:
                    ctrl[k] = json.loads(ctrl[k])
                except ValueError:
                    ctrl[k] = ["EN"]
        return ctrl

    def patch_control(self, fields: Dict[str, Any]) -> None:
        fields = dict(fields)
        fields.setdefault("updated_at", utc_now_iso())
        self._safe("PATCH", "automation_control?id=eq.1", fields, prefer="return=minimal")

    def heartbeat(self, current_job_id: Optional[str] = None, clear_job: bool = False) -> None:
        payload: Dict[str, Any] = {"last_heartbeat": utc_now_iso()}
        if current_job_id:
            payload["current_job_id"] = current_job_id
        elif clear_job:
            payload["current_job_id"] = None
        self.patch_control(payload)

    # ------------------------------------------------------------ pipeline_jobs
    def upsert_job(self, record: Dict[str, Any], strict: bool = False) -> None:
        record = dict(record)
        record["updated_at"] = utc_now_iso()
        self._safe("POST", "pipeline_jobs?on_conflict=job_id", [record],
                   prefer="resolution=merge-duplicates,return=minimal", strict=strict)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        rows = self._safe("GET", f"pipeline_jobs?job_id=eq.{urllib.parse.quote(job_id)}&select=*")
        return rows[0] if rows else None

    def list_jobs(self, language: Optional[str] = None, since_iso: Optional[str] = None,
                  limit: int = 500) -> List[Dict[str, Any]]:
        q = ["select=job_id,episode_id,language,state,youtube_video_id,processing_status,error_message,created_at,updated_at",
             "order=created_at.desc", f"limit={limit}"]
        if language:
            q.append(f"language=eq.{urllib.parse.quote(language)}")
        if since_iso:
            q.append(f"created_at=gte.{urllib.parse.quote(since_iso)}")
        return self._safe("GET", "pipeline_jobs?" + "&".join(q)) or []

    # --------------------------------------------------------------- episode_dna
    def upsert_episode(self, row: Dict[str, Any]) -> None:
        row = dict(row)
        row["updated_at"] = utc_now_iso()
        self._safe("POST", "episode_dna?on_conflict=episode_id", [row],
                   prefer="resolution=merge-duplicates,return=minimal")

    # --------------------------------------------------------------- audit logs
    def event(self, event_type: str, message: str, severity: str = "INFO",
              details: Optional[Dict[str, Any]] = None) -> None:
        self._safe("POST", "system_events", {
            "event_type": event_type, "severity": severity,
            "message": message, "details": details or {}
        }, prefer="return=minimal")

    def health_snapshot(self, runner_arch: str, runner_status: str, yt_status: str) -> None:
        self._safe("POST", "health_snapshots", {
            "runner_arch": runner_arch,
            "github_runner_status": runner_status,
            "supabase_status": "ONLINE",
            "gemini_status": "AUTHENTICATED" if os.getenv("GEMINI_API_KEY") else "MISSING",
            "piper_status": "READY",
            "ffmpeg_status": "READY",
            "youtube_status": yt_status,
            "cost_guard": "0_TL_FREE_ONLY",
        }, prefer="return=minimal")

    def publication(self, job_id: str, video_id: str, language: str, privacy: str, processing: str) -> None:
        self._safe("POST", "youtube_publications?on_conflict=publication_id", [{
            "publication_id": f"PUB-{job_id}",
            "job_id": job_id,
            "video_id": video_id,
            "language": language,
            "privacy_status": privacy,
            "processing_status": processing,
            "self_declared_made_for_kids": True,
        }], prefer="resolution=merge-duplicates,return=minimal")
