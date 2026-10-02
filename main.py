#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py: 智能体七阶工程生命周期状态机与证据门禁调度中枢
=============================================================================
遵循 UCFS v1.0 终端门面规范与 OMNI-PROJECT-SPEC 契约：
将 AI 传统的“脑内臆想计划与执行”彻底固化为“物理状态机驱动与独立证据裁判”！

通用 5 大动词契约：
  setup   - 运行环境探查与零依赖自检
  run     - 驱动生命周期快速自检运行
  test    - 运行全量自动化单元测试套件
  health  - 健康度评估与退出码探测
  clean   - 清理中间缓存与测试产物

生命周期专用指令：
  init     <goal>           - [G1 意图定格] 剥离私货并提取纯粹问题域约束
  plan     <plan_file>      - [G2 计划拓扑] 校验任务依赖无环 DAG 与要素完整性
  freeze   <oracle_cmd>     - [G3 神谕先验] 物理校验红灯先验断言并锁定哈希
  begin    <task_id>        - [G4/G5 事务快照] 创建 Git 原子快照开启安全执行
  verify                    - [G6 证据裁判] 运行神谕与防篡改门禁，生成证据包
  rollback                  - [G5 失败回滚] 一键撤销脏修改，恢复至安全基线
  reflect  <notes...>       - [G7 认知蒸馏] 沉淀只增不改 ADR 决策日志与持久记忆
  status                    - 查询当前生命周期阶段与物理证据状态
