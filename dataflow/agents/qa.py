"""QAAgent – static analysis, sandbox execution, circuit-breaker check."""
from __future__ import annotations

import ast
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from dataflow.schemas.execution import CleaningScript, ExecutionResult
from dataflow.schemas.task_config import TaskConfig


class CircuitBreaker:
    """Stateless check: returns (triggered, reason)."""

    def check(self, result: ExecutionResult, config: TaskConfig) -> tuple[bool, str]:
        max_red = config.circuit_breaker.max_row_reduction
        if result.row_delta_rate < -max_red:
            return (
                True,
                f"Row reduction {abs(result.row_delta_rate):.1%} exceeds "
                f"circuit-breaker threshold {max_red:.1%}",
            )
        if result.rows_before > 0:
            flagged_rate = result.flagged_record_count / result.rows_before
            if flagged_rate > 0.20:
                return (
                    True,
                    f"Flagged-record rate {flagged_rate:.1%} > 20 % – human review required",
                )
        return False, ""


class QAAgent:
    def __init__(
        self,
        task_config: TaskConfig,
        sandbox,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.task_config = task_config
        self.sandbox = sandbox
        self._circuit = CircuitBreaker()

        llm_model = model or task_config.llm_model
        self._llm = ChatOpenAI(
            model=llm_model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            timeout=60,
        )

    async def run(
        self, scripts: list[dict], data_path: str
    ) -> list[ExecutionResult]:
        """
        Takes *all* accumulated scripts, uses only the latest one for execution.
        Returns a list with a single ExecutionResult.
        """
        if not scripts:
            return []

        # Always execute the latest (most recently generated) script
        from dataflow.schemas.execution import CleaningScript as CS
        latest = CS.model_validate(scripts[-1])

        # 1. Static syntax check (fast, no I/O)
        syntax_ok, syntax_err = self._check_syntax(latest.code)
        if not syntax_ok:
            return [
                ExecutionResult(
                    script_id=latest.script_id,
                    success=False,
                    stderr_excerpt=f"SyntaxError: {syntax_err}",
                )
            ]

        # 2. Sandbox execution
        result = await self.sandbox.execute(
            code=latest.code,
            input_path=data_path,
            output_path=latest.output_path,
            timeout=300,
            memory_limit_mb=2048,
        )
        result = result.model_copy(update={"script_id": latest.script_id})

        # 3. Circuit-breaker check
        if result.success:
            triggered, reason = self._circuit.check(result, self.task_config)
            if triggered:
                result = result.model_copy(
                    update={"circuit_breaker_hit": True, "stderr_excerpt": reason}
                )

        return [result]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _check_syntax(code: str) -> tuple[bool, str]:
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as exc:
            return False, str(exc)

    async def classify_error(self, stderr: str) -> str:
        """Ask LLM whether the error is FIXABLE or needs ESCALATION."""
        prompt_path = Path(__file__).parent / "prompts" / "qa_v1.txt"
        sys_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        messages = []
        if sys_content:
            messages.append(SystemMessage(content=sys_content))
        messages.append(HumanMessage(content=f"## Stderr output:\n{stderr[:1500]}"))

        response = await self._llm.ainvoke(messages)
        return response.content
