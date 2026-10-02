#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/reflexion_distiller.py: G7 经验反思与知识持久化蒸馏器 (Reflexion Distiller)
=============================================================================
彻底终结“会话窗口关闭、AI 失忆下次再踩坑”的知识流失绝症：
1. 蒸馏本次任务的核心决策、重大重构理由与避坑要点
2. 自动化沉淀只增不改架构决策日志 (ADR)
3. 沉淀至智能体长期记忆库 (reflexion_memory.jsonl)，使系统具备跨任务自我进化能力
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class ReflexionDistiller:
    """G7 认知反思与经验蒸馏器"""

    @classmethod
    def distill_and_record(
        cls,
        workspace_dir: str,
        goal: str,
        decisions: List[str],
        pitfalls_avoided: List[str],
        adr_title: Optional[str] = None
    ) -> Dict[str, Any]:
        ws = Path(workspace_dir).resolve()
        lifecycle_dir = ws / ".agent_lifecycle"
        lifecycle_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        date_id = time.strftime("%Y%m%d_%H%M%S", time.localtime())

        title = adr_title or f"ADR-{date_id}: {goal[:30]}"

        # 1. 沉淀 Markdown 格式架构决策日志
        adr_dir = ws / "docs"
        adr_dir.mkdir(parents=True, exist_ok=True)
        adr_file = adr_dir / "ADR_LEDGER.md"

        adr_content = f"""
## 📌 [{timestamp_str}] {title}

* **业务目标与问题域**: {goal}
* **核心架构设计决策**:
"""
        for d in decisions:
            adr_content += f"  - [✓] {d}\n"

        adr_content += "* **踩坑记录与避障反思 (Reflexion)**:\n"
        for p in pitfalls_avoided:
            adr_content += f"  - [⚠️ 经验] {p}\n"

        adr_content += "\n---\n"

        # 追加写入
        with open(adr_file, "a", encoding="utf-8") as f:
            f.write(adr_content)

        # 2. 沉淀机读长期记忆 (reflexion_memory.jsonl)
        memory_file = lifecycle_dir / "reflexion_memory.jsonl"
        record = {
            "timestamp": time.time(),
            "datetime": timestamp_str,
            "goal": goal,
            "decisions": decisions,
            "pitfalls_avoided": pitfalls_avoided
        }
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return {
            "status": "REFLEXION_DISTILLED",
            "adr_file": str(adr_file),
            "memory_file": str(memory_file),
            "distilled_decisions_count": len(decisions),
            "distilled_pitfalls_count": len(pitfalls_avoided)
        }
