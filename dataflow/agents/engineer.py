"""EngineerAgent – reads the quality report and generates a Python cleaning script."""
from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from dataflow.schemas.execution import CleaningScript
from dataflow.schemas.report import DataQualityReport
from dataflow.schemas.task_config import TaskConfig


class EngineerAgent:
    def __init__(
        self,
        model: str = "gpt-4o",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            timeout=180,
        )

    async def run(
        self,
        report: DataQualityReport,
        task_config: TaskConfig,
        input_path: str,
        output_path: str,
        previous_errors: list[str] | None = None,
    ) -> list[CleaningScript]:
        prompt_path = Path(__file__).parent / "prompts" / "engineer_v1.txt"
        sys_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

        col_details = json.dumps(
            [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "null_rate": c.null_rate,
                    "unique_rate": c.unique_rate,
                    "sample_values": c.sample_values[:5],
                    "detected_issues": c.detected_issues,
                }
                for c in report.columns
            ],
            ensure_ascii=False,
            indent=2,
        )

        strategy_json = task_config.cleaning_strategy.model_dump_json(indent=2)
        ext = Path(input_path).suffix  # e.g. ".parquet"

        error_section = ""
        if previous_errors:
            valid = [e for e in previous_errors if e]
            if valid:
                error_section = (
                    "\n\n## ⚠ Previous Execution Errors – you MUST fix these:\n"
                    + "\n---\n".join(valid)
                )

        user_msg = f"""## Task: {task_config.task}
## Description: {task_config.description}
## Cleaning strategy:
{strategy_json}

## Data quality report:
- total_rows: {report.total_rows}
- duplicate_row_rate: {report.duplicate_row_rate:.1%}
- overall_quality_score: {report.overall_quality_score:.2f}
- LLM summary: {report.llm_summary[:400]}

## Column details:
{col_details}

## Sandbox I/O paths:
- Input:  /data/input{ext}
- Output: /data/output.parquet
{error_section}

Write the complete Python cleaning script now."""

        messages = []
        if sys_content:
            messages.append(SystemMessage(content=sys_content))
        messages.append(HumanMessage(content=user_msg))

        response = await self._llm.ainvoke(messages)
        code: str = response.content.strip()

        # Strip markdown fences if the model ignores instructions
        if code.startswith("```"):
            lines = code.splitlines()
            # drop first line (```python) and last line (```)
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        usage = response.usage_metadata or {}
        script = CleaningScript(
            script_id=f"scr-{uuid4().hex[:8]}",
            task_name=task_config.task,
            code=code,
            dependencies=["polars", "pandas", "pyarrow"],
            input_path=input_path,
            output_path=output_path,
            generated_by_model=task_config.llm_model,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )
        return [script]
