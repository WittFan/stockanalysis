"""迭代预算 + Token 预算控制 — 防止 Agent 无限循环和超额消耗"""


class BudgetExhaustedError(Exception):
    pass


class IterationBudget:
    """控制 ReAct 循环的最大迭代次数（每执行一批工具调用算一次）"""

    def __init__(self, max_iterations: int = 10):
        self.max = max_iterations
        self.used = 0

    def tick(self):
        self.used += 1
        if self.used >= self.max:
            raise BudgetExhaustedError(f"已达最大迭代次数 {self.max}")

    def is_exhausted(self) -> bool:
        return self.used >= self.max

    def remaining(self) -> int:
        return max(0, self.max - self.used)


class TokenBudget:
    """
    粗略 Token 消耗追踪（无需 tiktoken）。
    用于防止单次对话耗尽 API 额度。
    超出预算时在 agent_loop 中提前终止并通知前端。
    """

    def __init__(self, max_tokens: int = 80_000):
        self.max = max_tokens
        self.used = 0

    def charge(self, text: str):
        """估算并扣减 token（中文 ≈ 0.7/字，英文 ≈ 0.25/字符）"""
        if not text:
            return
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other = len(text) - chinese
        self.used += int(chinese * 0.7 + other * 0.25) + 1

    def is_exhausted(self) -> bool:
        return self.used >= self.max

    def remaining(self) -> int:
        return max(0, self.max - self.used)
