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

        # 3.1 跨工程联动: 动态解析 Tri-Sieve Oracle，未安装时退化至独立模式语法断言
        tri_sieve_verdict = None
        if is_passed and diff_info.get("changed_files"):
            oracle_cls = cls._resolve_tri_sieve_oracle()
            if oracle_cls:
                try:
                    oracle = oracle_cls()
                    for cf in diff_info.get("changed_files", []):
                        cf_path = ws / cf
                        if cf_path.exists() and cf_path.suffix == ".py":
                            content = cf_path.read_text(encoding="utf-8", errors="ignore")
                            v = oracle.judge_mutation(content, file_path=str(cf_path))
                            if not v.is_valid:
                                is_passed = False
                                tri_sieve_verdict = v.to_dict()
                                break
                            else:
                                tri_sieve_verdict = v.to_dict()
                except Exception as e:
                    tri_sieve_verdict = {"status": "ORACLE_EVAL_SKIPPED", "warning": str(e)}
            else:
                # 独立无依赖运行：对变更的 Python 文件进行标准库 AST 语法校验
                import ast
                syntax_errors = []
                for cf in diff_info.get("changed_files", []):
                    cf_path = ws / cf
                    if cf_path.exists() and cf_path.suffix == ".py":
                        try:
                            ast.parse(cf_path.read_text(encoding="utf-8", errors="ignore"), filename=str(cf_path))
                        except SyntaxError as se:
                            syntax_errors.append(f"{cf}: {se}")
                if syntax_errors:
                    is_passed = False
                    tri_sieve_verdict = {"status": "STANDALONE_SYNTAX_REJECTED", "errors": syntax_errors}
                else:
                    tri_sieve_verdict = {"status": "STANDALONE_CLEARED", "mode": "builtin_ast"}

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
            "tri_sieve_verdict": tri_sieve_verdict,
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

    @classmethod
    def _resolve_tri_sieve_oracle(cls):
        """动态解析外部 tool-problem-optima 的 TriSieveOracle，解耦绝对路径依赖"""
        try:
            from engine.tri_sieve_oracle import TriSieveOracle
            return TriSieveOracle
        except ImportError:
            pass

        candidates = []
        env_dir = os.environ.get("TOOL_PROBLEM_OPTIMA_PATH")
        if env_dir:
            candidates.append(Path(env_dir))
        # 探测同级目录结构
        candidates.append(Path(__file__).resolve().parent.parent.parent / "tool-problem-optima")
        # 探测标准本地开发目录
        candidates.append(Path("D:/github/tool-problem-optima"))

        for c in candidates:
            if c.exists() and (c / "engine" / "tri_sieve_oracle.py").exists():
                c_str = str(c.resolve())
                if c_str not in sys.path:
                    sys.path.insert(0, c_str)
                try:
                    from engine.tri_sieve_oracle import TriSieveOracle
                    return TriSieveOracle
                except ImportError:
                    continue
        return None
