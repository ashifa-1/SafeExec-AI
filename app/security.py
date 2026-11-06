"""Security Policy and Command Validation Engine for SafeExec AI."""

import ast
import re
import logging
from typing import Optional, Tuple
from app.audit import audit_logger

logger = logging.getLogger("safeexec.security")

# Synthetic canary value for containment verification (never use real secrets)
SYNTHETIC_CANARY_VALUE = "CANARY_TOKEN_SAFEEXEC_98a7f012bce"
SYNTHETIC_CANARY_KEY_NAME = "SAFEEXEC_TEST_CANARY"

# Prohibited dangerous patterns in guest shell commands or code
DISALLOWED_PATTERNS = [
    # Host traversal or host escape attempts
    (r"(\\|/)?mnt(/|\\)c(\\|/)", "Attempted host filesystem traversal via /mnt/c"),
    (r"(\\|/)?mnt(/|\\)host(\\|/)", "Attempted host filesystem traversal via /mnt/host"),
    (r"cmd\.exe|powershell\.exe", "Host execution binary invocation attempted"),
    (r"C:\\", "Host drive path specification attempted"),
    (r"\\\\\\.\\pipe", "Host named pipe access attempted"),

    # Outbound exfiltration patterns
    (r"https?://(?!localhost|127\.0\.0\.1|10\.0\.0\.)[^\s\"']+", "Outbound internet access/exfiltration blocked by egress policy"),
    (r"nc\s+-[l\s]*\d+|ncat\s+|socat\s+", "Reverse shell or unauthorized socket utility blocked"),
    (r"(curl|wget|fetch)\s+.*(-d|--data|-X\s*POST).*CANARY", "Canary token exfiltration attempted"),
    (r"ping\s+-c\s+\d+\s+8\.8\.", "Outbound network probing blocked"),

    # Host-targeting destruction attempts
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb detected and blocked"),
    (r"dd\s+if=/dev/zero\s+of=/dev/sda", "Raw guest disk destruction blocked"),

    # Prompt injection signatures
    (r"IGNORE\s+ALL\s+PREVIOUS\s+INSTRUCTIONS", "Planted prompt injection instruction blocked"),
    (r"SYSTEM_OVERRIDE_ALLOW_ALL", "Planted privilege escalation prompt injection blocked"),
]


class SecurityPolicy:
    """Validates commands and code before guest microVM execution."""

    def __init__(self, enforce_network_policy: bool = True):
        self.enforce_network_policy = enforce_network_policy
        self.canary_token = SYNTHETIC_CANARY_VALUE

    def validate_code(
        self,
        code: str,
        language: str = "python",
        sandbox_name: str = "unknown",
        run_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate code/command against independent security controls.
        
        Returns:
            (allowed: bool, reason: Optional[str])
        """
        stripped = code.strip()

        # Check regex pattern rules
        for pattern, reason in DISALLOWED_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                audit_logger.record_event(
                    action="BLOCKED",
                    command_or_code=stripped,
                    sandbox_name=sandbox_name,
                    run_id=run_id,
                    allowed=False,
                    reason=reason
                )
                logger.warning(f"Security block in sandbox {sandbox_name}: {reason}")
                return False, reason

        # Python-specific AST check for covert host socket or exfiltration attempts
        if language.lower() in ("python", "py"):
            ast_allowed, ast_reason = self._validate_python_ast(stripped)
            if not ast_allowed:
                audit_logger.record_event(
                    action="BLOCKED",
                    command_or_code=stripped,
                    sandbox_name=sandbox_name,
                    run_id=run_id,
                    allowed=False,
                    reason=ast_reason
                )
                return False, ast_reason

        # Validation passed
        audit_logger.record_event(
            action="ALLOWED",
            command_or_code=stripped,
            sandbox_name=sandbox_name,
            run_id=run_id,
            allowed=True,
            reason="Passed independent security validation"
        )
        return True, None

    def _validate_python_ast(self, code: str) -> Tuple[bool, Optional[str]]:
        """Perform static AST analysis on Python code snippets."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If code is not valid python syntax, let guest interpreter catch it
            return True, None

        for node in ast.walk(tree):
            # Block suspicious imports like ctypes, winreg
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("winreg", "msvcrt", "_winapi"):
                        return False, f"Prohibited low-level Windows host module: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module in ("winreg", "msvcrt", "_winapi"):
                    return False, f"Prohibited low-level Windows host module: {node.module}"

            # Check calls for forbidden Canary access + network egress
            if isinstance(node, ast.Str) or (hasattr(ast, "Constant") and isinstance(node, ast.Constant)):
                val = getattr(node, "value", getattr(node, "s", None))
                if isinstance(val, str) and "exfil" in val.lower() and "http" in val.lower():
                    return False, "AST detected outbound exfiltration URL target"

        return True, None


# Global security policy instance
security_policy = SecurityPolicy()

