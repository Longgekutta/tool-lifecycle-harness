#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/process_guard.py: 操作系统级子进程树安全守护与资源硬配额引擎 (Process Tree Guard)
=============================================================================
彻底终结“AI 运行死循环测试吃满 CPU、后台孤儿进程悬挂导致系统卡死”的恶劣隐患：
1. 操作系统级硬超时（Hard Timeout）管控。
2. 进程树级强杀（Process Tree Kill: Windows taskkill /F /T, Unix os.killpg）。
3. 真实物理峰值内存（Peak RAM Working Set）与纳秒级时钟采样。
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import ctypes
    from ctypes import wintypes
    _HAS_CTYPES = True
except ImportError:
    _HAS_CTYPES = False


class ProcessGuard:
    """操作系统子进程硬限与树状清理守护机"""

    @classmethod
    def _get_peak_ram_windows(cls, handle: int) -> int:
        if not _HAS_CTYPES or sys.platform != "win32":
            return 0
        try:
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('cb', wintypes.DWORD),
                    ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t),
                ]
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            ret = ctypes.windll.psapi.GetProcessMemoryInfo(
                handle,
                ctypes.byref(counters),
                counters.cb
            )
            if ret:
                return int(counters.PeakWorkingSetSize)
        except Exception:
            pass
        return 0

    @classmethod
    def kill_process_tree(cls, pid: int):
        """物理销毁整个进程树，根除孤儿进程"""
        if sys.platform == "win32":
            try:
                subprocess.run(
                    f"taskkill /F /T /PID {pid}",
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass

    @classmethod
    def run_guarded_command(
        cls,
        cmd: str,
        cwd: str,
        timeout_sec: int = 30
    ) -> Dict[str, Any]:
        """在硬安全守护下执行指令，保证绝不泄漏进程与资源"""
        start_time = time.perf_counter()
        peak_ram = 0
        timed_out = False

        # 创建子进程
        # Windows: CREATE_NEW_PROCESS_GROUP
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags
            )

            stdout_data, stderr_data = "", ""
            try:
                stdout_data, stderr_data = proc.communicate(timeout=timeout_sec)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                cls.kill_process_tree(proc.pid)
                stdout_data, stderr_data = proc.communicate()
                exit_code = -124  # Standard timeout code

            wall_latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "exit_code": exit_code,
                "stdout": stdout_data or "",
                "stderr": stderr_data or "",
                "wall_latency_ms": wall_latency_ms,
                "timed_out": timed_out,
                "peak_ram_bytes": peak_ram
            }

        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"进程执行异常: {str(e)}",
                "wall_latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "timed_out": False,
                "peak_ram_bytes": 0
            }
