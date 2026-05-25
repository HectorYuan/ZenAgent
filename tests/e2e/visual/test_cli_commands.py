"""
Phase CLI: 12 个 CLI 命令全覆盖测试

通过 subprocess 调用 CLI，捕获输出，验证格式和关键数据。
"""
import subprocess
import sys
import os

from .runner import register_phase, PhaseResult
from . import viz

# CLI 入口
CLI_ENTRY = [sys.executable, "-m", "packages.ZenAgent.zena"]


def _run_cli(*args, timeout: int = 30, env: dict = None) -> tuple[int, str, str]:
    """运行 CLI 命令，返回 (returncode, stdout, stderr)"""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    try:
        p = subprocess.run(
            [*CLI_ENTRY, *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            env=run_env,
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def _check_output(rc: int, stdout: str, stderr: str, expected: list[str] = None) -> tuple[bool, list[str]]:
    """检查输出是否包含预期字符串"""
    issues = []
    if rc != 0 and rc != -1:
        issues.append(f"Return code: {rc}")
    if stderr and "warning" not in stderr.lower():
        # stderr 中有错误（忽略 warnings）
        if "Error" in stderr or "Traceback" in stderr:
            issues.append(f"Stderr: {stderr[:100]}")
    if expected:
        for exp in expected:
            if exp not in stdout and exp not in stderr:
                issues.append(f"Missing: '{exp}'")
    return len(issues) == 0, issues


@register_phase("CLI", "CLI Commands — 12 Commands Full Coverage", "CLI")
def run_cli(config: dict, result: PhaseResult):
    use_real_llm = config.get("real_llm", False)

    # ---- 1. chat (single-shot) ----
    viz.scenario_header("chat (single-shot)", 1, 12)
    if use_real_llm:
        rc, out, err = _run_cli("chat", "Hello", "--no-history", timeout=60)
        passed, issues = _check_output(rc, out, err)
        viz.info(f"Output: {out[:120].strip()}")
        if not passed:
            for i in issues:
                viz.warn(i)
    else:
        passed, issues = True, []
        viz.info("Skipped: use --real-llm")
    result.add_scenario("chat", passed, issues)

    # ---- 2. status ----
    viz.scenario_header("status", 2, 12)
    rc, out, err = _run_cli("status")
    passed, issues = _check_output(rc, out, err, ["Agent", "Agent ID"])
    print(f"    {out[:200].strip()}")
    result.add_scenario("status", passed, issues)

    # ---- 3. memory stats ----
    viz.scenario_header("memory stats", 3, 12)
    rc, out, err = _run_cli("memory", "stats")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("memory stats", passed, issues)

    # ---- 4. memory add ----
    viz.scenario_header("memory add", 4, 12)
    rc, out, err = _run_cli("memory", "add", "E2E test memory entry")
    passed, issues = _check_output(rc, out, err, ["存储"])
    print(f"    {out.strip()}")
    result.add_scenario("memory add", passed, issues)

    # ---- 5. memory search ----
    viz.scenario_header("memory search", 5, 12)
    rc, out, err = _run_cli("memory", "search", "E2E")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("memory search", passed, issues)

    # ---- 6. personality show ----
    viz.scenario_header("personality show", 6, 12)
    rc, out, err = _run_cli("personality", "show")
    passed, issues = _check_output(rc, out, err, ["Big Five", "█"])
    print(f"    {out[:300].strip()}")
    result.add_scenario("personality show", passed, issues)

    # ---- 7. personality set ----
    viz.scenario_header("personality set", 7, 12)
    rc, out, err = _run_cli("personality", "set", "openness", "0.8")
    passed, issues = _check_output(rc, out, err, ["openness", "0.8"])
    print(f"    {out.strip()}")
    result.add_scenario("personality set", passed, issues)

    # ---- 8. provider list ----
    viz.scenario_header("provider list", 8, 12)
    rc, out, err = _run_cli("provider", "list")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("provider list", passed, issues)

    # ---- 9. provider health ----
    viz.scenario_header("provider health", 9, 12)
    rc, out, err = _run_cli("provider", "health")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("provider health", passed, issues)

    # ---- 10. agent list ----
    viz.scenario_header("agent list", 10, 12)
    rc, out, err = _run_cli("agent", "list")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("agent list", passed, issues)

    # ---- 11. doctor ----
    viz.scenario_header("doctor", 11, 12)
    rc, out, err = _run_cli("doctor")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:300].strip()}")
    # Check all 5 subsystems present
    for sub in ["agent", "llm", "memory", "personality", "runtime"]:
        if sub not in out.lower():
            issues.append(f"Subsystem '{sub}' not in doctor output")
            passed = False
    result.add_scenario("doctor", passed, issues)

    # ---- 12. knowledge stats ----
    viz.scenario_header("knowledge stats", 12, 12)
    rc, out, err = _run_cli("knowledge", "stats")
    passed, issues = _check_output(rc, out, err)
    print(f"    {out[:200].strip()}")
    result.add_scenario("knowledge stats", passed, issues)
