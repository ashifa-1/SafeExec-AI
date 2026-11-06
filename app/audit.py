"""Command and Security Audit Logger for SafeExec AI."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger("safeexec.audit")


class AuditLogger:
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or (settings.logs_dir / "commands.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.touch()

    def record_event(
        self,
        action: str,
        command_or_code: str,
        sandbox_name: str,
        run_id: Optional[str] = None,
        allowed: bool = True,
        reason: Optional[str] = None,
        exit_code: Optional[int] = None,
        execution_time_s: Optional[float] = None,
        stdout_snippet: Optional[str] = None,
        stderr_snippet: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Record an audit entry into logs/commands.jsonl."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id or "adhoc",
            "sandbox_name": sandbox_name,
            "action": action,
            "allowed": allowed,
            "reason": reason or ("Allowed by security policy" if allowed else "Blocked by security policy"),
            "command_or_code": command_or_code[:1000],  # Truncate if excessively long
            "exit_code": exit_code,
            "execution_time_s": execution_time_s,
            "stdout_snippet": stdout_snippet[:500] if stdout_snippet else None,
            "stderr_snippet": stderr_snippet[:500] if stderr_snippet else None,
            "metadata": metadata or {},
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to audit log {self.log_file}: {e}")

        return entry

    def read_recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read the most recent audit entries."""
        if not self.log_file.exists():
            return []
        entries = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return entries[-limit:]
        except Exception as e:
            logger.error(f"Failed to read audit logs: {e}")
            return []


# Global audit logger instance
audit_logger = AuditLogger()

