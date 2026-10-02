#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/lifecycle_state_machine.py: 智能体工程七阶生命周期状态机引擎
=============================================================================
彻底消除“AI 脑内凭直觉跳步编程”的工程绝症：
定义确定性强类型状态与合法转移边，任何越级操作（如未冻结神谕直接写代码、未出示证据直接结项）
均被状态机物理拦截！

七阶严格状态拓扑：
  G0: IDLE (空闲态)
  G1: INTENT_GROUNDED (意图定格态：问题域与私货剥离完成)
  G2: PLAN_VALIDATED (计划拓扑态：任务依赖 DAG 无环验证通过)
  G3: ORACLE_FROZEN (神谕先验态：验收测试红灯先验断言成功，哈希锁死)
  G4: EXECUTING (原子事务态：沙盒环境任务执行中)
  G5: CHECKPOINT_SECURED (快照守护态：Git 原子检查点就绪，随时可安全回滚)
  G6: EVIDENCE_VERIFIED (证据裁决态：物理机器退出码 0 与 AST 门禁通过)
  G7: REFLEXION_DISTILLED (认知终态：ADR 决策日志与避坑记忆持久化)
"""

import os
import json
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional


class LifecycleState(str, Enum):
    IDLE = "IDLE"
    G1_INTENT_GROUNDED = "G1_INTENT_GROUNDED"
    G2_PLAN_VALIDATED = "G2_PLAN_VALIDATED"
    G3_ORACLE_FROZEN = "G3_ORACLE_FROZEN"
    G4_EXECUTING = "G4_EXECUTING"
    G5_CHECKPOINT_SECURED = "G5_CHECKPOINT_SECURED"
    G6_EVIDENCE_VERIFIED = "G6_EVIDENCE_VERIFIED"
    G7_REFLEXION_DISTILLED = "G7_REFLEXION_DISTILLED"


class StateTransitionError(Exception):
    """非法状态转移异常"""
    pass


class LifecycleStateMachine:
    """
    确定性生命周期状态机管理器
    状态持久化于目标项目根目录的 .agent_lifecycle/state.json
    """

    VALID_TRANSITIONS = {
        LifecycleState.IDLE: [LifecycleState.G1_INTENT_GROUNDED],
        LifecycleState.G1_INTENT_GROUNDED: [LifecycleState.G2_PLAN_VALIDATED, LifecycleState.IDLE],
        LifecycleState.G2_PLAN_VALIDATED: [LifecycleState.G3_ORACLE_FROZEN, LifecycleState.G1_INTENT_GROUNDED],
        LifecycleState.G3_ORACLE_FROZEN: [LifecycleState.G4_EXECUTING, LifecycleState.G2_PLAN_VALIDATED],
        LifecycleState.G4_EXECUTING: [LifecycleState.G5_CHECKPOINT_SECURED, LifecycleState.G3_ORACLE_FROZEN],
        LifecycleState.G5_CHECKPOINT_SECURED: [LifecycleState.G6_EVIDENCE_VERIFIED, LifecycleState.G4_EXECUTING, LifecycleState.G3_ORACLE_FROZEN],
        LifecycleState.G6_EVIDENCE_VERIFIED: [LifecycleState.G7_REFLEXION_DISTILLED, LifecycleState.G4_EXECUTING],
        LifecycleState.G7_REFLEXION_DISTILLED: [LifecycleState.IDLE, LifecycleState.G1_INTENT_GROUNDED]
    }

    def __init__(self, workspace_dir: str):
        self.workspace = Path(workspace_dir).resolve()
        self.state_dir = self.workspace / ".agent_lifecycle"
        self.state_file = self.state_dir / "state.json"
        self.history_file = self.state_dir / "history.jsonl"
        self._ensure_storage()

    def _ensure_storage(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            initial_data = {
                "current_state": LifecycleState.IDLE.value,
                "goal": None,
                "plan_meta": {},
                "oracle_meta": {},
                "checkpoint_meta": {},
                "evidence_meta": {},
                "last_updated": time.time()
            }
            self.state_file.write_text(json.dumps(initial_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_state(self) -> Dict[str, Any]:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {"current_state": LifecycleState.IDLE.value}

    def current_phase(self) -> LifecycleState:
        data = self.get_state()
        return LifecycleState(data.get("current_state", LifecycleState.IDLE.value))

    def transition_to(self, next_state: LifecycleState, metadata_updates: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current = self.current_phase()
        allowed = self.VALID_TRANSITIONS.get(current, [])

        if next_state not in allowed:
            raise StateTransitionError(
                f"🚨 违背工程状态机物理法则！禁止从当前状态 [{current.value}] 直接跳跃转移至 [{next_state.value}]。\n"
                f"合法的下一阶段仅限: {[s.value for s in allowed]}。\n"
                f"原因: 必须严密依序完成意图定格、计划校验、神谕冻结、快照守护与证据门禁，严禁偷步！"
            )

        data = self.get_state()
        prev_state = data["current_state"]
        data["current_state"] = next_state.value
        data["last_updated"] = time.time()

        if metadata_updates:
            for k, v in metadata_updates.items():
                data[k] = v

        self.state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        # 记录不可篡改审计履历
        log_entry = {
            "timestamp": time.time(),
            "from_state": prev_state,
            "to_state": next_state.value,
            "updates_keys": list(metadata_updates.keys()) if metadata_updates else []
        }
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        return data

    def reset_to_idle(self):
        """强制重置状态至 IDLE (用于全新任务启动)"""
        data = {
            "current_state": LifecycleState.IDLE.value,
            "goal": None,
            "plan_meta": {},
            "oracle_meta": {},
            "checkpoint_meta": {},
            "evidence_meta": {},
            "last_updated": time.time()
        }
        self.state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return data
