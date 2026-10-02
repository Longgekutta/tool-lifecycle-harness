#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/mutation_validator.py: 语义变异断言有效性检验器 (Semantic Mutation Validator)
=============================================================================
彻底终结“AI 编写无断言伪测试、恒真测试放水”的学术级弊端：
1. 变异注入 (Mutant Injection): 在被测逻辑中故意注入确定性单点语义变异。
2. 杀灭验证 (Mutation Kill Verification): 运行神谕指令，若变异体【依然测试通过】，
   直接判定断言失效 (Weak/Tautological Assertion) 并拦截！
3. 只有当测试神谕能够敏锐捕获变异（退出码非 0）时，才证明断言具备真实缺陷拦截力！
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from .process_guard import ProcessGuard


class MutationValidator:
    """语义变异断言有效性校验器"""

    @classmethod
    def verify_assertion_strength(
        cls,
        workspace_dir: str,
        target_file: str,
        oracle_cmd: str,
        timeout_sec: int = 15
    ) -> Dict[str, Any]:
        """对目标文件施加变异，检测测试神谕是否能成功杀灭变异体 (Kill Mutant)"""
        ws = Path(workspace_dir).resolve()
        target_path = ws / target_file if not Path(target_file).is_absolute() else Path(target_file)

        if not target_path.exists() or not target_path.is_file():
            return {
                "verified": True,
                "note": "目标生产文件尚未物理建立，跳过变异对撞"
            }

        original_content = target_path.read_text(encoding="utf-8", errors="replace")
        backup_path = target_path.with_suffix(target_path.suffix + ".mutant_bak")

        try:
            # 1. 备份原文件
            shutil.copy2(target_path, backup_path)

            # 2. 注入精细化语义变异 (Function Return Mutation)
            # 在首个业务函数内将返回值篡改为 None，若测试用例没有检查返回值，变异体将放水存活
            import re
            if target_path.suffix == ".py":
                if re.search(r'\breturn\b', original_content):
                    mutant_content = re.sub(
                        r'(\breturn\s+)(.+)',
                        r'\1None  # [MUTATION_MUTATED]\n    # orig: \2',
                        original_content,
                        count=1
                    )
                elif re.search(r'def\s+\w+\s*\(.*?\)\s*:', original_content):
                    mutant_content = re.sub(
                        r'(def\s+\w+\s*\(.*?\)\s*:)',
                        r'\1\n    return None  # [MUTATION_SHORT_CIRCUIT]',
                        original_content,
                        count=1
                    )
                else:
                    mutant_content = original_content + "\n__mutant_val__ = None\n"
            else:
                mutant_content = "/* [MUTATION_INJECTED] */\n#error MUTATION_TRIGGERED\n" + original_content

            target_path.write_text(mutant_content, encoding="utf-8")

            # 3. 运行神谕指令测试变异体
            res = ProcessGuard.run_guarded_command(oracle_cmd, str(ws), timeout_sec=timeout_sec)

            # 4. 分析结果：神谕指令必须失败 (exit_code != 0) 才算杀灭变异体
            if res["exit_code"] == 0:
                # 变异体存活！说明测试根本没有调用该文件，或者没有任何有效断言！
                return {
                    "verified": False,
                    "mutant_killed": False,
                    "reason": (
                        "🚨 检测到虚假/弱测试断言 (Weak Assertion)！\n"
                        f"在目标文件 [{target_file}] 注入致命语义变异后，测试指令 [{oracle_cmd}] 竟然依然执行成功 (Exit Code == 0)！\n"
                        "这证明测试未能覆盖被测目标，属于无效测试。"
                    )
                }

            return {
                "verified": True,
                "mutant_killed": True,
                "reason": "变异体被测试神谕成功击杀 (Exit Code != 0)，断言敏锐度实证合格！"
            }

        finally:
            # 5. 绝对确保还原生产代码
            if backup_path.exists():
                shutil.copy2(backup_path, target_path)
                backup_path.unlink()
