#!/usr/bin/env python3
"""CLI commands for paper-workflow: status, resume, run.

Usage:
    python scripts/commands.py status [--verbose]
    python scripts/commands.py resume
    python scripts/commands.py run <stage> [--override]
"""

import argparse
import sys
from pathlib import Path

# Ensure scripts directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow_state import (
    find_project_root,
    load_state,
    save_state,
    validate_state,
    get_stage,
    get_current_stage,
    list_stages,
    get_stages_by_status,
    set_stage_status,
    get_next_stages,
    get_blocked_stages,
)


# ---------------------------------------------------------------------------
# Stage executors (stubs — will be filled in M3–M7)
# ---------------------------------------------------------------------------

def _execute_stage(stage_id: str) -> dict:
    """Execute a stage's logic. Currently a stub.

    Returns a dict with execution result for logging.
    Future milestones will implement real stage logic here.
    """
    print(f"  [stub] 阶段 '{stage_id}' 的执行逻辑尚未实现")
    print(f"  [stub] 该阶段将在后续里程碑中填充")
    return {"executed": False, "reason": "stub — not yet implemented"}


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def cmd_status(verbose: bool = False) -> int:
    """Display project status."""
    root = find_project_root()
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        print("请运行 /paper-workflow init 初始化项目，或在项目目录下执行此命令。")
        return 1

    try:
        loaded = load_state(root)
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return 1

    state = loaded["state"]
    config = loaded["config"]

    # Validate state
    errors = validate_state(state)
    if errors:
        print("警告：状态文件格式有误：")
        for err in errors:
            print(f"  - {err}")
        print()

    # Header
    project_id = state.get("project_id", "未知")
    paper_type = state.get("paper_type", "未知")
    language = state.get("language", "未知")
    current_stage = get_current_stage(state)
    current_status = get_stage(state, current_stage)
    status_label = current_status.get("status", "未知") if current_status else "未知"

    print(f"项目: {project_id}")
    print(f"类型: {paper_type}  |  语言: {language}")
    print(f"当前阶段: {current_stage} ({status_label})")
    print()

    # Completed stages
    done_stages = get_stages_by_status(state, "done")
    skipped_stages = get_stages_by_status(state, "skipped")
    if done_stages or skipped_stages:
        print(f"已完成: {', '.join(done_stages)}" if done_stages else "", end="")
        print(f"  [跳过: {', '.join(skipped_stages)}]" if skipped_stages else "")
        print()

    # Blocked stages
    blocked = get_blocked_stages(state)
    if blocked:
        print("阻塞的阶段:")
        for b in blocked:
            print(f"  ✗ {b['stage_id']}")
            for reason in b.get("blockers", []):
                print(f"    原因: {reason}")
        print()

    # Next stages
    next_stages = get_next_stages(state)
    if next_stages:
        print(f"下一步可执行: {', '.join(next_stages)}")

    # Artifacts
    artifacts = []
    for sid in list_stages(state):
        stage = get_stage(state, sid)
        if stage and stage.get("artifacts"):
            artifacts.extend(stage["artifacts"])
    if artifacts:
        print(f"\n产物 ({len(artifacts)} 项):")
        for a in artifacts:
            print(f"  - {a}")

    # Verbose: all stages
    if verbose:
        print("\n--- 全部阶段 ---")
        for sid in list_stages(state):
            s = get_stage(state, sid)
            if s is None:
                continue
            marker = "←" if sid == current_stage else " "
            started = s.get("started_at", "") or ""
            completed = s.get("completed_at", "") or ""
            print(f"  [{marker}] {sid:30s} {s['status']:12s}  {started[:19]}  {completed[:19]}")

    # Overrides
    overrides = state.get("overrides", [])
    if overrides:
        print(f"\n⚠ 强制推进记录 ({len(overrides)} 次):")
        for o in overrides[-5:]:  # Last 5 only
            print(f"  - [{o.get('timestamp', '')[:19]}] {o.get('stage', '')}: {o.get('reason', '')}")

    return 0


# ---------------------------------------------------------------------------
# Resume command
# ---------------------------------------------------------------------------

