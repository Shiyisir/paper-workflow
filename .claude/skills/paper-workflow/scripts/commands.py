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
    mark_stage_blocked,
)

from stage_executor import (
    load_contract,
    check_done_conditions,
    execute_stage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_project_dir(explicit: str | None = None) -> Path | None:
    """Resolve project directory from explicit --project, cwd, or upward search."""
    if explicit:
        proj = Path(explicit).resolve()
        if (proj / ".paper-workflow").is_dir():
            return proj
        print(f"错误：'{explicit}' 不是有效的 paper-workflow 项目目录（缺少 .paper-workflow/）。")
        return None
    return find_project_root()


# ---------------------------------------------------------------------------
# Stage executor (replaced stub in M7.1 — delegates to stage_executor)
# ---------------------------------------------------------------------------

def _execute_stage(stage_id: str, project_dir, state, config, override=False) -> dict:
    """Execute a stage's logic via stage_executor.execute_stage().

    Returns the full execution result dict. Does NOT write state.yaml.
    Kept as a thin wrapper so cmd_run() can call it cleanly.
    """
    return execute_stage(
        stage_id=stage_id,
        project_dir=project_dir,
        state=state,
        config=config,
        override=override,
    )


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def cmd_status(verbose: bool = False, project: str | None = None) -> int:
    """Display project status."""
    root = _resolve_project_dir(project)
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        print("请运行 /paper-workflow init 初始化项目，或传 --project 指定项目目录。")
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
            print(f"  [BLOCKED] {b['stage_id']}")
            for reason in b.get("blockers", []):
                print(f"    原因: {reason}")
        print()

    # Status-specific guidance
    current_stage_data = get_stage(state, current_stage)
    if current_stage_data:
        st = current_stage_data.get("status", "")
        if st == "waiting_for_user":
            handoff_path = root / ".paper-workflow" / "handoffs" / f"{current_stage}.json"
            if handoff_path.exists():
                print(f"\n等待用户完成")
                print(f"handoff 文件路径：.paper-workflow/handoffs/{current_stage}.json")
                print(f"下一步：执行对应 skill 后运行 confirm")
            else:
                print(f"\n等待用户完成")
                print(f"下一步：手动完成后运行 confirm {current_stage}")
        elif st == "pending_confirmation":
            script_dir = str(Path(__file__).resolve().parent)
            print(f"\n产物已生成，等待用户确认")
            print(f"下一步：python {script_dir}/commands.py confirm {current_stage} --project ...")
        elif st == "blocked":
            blockers = current_stage_data.get("blockers", [])
            print(f"\n阶段被阻塞")
            for b in blockers:
                print(f"原因：{b}")

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
        print(f"\n[WARN] 强制推进记录 ({len(overrides)} 次):")
        for o in overrides[-5:]:  # Last 5 only
            print(f"  - [{o.get('timestamp', '')[:19]}] {o.get('stage', '')}: {o.get('reason', '')}")

    return 0


# ---------------------------------------------------------------------------
# Resume command
# ---------------------------------------------------------------------------

def cmd_resume(project: str | None = None) -> int:
    """Resume from current stage."""
    root = _resolve_project_dir(project)
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        print("请运行 /paper-workflow init 初始化项目，或传 --project 指定项目目录。")
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

    elif status == "waiting_for_user":
        handoff_path = root / ".paper-workflow" / "handoffs" / f"{current_stage}.json"
        if handoff_path.exists():
            print(f"\n当前阶段需要你完成外部操作或 skill handoff。")
            print(f"handoff 文件：.paper-workflow/handoffs/{current_stage}.json")
            print(f"完成后运行 confirm。")
        else:
            print(f"\n当前阶段等待用户完成。完成后运行 confirm。")
        return 0

    elif status == "pending_confirmation":
        print(f"\n当前阶段已生成产物，等待确认。")
        print(f"请检查产物后运行 confirm。")
        return 0

    elif status == "blocked":
        blockers = current.get("blockers", [])
        print(f"\n当前阶段被阻塞，请根据 blocked_reason 修复后重新 run 或 override。")
        for b in blockers:
            print(f"  - {b}")
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

def cmd_run(stage_id: str, override: bool = False, project: str | None = None) -> int:
    """Run a specific stage via stage_executor."""
    root = _resolve_project_dir(project)
    if root is None:
        print("错误：未找到 paper-workflow 项目。")
        print("请运行 /paper-workflow init 初始化项目，或传 --project 指定项目目录。")
        return 1

    try:
        loaded = load_state(root)
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return 1

    state = loaded["state"]
    config = loaded["config"]

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
        print(f"[WARN] 已跳过依赖检查，强制执行 '{stage_id}'。")

    print(f"执行阶段: {stage_id} ({current_status} → in_progress)")

    # Execute the stage via stage_executor (M7.1: replaces old stub)
    exec_result = _execute_stage(
        stage_id=stage_id,
        project_dir=root,
        state=state,
        config=config,
        override=override,
    )

    recommended = exec_result.get("recommended_status", "blocked")
    handoff_generated = exec_result.get("handoff_generated", False)
    requires_manual = exec_result.get("requires_manual_action", False)
    requires_confirmation = exec_result.get("requires_confirmation", False)

    # ── Result handling ──────────────────────────────────────────

    if recommended == "done":
        # Script / hybrid-clean path: verify done_conditions before marking done
        all_met, unmet = check_done_conditions(stage_id, root)
        if all_met:
            done_result = set_stage_status(state, stage_id, "done", override=override)
            if done_result["success"]:
                save_state(state, root)
                print(f"阶段 '{stage_id}' 完成。")
                # Show warnings if any
                for w in exec_result.get("warnings", []):
                    print(f"  [WARN] {w}")
            else:
                save_state(state, root)
                print(f"阶段 '{stage_id}' 执行完成，但标记 done 失败: {done_result['message']}")
                return 1
        else:
            mark_stage_blocked(
                state, stage_id,
                f"done_conditions not met: {'; '.join(unmet)}"
            )
            save_state(state, root)
            print(f"阶段 '{stage_id}' 执行完成，但 done_conditions 不满足:")
            for u in unmet:
                print(f"  - {u}")
            print("请补齐产物后运行 confirm，或用 --override 强制确认。")
            return 1

    elif recommended == "pending_confirmation":
        # Script stage with user_confirmation_required (e.g., evidence_matrix)
        set_stage_status(state, stage_id, "pending_confirmation", override=override)
        save_state(state, root)
        print(f"产物已生成，等待用户确认。")
        for a in exec_result.get("artifacts", []):
            print(f"  - {a}")
        script_dir = str(Path(__file__).resolve().parent)
        print(f"下一步：python {script_dir}/commands.py confirm {stage_id} --project {root}")
        for w in exec_result.get("warnings", []):
            print(f"  [WARN] {w}")

    elif recommended == "waiting_for_user":
        # skill_handoff or manual or hybrid-issues path
        set_stage_status(state, stage_id, "waiting_for_user", override=override)
        save_state(state, root)

        if handoff_generated:
            handoff_path = exec_result.get("handoff_path", "")
            print(f"\n已生成 handoff 任务包：")
            print(f"  {handoff_path}")
            print(f"\n请执行对应 skill 完成产物后，再运行：")
            script_dir = str(Path(__file__).resolve().parent)
            print(f"  python {script_dir}/commands.py confirm {stage_id} --project {root}")
        elif requires_manual:
            msg = exec_result.get("message", "")
            if msg:
                print(msg)
            else:
                print(f"阶段 '{stage_id}' 需要你手动完成。")
                print(f"完成后运行 confirm {stage_id}。")
        else:
            print(f"阶段 '{stage_id}' 等待用户完成。")
            print(f"完成后运行 confirm {stage_id}。")

        for w in exec_result.get("warnings", []):
            print(f"  [WARN] {w}")

    elif recommended == "blocked":
        # Executor blocked (missing files, errors, etc.)
        reason = exec_result.get("blocked_reason", "unknown error")
        mark_stage_blocked(state, stage_id, reason)
        save_state(state, root)
        print(f"阶段 '{stage_id}' 被阻塞。")
        print(f"原因：{reason}")
        for w in exec_result.get("warnings", []):
            print(f"  [WARN] {w}")
        return 1

    else:
        # Unknown recommended_status — save state as-is and flag
        save_state(state, root)
        print(f"警告：未知的 recommended_status '{recommended}'，阶段保持 in_progress。")
        return 1

    # Show next steps
    next_stages = get_next_stages(state)
    if next_stages:
        print(f"\n下一步建议: {', '.join(next_stages[:5])}")

    return 0


# ---------------------------------------------------------------------------
# Confirm command (M5.2: added in v0.2, does NOT replace _execute_stage)
# ---------------------------------------------------------------------------

def cmd_confirm(stage_id: str, override: bool = False, project: str | None = None) -> int:
    """Confirm a stage as done after checking done conditions.

    Rules:
      - script/manual/hybrid: check contract['done_conditions']
      - skill_handoff: check contract['stage_done'] (NOT handoff_done)
      - --override skips checks and forces done
    """
    from datetime import datetime, timezone

    root = _resolve_project_dir(project)
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
        print(f"错误：未知阶段 '{stage_id}'。可用: {valid}")
        return 1

    current_status = stage.get("status")

    # Already done?
    if current_status == "done":
        print(f"阶段 '{stage_id}' 已完成，无需确认。")
        return 0

    # Only allow confirm from certain states
    allowed = {"in_progress", "waiting_for_user", "pending_confirmation", "blocked", "pending"}
    if current_status not in allowed:
        print(f"阶段 '{stage_id}' 当前状态为 '{current_status}'，无法确认。")
        print(f"可确认的状态: {', '.join(sorted(allowed))}")
        return 1

    # Load contract to determine which conditions to check
    try:
        contract = load_contract(stage_id)
    except Exception as e:
        print(f"警告：无法加载 contract: {e}，使用基础 done_conditions 检查。")
        contract = {}

    executor_type = contract.get("executor_type", "manual")

    if not override:
        # Check appropriate conditions
        all_met, unmet = check_done_conditions(stage_id, root)

        if not all_met:
            print(f"阶段 '{stage_id}' 尚不能确认完成。")
            print()
            print(f"未满足条件:")
            for u in unmet:
                print(f"  - {u}")
            print()
            marker = "stage_done" if executor_type == "skill_handoff" else "done_conditions"
            print(f"（检查的是 contract 的 {marker} 字段）")
            print()
            print(f"请补齐产物后再次运行 confirm，或使用 --override 强制确认。")

            # Optionally mark as blocked
            if current_status not in ("blocked",):
                mark_stage_blocked(state, stage_id, f"confirm 检查失败: {unmet}")
                save_state(state, root)

            return 1

        # All conditions met
        set_stage_status(state, stage_id, "done")
        save_state(state, root)
        print(f"[OK] 阶段 '{stage_id}' 已确认完成（{executor_type}）。")
        return 0

    else:
        # --override: force done
        all_met, unmet = check_done_conditions(stage_id, root)

        now = datetime.now(timezone.utc).isoformat()
        overrides = state.setdefault("overrides", [])
        overrides.append({
            "stage": stage_id,
            "timestamp": now,
            "action": "confirm_override",
            "reason": "用户使用 --override 强制确认",
            "unmet_conditions": unmet,
        })

        set_stage_status(state, stage_id, "done", override=True)
        save_state(state, root)

        print(f"[WARN] 已使用 --override 强制确认阶段 '{stage_id}'。")
        if unmet:
            print(f"跳过的未满足条件: {', '.join(unmet)}")
        print(f"override 已记录到 state.yaml。")
        return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="paper-workflow CLI",
        prog="commands.py",
    )
    parser.add_argument("--project", "-p", default=None,
                        help="Project root directory (auto-detected from cwd if not set)")
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

    # confirm (v0.2 M5.2)
    confirm_parser = subparsers.add_parser("confirm", help="Confirm a stage as done")
    confirm_parser.add_argument("stage", help="Stage identifier")
    confirm_parser.add_argument("--override", action="store_true",
                                help="Force confirm and skip done_conditions check")

    args = parser.parse_args()

    project = getattr(args, "project", None)

    if args.command == "status":
        return cmd_status(verbose=args.verbose, project=project)
    elif args.command == "resume":
        return cmd_resume(project=project)
    elif args.command == "run":
        return cmd_run(args.stage, override=args.override, project=project)
    elif args.command == "confirm":
        return cmd_confirm(args.stage, override=args.override, project=project)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
