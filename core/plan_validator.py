#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/plan_validator.py: G2 计划拓扑校验与因果依赖分析器 (Plan Validator)
=============================================================================
彻底终结“AI 随手写无序 Markdown 计划”的非结构化混乱：
1. 校验任务依赖有向图是否存在循环依赖 (DAG Cycle Detection)
2. 强制每个任务单元必须绑定【目标文件】与【验收神谕指令 (oracle_cmd)】
3. 计算任务拓扑执行序列 (Topological Sort Execution Order)
"""

import json
from typing import Dict, Any, List, Set, Tuple


class PlanValidationError(Exception):
    pass


class PlanValidator:
    """G2 计划结构与拓扑依赖校验器"""

    @classmethod
    def validate_plan(cls, plan_data: Dict[str, Any] | List[Dict[str, Any]]) -> Dict[str, Any]:
        tasks = plan_data if isinstance(plan_data, list) else plan_data.get("tasks", [])
        if not tasks:
            raise PlanValidationError("计划内容为空，任务列表 (tasks) 必须至少包含 1 个原子工程步骤！")

        task_map: Dict[str, Dict[str, Any]] = {}
        adj: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}

        for idx, task in enumerate(tasks):
            t_id = task.get("id") or f"task_{idx+1}"
            task["id"] = t_id

            if t_id in task_map:
                raise PlanValidationError(f"检测到重复的任务 ID: '{t_id}'，任务标识必须全域唯一！")

            # 校验刚性三要素：描述、目标文件、神谕指令
            desc = task.get("description", "").strip()
            if not desc:
                raise PlanValidationError(f"任务 [{t_id}] 缺少必要的目标描述 (description)！")

            targets = task.get("target_files", [])
            if not targets:
                raise PlanValidationError(f"任务 [{t_id}] 未声明明确的受控目标文件列表 (target_files)，禁止全仓无界限漫游！")

            oracle = task.get("oracle_cmd", "").strip()
            if not oracle:
                raise PlanValidationError(f"任务 [{t_id}] 未声明验收神谕指令 (oracle_cmd)！任何未声明机器验收指令的任务均为无效计划！")

            task_map[t_id] = task
            adj[t_id] = []
            in_degree[t_id] = 0

        # 构建依赖图
        for t_id, task in task_map.items():
            deps = task.get("dependencies", [])
            for dep in deps:
                if dep not in task_map:
                    raise PlanValidationError(f"任务 [{t_id}] 声明了不存在的前置依赖: '{dep}'")
                adj[dep].append(t_id)
                in_degree[t_id] += 1

        # Kahn 算法拓扑排序与环路检测
        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        topo_order = []

        while queue:
            curr = queue.pop(0)
            topo_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) != len(task_map):
            cycle_tasks = [t_id for t_id, deg in in_degree.items() if deg > 0]
            raise PlanValidationError(f"计划拓扑存在不可解的循环依赖 (Cycle Deadlock): {cycle_tasks}！必须为纯净有向无环图 (DAG)。")

        return {
            "status": "VALIDATED",
            "total_tasks": len(tasks),
            "topological_sequence": topo_order,
            "tasks": [task_map[tid] for tid in topo_order],
            "is_acyclic_dag": True
        }