def cmd_resume() -> int:
    """Resume from current stage."""
    root = find_project_root()
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        return 1

    try:
        loaded = load_state(root)
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return 1

    state = loaded["state"]
    current_stage = get_current_stage(state)
    current = get_stage(state, current_stage)

    if current is None:
        print(f"错误：当前阶段 '{current_stage}' 在状态文件中不存在。")
        return 1

    status = current.get("status", "unknown")

    print(f"当前阶段: {current_stage} ({status})")

    if status == "in_progress":
        print(f"\n阶段 '{current_stage}' 正在执行中。")
        print("你可以继续推进此阶段，或运行 /paper-workflow status 查看详情。")
        return 0

    elif status == "blocked":
        blockers = current.get("blockers", [])
        print(f"\n阶段 '{current_stage}' 被阻塞:")
        for b in blockers:
            print(f"  - {b}")
        print("\n修复阻塞原因后，用 /paper-workflow run {current_stage} 重新开始。")
        return 1

    elif status == "done":
        next_stages = get_next_stages(state)
        if next_stages:
            print(f"\n当前阶段已完成。下一步建议: {', '.join(next_stages[:3])}")
            print("用 /paper-workflow run <stage> 推进。")
        else:
            print("\n所有阶段已完成。用 /paper-workflow qa 运行最终质量核验。")
        return 0

    elif status == "pending":
        print(f"\n阶段 '{current_stage}' 尚未开始。")
        next_stages = get_next_stages(state)
        if current_stage in next_stages:
            print("此阶段依赖已满足，可以开始。用 /paper-workflow run {current_stage}。")
        else:
            unmet = [
                dep for dep in current.get("depends_on", [])
                if not (get_stage(state, dep) or {}).get("status") in ("done", "skipped")
            ]
            if unmet:
                print(f"依赖未满足: {', '.join(unmet)}")
                print("请先完成前置阶段。")
        return 0 if current_stage in next_stages else 1

    else:
        print(f"未知状态: {status}")
        return 1


# ---------------------------------------------------------------------------
# Run command
# ---------------------------------------------------------------------------

def cmd_run(stage_id: str, override: bool = False) -> int:
    """Run a specific stage."""
    root = find_project_root()
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        return 1

    try:
        loaded = load_state(root)
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return 1

    state = loaded["state"]

    # Check stage exists
    stage = get_stage(state, stage_id)
    if stage is None:
        valid = ", ".join(list_stages(state))
        print(f"错误：未知阶段 '{stage_id}'。")
        print(f"可用阶段: {valid}")
        return 1

    current_status = stage.get("status")

    # If already done or skipped, nothing to do
    if current_status in ("done", "skipped"):
        print(f"阶段 '{stage_id}' 已完成 (status={current_status})，无需再次执行。")
        return 0

    # Set to in_progress (with dependency check)
    result = set_stage_status(state, stage_id, "in_progress", override=override)

    if not result["success"]:
        print(f"错误：{result['message']}")
        if result["blocked_deps"]:
            print(f"未完成的前置阶段: {', '.join(result['blocked_deps'])}")
            print("用 --override 可跳过依赖检查强制执行。")
        # Save the blocked state
        save_state(state, root)
        return 1

    if result["overridden"]:
        print(f"⚠ 已跳过依赖检查，强制执行 '{stage_id}'。")

    print(f"执行阶段: {stage_id} ({current_status} → in_progress)")

    # Execute the stage logic
    exec_result = _execute_stage(stage_id)

    # Mark as done
    done_result = set_stage_status(state, stage_id, "done", override=override)
    if done_result["success"]:
        print(f"阶段 '{stage_id}' 完成。")
    else:
        print(f"阶段 '{stage_id}' 执行完成，但标记 done 失败: {done_result['message']}")
        # Save partial progress
        save_state(state, root)
        return 1

    # Save final state
    save_state(state, root)

    # Show next steps
    next_stages = get_next_stages(state)
    if next_stages:
        print(f"\n下一步建议: {', '.join(next_stages[:5])}")

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="paper-workflow CLI",
        prog="commands.py",
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("--verbose", "-v", action="store_true",
                               help="Show all stage details")

    # resume
    subparsers.add_parser("resume", help="Resume from current stage")

    # run
    run_parser = subparsers.add_parser("run", help="Run a stage")
    run_parser.add_argument("stage", help="Stage identifier")
    run_parser.add_argument("--override", action="store_true",
                            help="Skip dependency checks")

    args = parser.parse_args()

    if args.command == "status":
        return cmd_status(verbose=args.verbose)
    elif args.command == "resume":
        return cmd_resume()
    elif args.command == "run":
        return cmd_run(args.stage, override=args.override)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
