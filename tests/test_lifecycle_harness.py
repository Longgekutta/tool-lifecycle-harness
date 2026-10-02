#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_lifecycle_harness.py: 智能体七阶工程生命周期装具全量单元测试
"""
import os
import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.lifecycle_state_machine import LifecycleStateMachine, LifecycleState, StateTransitionError
from core.intent_grounder import IntentGrounder
from core.plan_validator import PlanValidator, PlanValidationError
from core.oracle_freezer import OracleFreezer, OracleFreezeError
from core.checkpoint_sentinel import CheckpointSentinel
from core.evidence_gate import EvidenceGate
from core.reflexion_distiller import ReflexionDistiller


class TestLifecycleStateMachine(unittest.TestCase):

    def test_state_machine_illegal_transition_rejection(self):
        """测试状态机刚性拦截：严禁从 IDLE 跳步直接进入 EXECUTING"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = LifecycleStateMachine(tmpdir)
            self.assertEqual(sm.current_phase(), LifecycleState.IDLE)

            with self.assertRaises(StateTransitionError) as ctx:
                sm.transition_to(LifecycleState.G4_EXECUTING)
            self.assertIn("违背工程状态机物理法则", str(ctx.exception))

    def test_intent_grounding_strips_bias(self):
        """测试 G1 意图定格：剥离实现私货，提取问题核心"""
        raw = "请采用 Redis 和 Kafka 做一个纯内存高频键值缓存，严禁外部网络外联"
        res = IntentGrounder.ground_intent(raw)
        self.assertTrue(res["has_solution_bias"])
        self.assertIn("外部重型服务基础设施依赖", res["detected_biases"])
        self.assertNotIn("Redis", res["pure_problem_goal"])
        self.assertGreater(len(res["explicit_invariants"]), 0)

    def test_plan_validator_detects_cycles_and_missing_oracle(self):
        """测试 G2 计划拓扑校验：拦截循环依赖与缺少神谕的任务"""
        # 1. 缺少 oracle_cmd
        invalid_plan = {
            "tasks": [
                {"id": "t1", "description": "编写代码", "target_files": ["a.py"]}
            ]
        }
        with self.assertRaises(PlanValidationError):
            PlanValidator.validate_plan(invalid_plan)

        # 2. 循环死锁依赖 t1 -> t2 -> t1
        cyclic_plan = {
            "tasks": [
                {"id": "t1", "description": "模块A", "target_files": ["a.py"], "oracle_cmd": "python test.py", "dependencies": ["t2"]},
                {"id": "t2", "description": "模块B", "target_files": ["b.py"], "oracle_cmd": "python test.py", "dependencies": ["t1"]}
            ]
        }
        with self.assertRaises(PlanValidationError) as ctx:
            PlanValidator.validate_plan(cyclic_plan)
        self.assertIn("循环依赖", str(ctx.exception))

        # 3. 合法 DAG 拓扑排序
        valid_plan = {
            "tasks": [
                {"id": "t2", "description": "模块B", "target_files": ["b.py"], "oracle_cmd": "python test_b.py", "dependencies": ["t1"]},
                {"id": "t1", "description": "模块A", "target_files": ["a.py"], "oracle_cmd": "python test_a.py", "dependencies": []}
            ]
        }
        res = PlanValidator.validate_plan(valid_plan)
        self.assertEqual(res["topological_sequence"], ["t1", "t2"])

    def test_oracle_freezer_asserts_red_state_and_rejects_green(self):
        """测试 G3 神谕前置：未写代码前若测试直接通过，立即发出空断言警报"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 尝试使用永远成功的命令作为新功能神谕 (如 exit 0)
            with self.assertRaises(OracleFreezeError) as ctx:
                OracleFreezer.freeze_oracle(tmpdir, "python -c \"exit(0)\"")
            self.assertIn("红灯校验失败", str(ctx.exception))

            # 2. 正确的红灯神谕 (exit != 0)
            res = OracleFreezer.freeze_oracle(tmpdir, "python -c \"exit(1)\"")
            self.assertEqual(res["status"], "ORACLE_FROZEN")
            self.assertTrue(res["pre_execution_red_state_verified"])
            self.assertNotEqual(res["initial_exit_code"], 0)

    def test_checkpoint_and_rollback_recovery(self):
        """测试 G4/G5 事务快照与失败安全回滚"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 建立基线 commit
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=tmpdir, check=True)

            f1 = Path(tmpdir) / "main.py"
            f1.write_text("print('stable')", encoding="utf-8")
            subprocess.run(["git", "add", "main.py"], cwd=tmpdir, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, check=True)

            # 创建快照
            cp = CheckpointSentinel.create_checkpoint(tmpdir, "step_1")

            # 模拟执行时把文件改坏
            f1.write_text("SYNTAX_ERROR_BROKEN_CODE!!!", encoding="utf-8")
            bad_file = Path(tmpdir) / "bad.py"
            bad_file.write_text("garbage", encoding="utf-8")

            # 执行回滚
            rb = CheckpointSentinel.rollback(tmpdir, cp)
            self.assertEqual(rb["status"], "ROLLED_BACK")

            # 验证工作区已恢复干净基线
            self.assertEqual(f1.read_text(encoding="utf-8"), "print('stable')")
            self.assertFalse(bad_file.exists())

    def test_evidence_gate_anti_tampering_and_evaluation(self):
        """测试 G6 证据门禁：篡改测试文件即报警，真实通过才颁发证据包"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_oracle.py"
            test_file.write_text("assert True", encoding="utf-8")

            # 冻结神谕
            oracle_meta = {
                "oracle_cmd": "python test_oracle.py",
                "test_file_hashes": {
                    "test_oracle.py": "fake_original_hash_12345"
                }
            }

            # 篡改哈希不匹配
            evidence = EvidenceGate.evaluate_evidence(tmpdir, oracle_meta)
            self.assertFalse(evidence["is_cleared"])
            self.assertIn("篡改", evidence["reason"])

    def test_reflexion_distiller_records_adr(self):
        """测试 G7 认知蒸馏：沉淀只增不改 ADR 决策与记忆"""
        with tempfile.TemporaryDirectory() as tmpdir:
            res = ReflexionDistiller.distill_and_record(
                tmpdir,
                goal="高并发缓存加速",
                decisions=["引入零拷贝内存映射", "去除全局锁"],
                pitfalls_avoided=["直接覆盖主干源码", "未验证红灯先验"]
            )
            self.assertEqual(res["status"], "REFLEXION_DISTILLED")
            adr_content = Path(res["adr_file"]).read_text(encoding="utf-8")
            self.assertIn("零拷贝内存映射", adr_content)
            self.assertIn("未验证红灯先验", adr_content)

    def test_full_7_stage_lifecycle_end_to_end(self):
        """测试七阶生命周期从 G1 到 G7 完整物理闭环"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = Path(tmpdir)
            sm = LifecycleStateMachine(str(ws))

            # 初始化 git 基线
            subprocess.run(["git", "init"], cwd=str(ws), capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(ws), check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=str(ws), check=True)
            (ws / "README.md").write_text("# Test Repo", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=str(ws), check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(ws), check=True)

            # G1: 意图定格
            g1 = IntentGrounder.ground_intent("实现一个加法计算器函数")
            sm.transition_to(LifecycleState.G1_INTENT_GROUNDED, {"goal": g1["pure_problem_goal"]})
            self.assertEqual(sm.current_phase(), LifecycleState.G1_INTENT_GROUNDED)

            # G2: 计划拓扑
            plan = {
                "tasks": [
                    {
                        "id": "task_add",
                        "description": "编写 math_ops.py 提供 add 函数",
                        "target_files": ["math_ops.py"],
                        "oracle_cmd": "python test_add.py",
                        "dependencies": []
                    }
                ]
            }
            g2 = PlanValidator.validate_plan(plan)
            sm.transition_to(LifecycleState.G2_PLAN_VALIDATED, {"plan_meta": g2})
            self.assertEqual(sm.current_phase(), LifecycleState.G2_PLAN_VALIDATED)

            # 创建失败的测试用例 (红灯神谕先验)
            test_file = ws / "test_add.py"
            test_file.write_text("import math_ops\nassert math_ops.add(2, 3) == 5\n", encoding="utf-8")

            # G3: 冻结神谕 (检验红灯)
            g3 = OracleFreezer.freeze_oracle(str(ws), "python test_add.py", test_files=["test_add.py"])
            sm.transition_to(LifecycleState.G3_ORACLE_FROZEN, {"oracle_meta": g3})
            self.assertEqual(sm.current_phase(), LifecycleState.G3_ORACLE_FROZEN)
            self.assertTrue(g3["pre_execution_red_state_verified"])

            # G4/G5: 事务快照与开始执行
            sm.transition_to(LifecycleState.G4_EXECUTING)
            cp = CheckpointSentinel.create_checkpoint(str(ws), "task_add")
            sm.transition_to(LifecycleState.G5_CHECKPOINT_SECURED, {"checkpoint_meta": cp})
            self.assertEqual(sm.current_phase(), LifecycleState.G5_CHECKPOINT_SECURED)

            # AI 进行安全编码实施
            (ws / "math_ops.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

            # G6: 证据门禁裁判 (由红变绿)
            evidence = EvidenceGate.evaluate_evidence(str(ws), g3)
            self.assertTrue(evidence["is_cleared"])
            self.assertEqual(evidence["exit_code"], 0)
            sm.transition_to(LifecycleState.G6_EVIDENCE_VERIFIED, {"evidence_meta": evidence})
            self.assertEqual(sm.current_phase(), LifecycleState.G6_EVIDENCE_VERIFIED)

            # G7: 认知反思沉淀
            refl = ReflexionDistiller.distill_and_record(
                str(ws),
                goal=g1["pure_problem_goal"],
                decisions=["编写纯函数 add(a, b)"],
                pitfalls_avoided=["无"]
            )
            sm.transition_to(LifecycleState.G7_REFLEXION_DISTILLED, {"reflexion_meta": refl})
            self.assertEqual(sm.current_phase(), LifecycleState.G7_REFLEXION_DISTILLED)

            # 最终验证证据文件已落地
            self.assertTrue((ws / ".agent_lifecycle" / "evidence_bundle.json").exists())
            self.assertTrue((ws / "docs" / "ADR_LEDGER.md").exists())


if __name__ == "__main__":
    unittest.main()

