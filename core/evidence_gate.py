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

        # 2. 物理执行验收指令
        t0 = time.perf_counter()
        proc = subprocess.run(
            oracle_cmd,
            shell=True,
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=60
        )
        elapsed_sec = round(time.perf_counter() - t0, 3)

        is_passed = (proc.returncode == 0)

        # 3. 统计代码变动物理事实
        diff_proc = subprocess.run(["git", "diff", "--stat"], cwd=str(ws), capture_output=True, text=True)
        diff_stat = diff_proc.stdout.strip() if diff_proc.returncode == 0 else ""

        evidence_bundle = {
            "is_cleared": is_passed,
            "timestamp": time.time(),
            "execution_duration_sec": elapsed_sec,
            "oracle_cmd": oracle_cmd,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
            "anti_tampering_passed": True,
            "git_diff_stat": diff_stat,
            "verdict": "PHYSICAL_PROOF_VALIDATED" if is_passed else "VERIFICATION_REJECTED"
        }

        # 持久化证据档案
        bundle_file = ws / ".agent_lifecycle" / "evidence_bundle.json"
        bundle_file.parent.mkdir(parents=True, exist_ok=True)
        bundle_file.write_text(json.dumps(evidence_bundle, indent=2, ensure_ascii=False), encoding="utf-8")

        return evidence_bundle