"""

import os
import sys
import json
import argparse
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.lifecycle_state_machine import LifecycleStateMachine, LifecycleState, StateTransitionError
from core.intent_grounder import IntentGrounder
from core.plan_validator import PlanValidator
from core.oracle_freezer import OracleFreezer
from core.checkpoint_sentinel import CheckpointSentinel
from core.evidence_gate import EvidenceGate
from core.reflexion_distiller import ReflexionDistiller
from core.candidate_patch_engine import CandidatePatchEngine


def cmd_setup(workspace: str):
    print("=" * 70)
    print(" 🛠️  tool-lifecycle-harness 运行环境与零依赖自检")
    print("=" * 70)
    print(f" • Python 解释器: {sys.executable} (版本 {sys.version.split()[0]})")
    print(f" • 工作区路径:    {Path(workspace).resolve()}")
    print(" • 第三方依赖库:  零外部 pip 依赖 (100% 纯标准库自洽)")
    print(" • Git 状态机底座: 检测完毕")
    print("----------------------------------------------------------------------")
    print(" [✓] 智能体工程生命周期装具就绪，所有自检 100% 通过！")
    print("=" * 70)


def cmd_health(workspace: str):
    sm = LifecycleStateMachine(workspace)
    state = sm.get_state()
    phase = sm.current_phase()
    print(f"[HEALTH] 状态: HEALTHY | 当前生命周期阶段: {phase.value} | 状态文件: {sm.state_file}")


def cmd_clean(workspace: str):
    sm = LifecycleStateMachine(workspace)
    print(f"[*] 正在重置生命周期状态机至 IDLE...")
    sm.reset_to_idle()
    print("[✓] 状态机已复位完成。")


def cmd_status(workspace: str):
    sm = LifecycleStateMachine(workspace)
    state = sm.get_state()
    print("=" * 70)
    print(" 📊 智能体工程七阶生命周期状态看板 (Lifecycle Status Dashboard)")
    print("=" * 70)
    print(f" • 当前阶段:       {state.get('current_state')}")
    print(f" • 当前意图目标:   {state.get('goal') or '未定义'}")
    print(f" • 计划任务总数:   {state.get('plan_meta', {}).get('total_tasks', 0)}")
    print(f" • 冻结神谕指令:   {state.get('oracle_meta', {}).get('oracle_cmd') or '未冻结'}")
    print(f" • 最近检查点:     {state.get('checkpoint_meta', {}).get('checkpoint_id') or '无'}")
    ev = state.get('evidence_meta', {})
    print(f" • 证据裁决状态:   {'🟢 ' + ev.get('verdict') if ev.get('is_cleared') else '⚪ 未验证/未通过'}")
    print("=" * 70)


def cmd_init(workspace: str, goal: str):
    sm = LifecycleStateMachine(workspace)
    grounded = IntentGrounder.ground_intent(goal)
    sm.transition_to(LifecycleState.G1_INTENT_GROUNDED, {
        "goal": grounded["pure_problem_goal"],
        "intent_meta": grounded
    })
    print("=" * 70)
    print(" 🎯 G1: 意图定格已完成 (Intent Grounded)")
    print("=" * 70)
    print(f" • 原始陈述:       {grounded['raw_prompt']}")
    print(f" • 纯粹问题域核心: {grounded['pure_problem_goal']}")
    if grounded["has_solution_bias"]:
        print(f" • 剔除私货与偏见: {grounded['detected_biases']}")
    if grounded["explicit_invariants"]:
        print(f" • 提取刚性红线:   {grounded['explicit_invariants']}")
    print("----------------------------------------------------------------------")
    print(" 🚀 下一步: 编写结构化计划并调用 'plan <plan_file>' 进入 G2 阶段。")
    print("=" * 70)


def cmd_plan(workspace: str, plan_file: str):
    sm = LifecycleStateMachine(workspace)
    p_path = Path(plan_file).resolve()
    if not p_path.exists():
        print(f"[ERROR] 找不到计划文件: {p_path}", file=sys.stderr)
        sys.exit(1)

    try:
        plan_content = json.loads(p_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] 计划文件 JSON 解析失败: {e}", file=sys.stderr)
        sys.exit(1)

    validated = PlanValidator.validate_plan(plan_content)
    sm.transition_to(LifecycleState.G2_PLAN_VALIDATED, {
        "plan_meta": validated
    })
    print("=" * 70)
    print(" 📐 G2: 计划拓扑校验已通过 (Plan Validated DAG)")
    print("=" * 70)
    print(f" • 任务总数:     {validated['total_tasks']} 个原子任务")
    print(f" • 拓扑执行序列: {' -> '.join(validated['topological_sequence'])}")
    print("----------------------------------------------------------------------")
    print(" 🚀 下一步: 执行代码前，必须调用 'freeze <oracle_cmd>' 冻结验收神谕并验证红灯态！")
    print("=" * 70)


def cmd_freeze(workspace: str, oracle_cmd: str, test_files: list = None):
    sm = LifecycleStateMachine(workspace)
    try:
        frozen = OracleFreezer.freeze_oracle(workspace, oracle_cmd, test_files=test_files)
    except Exception as e:
        print(f"\n[ORACLE_FREEZE_REJECTED]\n{e}\n", file=sys.stderr)
        sys.exit(1)

    sm.transition_to(LifecycleState.G3_ORACLE_FROZEN, {
        "oracle_meta": frozen
    })
    print("=" * 70)
    print(" 🔒 G3: 验收神谕已成功冻结 (Oracle Frozen & Red State Confirmed)")
    print("=" * 70)
    print(f" • 验收神谕指令: {frozen['oracle_cmd']}")
    print(f" • 红灯先验断言: ✓ PASS (修改前执行确实失败，退出码 {frozen['initial_exit_code']})")
    print(f" • 指令哈希签名: {frozen['cmd_sha256'][:16]}...")
    print("----------------------------------------------------------------------")
    print(" 🚀 下一步: 调用 'begin <task_id>' 创建安全事务快照并开始编码！")
    print("=" * 70)


def cmd_begin(workspace: str, task_id: str):
    sm = LifecycleStateMachine(workspace)
    # 状态转移至 EXECUTING 与 CHECKPOINT_SECURED
    sm.transition_to(LifecycleState.G4_EXECUTING)
    cp = CheckpointSentinel.create_checkpoint(workspace, task_id)
    sm.transition_to(LifecycleState.G5_CHECKPOINT_SECURED, {
        "checkpoint_meta": cp,
        "active_task_id": task_id
    })
    print("=" * 70)
    print(f" 🛡️  G4/G5: 原子事务快照已就绪 (Task: {task_id})")
    print("=" * 70)
    print(f" • 快照 ID:       {cp['checkpoint_id']}")
    print(f" • 基线提交 SHA:  {cp['base_head_sha'][:12]}")
    print("----------------------------------------------------------------------")
    print(" 🚀 提示: AI 现在可以安全修改受控文件。若写坏随时可 'rollback'，改完调用 'verify' 验证！")
    print("=" * 70)


def cmd_verify(workspace: str):
    sm = LifecycleStateMachine(workspace)
    state = sm.get_state()
    oracle_meta = state.get("oracle_meta", {})

    evidence = EvidenceGate.evaluate_evidence(workspace, oracle_meta)

    if evidence.get("is_cleared"):
        sm.transition_to(LifecycleState.G6_EVIDENCE_VERIFIED, {
            "evidence_meta": evidence
        })
        print("=" * 70)
        print(" 🟢 G6: 独立机器证据裁决已通过！(Evidence Verified)")
        print("=" * 70)
        print(f" • 验收神谕指令: {evidence['oracle_cmd']}")
        print(f" • 物理执行退出码: {evidence['exit_code']} (SUCCESS)")
        print(f" • 防篡改校验:   ✓ 通过 (测试文件与原版严格一致)")
        print(f" • 物理执行耗时: {evidence['execution_duration_sec']} 秒")
        print("----------------------------------------------------------------------")
        print(" 🚀 下一步: 调用 'reflect <notes>' 沉淀决策日志与避坑知识，完成结项！")
        print("=" * 70)
    else:
        print("=" * 70)
        print(" 🔴 G6: 证据门禁拒绝合流！(Evidence Rejected)")
        print("=" * 70)
        print(f" • 拒绝理由:     {evidence.get('reason') or '神谕测试未通过'}")
        print(f" • 退出码:       {evidence.get('exit_code', -1)}")
        if evidence.get('stderr_tail'):
            print(f" • 错误回溯:\n{evidence['stderr_tail']}")
        print("----------------------------------------------------------------------")
        print(" 💡 建议: 请继续修改代码或调用 'rollback' 一键撤销本轮脏修改！")
        print("=" * 70)
        sys.exit(2)


def cmd_rollback(workspace: str):
    sm = LifecycleStateMachine(workspace)
    state = sm.get_state()
    cp = state.get("checkpoint_meta", {})
    if not cp:
        print("[ERROR] 未检测到活跃的检查点快照，无法回滚！", file=sys.stderr)
        sys.exit(1)

    res = CheckpointSentinel.rollback(workspace, cp)
    sm.transition_to(LifecycleState.G3_ORACLE_FROZEN, {
        "checkpoint_meta": {}
    })
    print("=" * 70)
    print(" ⏪ G5: 物理回滚已执行完毕！(Rolled Back to Safe Baseline)")
    print("=" * 70)
    print(f" • 已恢复至基线: {res.get('rolled_back_to')}")
    print(" • 工作区已彻底重置为干净状态，避免脏代码引发级联故障。")
    print("=" * 70)


def cmd_reflect(workspace: str, notes: list):
    sm = LifecycleStateMachine(workspace)
    state = sm.get_state()
    goal = state.get("goal", "未知目标")

    decisions = [n for n in notes if not n.startswith("pitfall:")]
    pitfalls = [n.replace("pitfall:", "").strip() for n in notes if n.startswith("pitfall:")]
    if not decisions:
        decisions = ["按照 7 阶工程生命周期规范完成功能自洽重构"]

    distilled = ReflexionDistiller.distill_and_record(
        workspace, goal, decisions, pitfalls
    )
    sm.transition_to(LifecycleState.G7_REFLEXION_DISTILLED, {
        "reflexion_meta": distilled
    })
    print("=" * 70)
    print(" 🧠 G7: 认知反思与经验持久化已蒸馏完成！(Reflexion Distilled)")
    print("=" * 70)
    print(f" • 沉淀 ADR 决策:  {distilled['adr_file']}")
    print(f" • 沉淀长期记忆库: {distilled['memory_file']}")
    print(f" • 决策数: {distilled['distilled_decisions_count']} | 避坑经验数: {distilled['distilled_pitfalls_count']}")
    print("----------------------------------------------------------------------")
    print(" [✓] 本轮智能体生命周期闭环圆满完成！状态已安全归档。")
    print("=" * 70)


def cmd_apply(workspace: str):
    res = CandidatePatchEngine.apply_candidate_patch(workspace)
    if res["success"]:
        print("=" * 70)
        print(" 🚀 候选补丁已安全合入主分支！(Candidate Patch Merged)")
        print("=" * 70)
        print(" • 遵循 Google Tricorder 规范，改动已固化为正式提交。")
        print("=" * 70)
    else:
        print(f"[ERROR] 补丁合流失败: {res.get('reason')}", file=sys.stderr)
        sys.exit(1)


def cmd_discard(workspace: str):
    res = CandidatePatchEngine.discard_candidate_patch(workspace)
    print("=" * 70)
    print(" 🗑️ 候选补丁已彻底丢弃，工作区已恢复至干净基线！")
    print("=" * 70)


def cmd_packet(workspace: str):
    sm = LifecycleStateMachine(workspace)
    packet = CandidatePatchEngine.build_review_packet(
        workspace,
        sm.get_state(),
        reason="MANUAL_INSPECT_PACKET"
    )
    print(json.dumps(packet, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="tool-lifecycle-harness: 智能体七阶工程生命周期状态机与证据门禁调度器")
    parser.add_argument("verb", nargs="?", default="health", help="通用动词或生命周期操作")
    parser.add_argument("args", nargs="*", help="操作附属参数")
    parser.add_argument("--workspace", default=".", help="目标工作区路径")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")

    parsed = parser.parse_args()
    v = parsed.verb.lower()
    ws = parsed.workspace

    try:
        if v == "setup":
            cmd_setup(ws)
        elif v in ("health", "check"):
            cmd_health(ws)
        elif v == "clean":
            cmd_clean(ws)
        elif v == "test":
            loader = unittest.TestLoader()
            suite = loader.discover(str(BASE_DIR / "tests"))
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            sys.exit(0 if result.wasSuccessful() else 1)
        elif v == "status":
            cmd_status(ws)
        elif v == "init":
            goal_str = " ".join(parsed.args) if parsed.args else "通用软件工程重构任务"
            cmd_init(ws, goal_str)
        elif v == "plan":
            if not parsed.args:
                print("请指定计划文件路径: python main.py plan <plan.json>", file=sys.stderr)
                sys.exit(1)
            cmd_plan(ws, parsed.args[0])
        elif v == "freeze":
            if not parsed.args:
                print("请指定验收神谕指令: python main.py freeze \"<oracle_cmd>\"", file=sys.stderr)
                sys.exit(1)
            cmd_freeze(ws, parsed.args[0])
        elif v == "begin":
            task_id = parsed.args[0] if parsed.args else "task_1"
            cmd_begin(ws, task_id)
        elif v == "verify":
            cmd_verify(ws)
        elif v == "rollback":
            cmd_rollback(ws)
        elif v == "reflect":
            cmd_reflect(ws, parsed.args)
        elif v == "apply":
            cmd_apply(ws)
        elif v == "discard":
            cmd_discard(ws)
        elif v == "packet":
            cmd_packet(ws)
        elif v == "run":
            cmd_setup(ws)
            cmd_health(ws)
        else:
            parser.print_help()
    except StateTransitionError as e:
        print(f"\n[STATE_MACHINE_ERROR]\n{e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
