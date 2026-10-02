# tool-lifecycle-harness 核心架构不变量 (Core Invariants)

## 🏛️ 第一性原理不可变原则

1. **绝对状态机拦截 (Strict State Machine Guardrail)**:
   - 智能体软件工程由确定性的 7 阶状态机驱动：
     `G0: IDLE` $\to$ `G1: INTENT_GROUNDED` $\to$ `G2: PLAN_VALIDATED` $\to$ `G3: ORACLE_FROZEN` $\to$ `G4: EXECUTING` $\to$ `G5: CHECKPOINT_SECURED` $\to$ `G6: EVIDENCE_VERIFIED` $\to$ `G7: REFLEXION_DISTILLED`。
   - 任何跳步请求（如未冻结神谕直接执行、未出具证据直接结项）必须物理抛出 `StateTransitionError` 阻断，绝无妥协例外。

2. **红灯先验断言 (Red State Pre-condition)**:
   - 严禁先写代码再写测试！
   - 在修改生产代码之前，验收神谕指令必须处于失败态（Exit Code $\ne$ 0），以物理证明该神谕并非同义反复或已实现的空断言。

3. **神谕不可变哈希 (Oracle Immutability Invariant)**:
   - 神谕冻结后，其测试指令与关联测试文件的 SHA-256 哈希被锁死。
   - 执行阶段一旦发生任何对测试文件的篡改，证据门禁立即以“作弊报警”拒绝结项。

4. **单步可撤销与零脏状态 (Atomic Checkpoint & Zero-Pollution)**:
   - 任何任务执行前必须持有 Git 原子快照。
   - 一旦证据门禁未通过，必须能一键 `rollback` 瞬时回到安全基线，绝不留半行破坏性脏代码。

5. **独立证据裁判 (Actor-Critic Separation)**:
   - 不信任 AI 的自言自语总结，只承认物理机器事实（Exit Code == 0、防篡改校验通过、真实 stdout/stderr、Git diff stat）。

6. **只增不改持久认知 (Append-Only Reflexion Distillation)**:
   - 每次任务的架构决策与避坑反思以追加方式固化到 `ADR_LEDGER.md` 与机读记忆流中，终生传承。
