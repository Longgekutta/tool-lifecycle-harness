#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/intent_grounder.py: G1 意图定格与需求收敛器 (Intent Grounder)
=============================================================================
在制定任何计划之前，执行物理级“意图验真”：
1. 剥离注入的特定实现偏见与私货 (Solution Bias / Pre-mature Tech Stacks)
2. 提取不可违背的刚性验收条件 (Acceptance Invariants)
3. 冻结纯粹问题域陈述，防止需求在后续多轮迭代中发生语义漂移 (Semantic Drift)
"""

import re
from typing import Dict, Any, List


class IntentGrounder:
    """G1 意图定格引擎"""

    BIAS_PATTERNS = [
        (r'(?:用|使用|基于|采用)?\s*(redis|kafka|docker|k8s|kubernetes|mongodb|rabbitmq|spark|flink)', "外部重型服务基础设施依赖"),
        (r'(?:用|使用|基于|采用)?\s*(spring\s*boot|django|express|vue|react|angular)', "全家桶应用框架偏见"),
        (r'(?:必须写成|做成|采用)\s*(微服务|分布式集群|插件系统)', "过度架构设计偏见")
    ]

    @classmethod
    def ground_intent(cls, raw_user_prompt: str) -> Dict[str, Any]:
        prompt = raw_user_prompt.strip()
        if not prompt:
            raise ValueError("用户需求陈述为空，无法进行意图定格！")

        detected_biases = []
        cleaned_goal = prompt

        for pattern, desc in cls.BIAS_PATTERNS:
            matches = re.findall(pattern, prompt, re.IGNORECASE)
            if matches:
                detected_biases.append(desc)
                # 剔除私货干扰词，提取问题核心
                cleaned_goal = re.sub(pattern, "", cleaned_goal, flags=re.IGNORECASE).strip()

        # 整理纯粹问题域描述
        cleaned_goal = re.sub(r'\s+', ' ', cleaned_goal).strip()
        if not cleaned_goal:
            cleaned_goal = prompt

        # 提取验收准则与约束
        invariants = []
        if "不能" in prompt or "严禁" in prompt or "禁止" in prompt or "杜绝" in prompt:
            for sent in re.split(r'[，。；\n]', prompt):
                if any(w in sent for w in ["不能", "严禁", "禁止", "杜绝"]):
                    invariants.append(sent.strip())

        return {
            "raw_prompt": prompt,
            "pure_problem_goal": cleaned_goal,
            "has_solution_bias": len(detected_biases) > 0,
            "detected_biases": detected_biases,
            "explicit_invariants": invariants,
            "status": "GROUNDED"
        }
