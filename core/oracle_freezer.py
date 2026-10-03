#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/oracle_freezer.py: G3 验收神谕前置与红灯先验断言器 (Oracle Freezer)
=============================================================================
彻底杜绝“写完代码再编测试、修改断言迎合 Bug”的同义反复伪造：
1. 在动任何生产代码前，执行验收神谕指令，确认当前处于红灯态 (Exit Code != 0)
2. 锁定神谕指令与关联测试文件的 SHA-256 不可变哈希签名
3. 后续执行阶段一旦检测到神谕文件被篡改，立即触发作弊报警并阻断合流！
"""

import os
import sys
import ast
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class OracleFreezeError(Exception):
    pass


class OracleFreezer:
    """G3 验收神谕冻结与红灯先验引擎"""

    @classmethod
    def freeze_oracle(
        cls,
        workspace_dir: str,
        oracle_cmd: str,
        test_files: Optional[List[str]] = None,
        allow_preexisting_green: bool = False
    ) -> Dict[str, Any]:
        ws = Path(workspace_dir).resolve()
        cmd = oracle_cmd.strip()
        if not cmd:
            raise OracleFreezeError("验收神谕执行指令不能为空！")

        # 1. 计算关联测试文件的物理哈希
        file_hashes = {}
        if test_files:
            for tf in test_files:
                tf_path = ws / tf if not Path(tf).is_absolute() else Path(tf)
                if tf_path.exists() and tf_path.is_file():
                    content = tf_path.read_bytes()
                    file_hashes[str(tf_path.relative_to(ws))] = hashlib.sha256(content).hexdigest()
                else:
                    file_hashes[str(tf)] = "NOT_CREATED_YET"

        # 1.1 AST 语义防作弊检验 (动态发现 tool-problem-optima 或退化至内置独立 AST 检验)
        if test_files:
            auditor = cls._resolve_ast_auditor()
            for tf in test_files:
                tf_path = ws / tf if not Path(tf).is_absolute() else Path(tf)
                if tf_path.exists() and tf_path.suffix == ".py":
                    src_text = tf_path.read_text(encoding="utf-8", errors="ignore")
                    if auditor:
                        try:
                            findings = auditor(src_text, file_path=str(tf_path))
                            gaming_codes = {"PRB-E104", "PRB-E105", "PRB-E401", "PRB-E402", "PRB-E003"}
                            bad_findings = [f for f in findings if f.code in gaming_codes]
                            if bad_findings:
                                f0 = bad_findings[0]
                                raise OracleFreezeError(
                                    f"🚨 G3 验收神谕物理拒绝：测试文件 [{tf}] 包含作弊测试病理 [{f0.code}] {f0.name}！\n"
                                    f"详细说明: {f0.message}\n"
                                    f"修复建议: {f0.remediation_suggestion}"
                                )
                        except OracleFreezeError:
                            raise
                        except Exception:
                            # 容错降级至独立内置检验
                            cls._standalone_ast_check(src_text, str(tf_path))
                    else:
                        # 独立模式运行：执行内置 AST 防作弊断言
                        cls._standalone_ast_check(src_text, str(tf_path))

        # 2. 物理执行神谕指令，检验红灯先验 (TDD 核心：新功能代码未写前必须失败)
        from .process_guard import ProcessGuard
        res = ProcessGuard.run_guarded_command(cmd, str(ws), timeout_sec=30)

        if res["timed_out"]:
            raise OracleFreezeError("🚨 神谕指令执行超时！超过 30 秒无响应，已强杀子进程树，防止死循环命令挂起宿主机！")

        is_red = (res["exit_code"] != 0)

        # 严格红灯断言
        if not is_red and not allow_preexisting_green:
            raise OracleFreezeError(
                f"🚨 神谕先验红灯校验失败！\n"
                f"在尚未开始编写功能代码前，执行指令 [{cmd}] 的退出码居然为 0 (测试通过)！\n"
                f"这说明该测试用例无法衡量新开发的代码，属于同义反复、空断言或已实现逻辑。\n"
                f"必须首先编写能够精准捕获未实现缺陷的真实失败测试，才能冻结神谕！"
            )

        cmd_hash = hashlib.sha256(cmd.encode("utf-8")).hexdigest()

        return {
            "status": "ORACLE_FROZEN",
            "oracle_cmd": cmd,
            "cmd_sha256": cmd_hash,
            "test_file_hashes": file_hashes,
            "pre_execution_red_state_verified": is_red,
            "initial_exit_code": res["exit_code"],
            "initial_stderr_sample": (res["stderr"] or res["stdout"])[:300].strip(),
            "wall_latency_ms": res["wall_latency_ms"]
        }

    @classmethod
    def verify_oracle_tampering(
        cls,
        workspace_dir: str,
        frozen_meta: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """检查神谕文件是否在执行过程中被篡改"""
        ws = Path(workspace_dir).resolve()
        saved_hashes = frozen_meta.get("test_file_hashes", {})

        for rel_file, orig_hash in saved_hashes.items():
            if orig_hash == "NOT_CREATED_YET":
                continue
            f_path = ws / rel_file
            if not f_path.exists():
                return False, f"神谕测试文件被删除: {rel_file}"
            curr_hash = hashlib.sha256(f_path.read_bytes()).hexdigest()
            if curr_hash != orig_hash:
                return False, f"神谕测试文件发生非授权篡改 (Hash Mismatch): {rel_file}"

        return True, None

    @classmethod
    def _resolve_ast_auditor(cls):
        """动态解析外部 tool-problem-optima 的 audit_source_code，解耦绝对路径依赖"""
        try:
            from engine.ast_interceptor import audit_source_code
            return audit_source_code
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
            if c.exists() and (c / "engine" / "ast_interceptor.py").exists():
                c_str = str(c.resolve())
                if c_str not in sys.path:
                    sys.path.insert(0, c_str)
                try:
                    from engine.ast_interceptor import audit_source_code
                    return audit_source_code
                except ImportError:
                    continue
        return None

    @classmethod
    def _standalone_ast_check(cls, src_text: str, file_path: str):
        """零依赖独立运行模式下的 AST 基本防作弊与语法断言器"""
        try:
            tree = ast.parse(src_text, filename=file_path)
        except SyntaxError as e:
            raise OracleFreezeError(f"🚨 G3 验收神谕物理拒绝：测试文件 [{file_path}] 存在语法解析错误！\n详细说明: {e}")

        has_test_func = False
        test_funcs_with_asserts = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                has_test_func = True
                assert_count = sum(1 for n in ast.walk(node) if isinstance(n, (ast.Assert, ast.Call)))
                if assert_count > 0:
                    test_funcs_with_asserts += 1
                for n in ast.walk(node):
                    if isinstance(n, ast.Assert):
                        test_expr = n.test
                        if isinstance(test_expr, ast.Constant) and test_expr.value is True:
                            raise OracleFreezeError(f"🚨 G3 验收神谕物理拒绝：测试文件 [{file_path}] 包含恒真断言 'assert True' 作弊！")
                        if isinstance(test_expr, ast.Compare):
                            if (isinstance(test_expr.left, ast.Constant) and
                                len(test_expr.comparators) == 1 and
                                isinstance(test_expr.comparators[0], ast.Constant) and
                                test_expr.left.value == test_expr.comparators[0].value):
                                raise OracleFreezeError(f"🚨 G3 验收神谕物理拒绝：测试文件 [{file_path}] 包含恒真数值比对断言作弊！")
        if has_test_func and test_funcs_with_asserts == 0:
            raise OracleFreezeError(f"🚨 G3 验收神谕物理拒绝：测试文件 [{file_path}] 包含测试函数但缺少任何断言或调用验证！")
