#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/candidate_patch_engine.py: 候选补丁包与人机审查数据包引擎 (Candidate Patch & Review Packet Engine)
=============================================================================
遵循 Google Tricorder 与 Meta SapFix 工业界规范：
1. 彻底落实“非侵入、不越权”：所有改动在合流前生成标准 Unified Diff (candidate.patch)。
2. 自动化装配人机审查数据包 (review_packet.json)，记录物理时延、内存开销与断言有效性。
3. 提供原子化一键合流 (apply) 与一键丢弃 (discard) 接口，合流权完全归属人类工程师或顶层中枢。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class CandidatePatchEngine:
    """标准候选补丁与人机协作审查包中枢"""

    @classmethod
    def generate_candidate_patch(
        cls,
        workspace_dir: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """提取当前工作区与上次提交的物理 Diff 并打包"""
        ws = Path(workspace_dir).resolve()
        out_p = Path(output_dir).resolve() if output_dir else ws / ".agent_lifecycle"
        out_p.mkdir(parents=True, exist_ok=True)

        patch_file = out_p / "candidate.patch"

        proc = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=str(ws),
            capture_output=True,
            text=True
        )

        diff_content = proc.stdout

        # 如果没有未暂存修改，再检查 staged
        if not diff_content.strip():
            proc_cached = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=str(ws),
                capture_output=True,
                text=True
            )
            diff_content = proc_cached.stdout

        patch_file.write_text(diff_content, encoding="utf-8")

        # 统计修改行数
        added_lines = sum(1 for line in diff_content.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed_lines = sum(1 for line in diff_content.splitlines() if line.startswith("-") and not line.startswith("---"))

        return {
            "patch_path": str(patch_file),
            "diff_bytes": len(diff_content.encode("utf-8")),
            "lines_added": added_lines,
            "lines_removed": removed_lines,
            "has_changes": bool(diff_content.strip())
        }

    @classmethod
    def build_review_packet(
        cls,
        workspace_dir: str,
        state_meta: Dict[str, Any],
        evidence_bundle: Optional[Dict[str, Any]] = None,
        reason: str = "NORMAL_VERIFIED"
    ) -> Dict[str, Any]:
        """组装供人类或顶层大脑审查的独立数据包"""
        ws = Path(workspace_dir).resolve()
        lifecycle_dir = ws / ".agent_lifecycle"
        lifecycle_dir.mkdir(parents=True, exist_ok=True)

        patch_info = cls.generate_candidate_patch(str(ws), str(lifecycle_dir))

        packet = {
            "packet_id": f"REV_{int(os.times().elapsed * 1000)}",
            "reason": reason,
            "lifecycle_phase": state_meta.get("current_phase", "UNKNOWN"),
            "current_goal": state_meta.get("active_intent", {}).get("raw_goal", "N/A"),
            "patch_metrics": patch_info,
            "evidence": evidence_bundle or {},
            "commands": {
                "inspect": "git diff HEAD",
                "apply": "python main.py apply",
                "discard": "python main.py discard"
            }
        }

        packet_file = lifecycle_dir / "review_packet.json"
        packet_file.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

        return packet

    @classmethod
    def apply_candidate_patch(cls, workspace_dir: str) -> Dict[str, Any]:
        """将生成的 candidate.patch 正式原子合入 Git 主分支"""
        ws = Path(workspace_dir).resolve()
        patch_file = ws / ".agent_lifecycle" / "candidate.patch"

        if not patch_file.exists():
            return {"success": False, "reason": "未找到待合流的 candidate.patch 补丁文件！"}

        # git apply
        proc = subprocess.run(
            ["git", "apply", "--check", str(patch_file)],
            cwd=str(ws),
            capture_output=True,
            text=True
        )
        if proc.returncode != 0:
            return {"success": False, "reason": f"补丁冲突预检失败: {proc.stderr}"}

        proc_apply = subprocess.run(
            ["git", "commit", "-am", "[Agent Lifecycle] Merge candidate patch"],
            cwd=str(ws),
            capture_output=True,
            text=True
        )

        return {"success": True, "output": proc_apply.stdout}

    @classmethod
    def discard_candidate_patch(cls, workspace_dir: str) -> Dict[str, Any]:
        """一键丢弃候选修改，恢复至健康主线"""
        ws = Path(workspace_dir).resolve()
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=str(ws), capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=str(ws), capture_output=True)
        return {"success": True, "message": "已彻底丢弃未合流候选补丁，工作区已恢复纯净！"}
