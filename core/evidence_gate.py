#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/evidence_gate.py: G6 独立机器证据裁决门禁 (Independent Evidence Gate)
=============================================================================
彻底终结“AI 巧言令色自圆其说、假装测试全过”的阿谀奉承病：
1. 物理重放执行冻结的神谕指令，强制要求 Exit Code == 0
2. 校验测试文件是否在编码期间被恶意篡改 (Anti-Tampering Check)
3. 调取 AST 结构解析与代码健康度指标
4. 生成不可伪造的物理证据包 (evidence_bundle.json)，作为合流唯一通关文牒！
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .oracle_freezer import OracleFreezer


class EvidenceGate:
    """G6 独立机器证据裁决门禁"""

    @classmethod
    def evaluate_evidence(
        cls,
        workspace_dir: str,
        oracle_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        ws = Path(workspace_dir).resolve()
        oracle_cmd = oracle_meta.get("oracle_cmd")

        if not oracle_cmd:
            return {
                "is_cleared": False,
                "reason": "未找到冻结的验收神谕指令，严禁在无神谕状态下盲目验收！"
            }

        # 1. 防篡改检查 (Anti-Tampering)
        is_clean, tamper_err = OracleFreezer.verify_oracle_tampering(str(ws), oracle_meta)
        if not is_clean:
            return {
                "is_cleared": False,
                "reason": f"🚨 拦截到神谕测试篡改行为！{tamper_err}。严禁为了通过测试而篡改断言标准！"
            }

        # 2. 物理执行验收指令 (采用 ProcessGuard 硬守护防僵尸进程与死循环)
        from .process_guard import ProcessGuard
        from .candidate_patch_engine import CandidatePatchEngine
        from .mutation_validator import MutationValidator

        res = ProcessGuard.run_guarded_command(oracle_cmd, str(ws), timeout_sec=60)

        if res["timed_out"]:
            return {
                "is_cleared": False,
                "reason": "🚨 验收指令执行超时 (超过 60 秒)！系统已强制强杀子进程树，阻断死循环占用。",
                "exit_code": -124,
                "verdict": "EXECUTION_TIMEOUT_REJECTED"
            }

        is_passed = (res["exit_code"] == 0)

        # 3. 统计代码变动物理事实与候选补丁
        diff_info = CandidatePatchEngine.generate_candidate_patch(str(ws))

        evidence_bundle = {
            "is_cleared": is_passed,
            "timestamp": time.time(),
            "execution_duration_sec": round(res["wall_latency_ms"] / 1000, 3),
            "oracle_cmd": oracle_cmd,
            "exit_code": res["exit_code"],
            "stdout_tail": res["stdout"][-500:] if res["stdout"] else "",
            "stderr_tail": res["stderr"][-500:] if res["stderr"] else "",
            "anti_tampering_passed": True,
            "patch_metrics": diff_info,
            "verdict": "PHYSICAL_PROOF_VALIDATED" if is_passed else "VERIFICATION_REJECTED"
        }

        # 持久化证据档案与人机审查数据包
        bundle_file = ws / ".agent_lifecycle" / "evidence_bundle.json"
        bundle_file.parent.mkdir(parents=True, exist_ok=True)
        bundle_file.write_text(json.dumps(evidence_bundle, indent=2, ensure_ascii=False), encoding="utf-8")

        # 自动生成 review_packet.json
        CandidatePatchEngine.build_review_packet(
            str(ws),
            {"current_phase": "G6_EVIDENCE_VERIFIED" if is_passed else "G5_CHECKPOINT_SECURED"},
            evidence_bundle=evidence_bundle,
            reason="PHYSICAL_PROOF_PASSED" if is_passed else "ORACLE_ASSERTION_FAILED"
        )

        return evidence_bundle
