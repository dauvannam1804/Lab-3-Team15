import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgent:
    """
    ReAct Agent (Reasoning + Acting) that follows the Thought-Action-Observation loop.
    Supports any LLMProvider (Gemini, OpenAI, Local).
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 7):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[str] = []

    # ------------------------------------------------------------------
    # System Prompt
    # ------------------------------------------------------------------
    def get_system_prompt(self) -> str:
        """Build a detailed system prompt that defines the ReAct format and lists tools."""
        tool_descriptions = "\n".join(
            [f"  - {t['name']}: {t['description']}" for t in self.tools]
        )
        tool_names = ", ".join([t["name"] for t in self.tools])

        return f"""You are an intelligent AI assistant specialised in flight booking.
You have access to the following tools:
{tool_descriptions}

You MUST follow this exact format every turn. Never skip steps:

Thought: <your step-by-step reasoning about what to do next>
Action: <tool_name>({{"arg1": "value1", "arg2": "value2"}})

Wait for an Observation before continuing.

When you have enough information to answer the user:
Thought: I now know the final answer.
Final Answer: <your helpful, concise answer to the user>

Rules:
- Only use tools from this list: {tool_names}
- Action arguments MUST be valid JSON (double-quoted keys and values).
- NEVER fabricate an Observation or a PNR code. Wait for the tool result.
- If a tool returns an error, explain it to the user in your Final Answer.
- Always respond in the same language as the user.
"""

    # ------------------------------------------------------------------
    # Main ReAct Loop
    # ------------------------------------------------------------------
    def run(self, user_input: str) -> str:
        """Execute the Thought → Action → Observation loop until Final Answer or max_steps."""
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        # Build a running transcript; append each LLM turn + Observation
        transcript = f"User: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            # ── 1. Call LLM ──────────────────────────────────────────
            response = self.llm.generate(transcript, system_prompt=self.get_system_prompt())
            llm_text: str = response.get("content", "").strip()
            usage: dict = response.get("usage", {})
            latency: int = response.get("latency_ms", 0)

            logger.log_event("LLM_RESPONSE", {
                "step": steps,
                "content": llm_text,
                "usage": usage,
                "latency_ms": latency,
            })

            # Append LLM output to transcript
            transcript += f"\n{llm_text}\n"

            # ── 2. Check for Final Answer ─────────────────────────────
            if "Final Answer:" in llm_text:
                final_answer = llm_text.split("Final Answer:")[-1].strip()
                logger.log_event("AGENT_END", {
                    "steps": steps + 1,
                    "status": "success",
                    "usage": usage,
                })
                return final_answer

            # ── 3. Parse Action ───────────────────────────────────────
            # Expected format: Action: tool_name({"key": "val"})
            action_match = re.search(
                r"Action:\s*(\w+)\s*\((\{.*?\})\)",
                llm_text,
                re.DOTALL,
            )

            if action_match:
                tool_name = action_match.group(1).strip()
                args_str = action_match.group(2).strip()

                # ── 4. Execute Tool ───────────────────────────────────
                observation = self._execute_tool(tool_name, args_str)
                logger.log_event("TOOL_EXECUTED", {
                    "step": steps,
                    "tool": tool_name,
                    "args": args_str,
                    "observation": observation,
                })

                # Append Observation to transcript for next LLM call
                transcript += f"Observation: {observation}\n"

            else:
                # ── 5. Failure Handling ───────────────────────────────
                error_hint = (
                    "Observation: [SYSTEM] Could not parse an Action from your last response. "
                    "Please follow the format: Action: tool_name({\"key\": \"value\"}) "
                    "or write 'Final Answer: ...' if you are done."
                )
                transcript += f"{error_hint}\n"
                logger.log_event("PARSER_ERROR", {
                    "step": steps,
                    "raw_response": llm_text,
                })

            steps += 1

        # ── 6. Max steps reached ──────────────────────────────────────
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return "Agent could not complete the task within the maximum number of steps."

    # ------------------------------------------------------------------
    # Tool Dispatcher
    # ------------------------------------------------------------------
    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """Dispatch a tool call by name, parsing JSON arguments dynamically."""
        for tool in self.tools:
            if tool["name"] != tool_name:
                continue

            func = tool.get("function")
            if not callable(func):
                return f"[Error] Tool '{tool_name}' has no callable function attached."

            try:
                args: dict = json.loads(args_str) if args_str.strip() else {}
                if not isinstance(args, dict):
                    return f"[Error] Arguments must be a JSON object, got: {type(args).__name__}"
                result = func(**args)
                return str(result)
            except json.JSONDecodeError as e:
                return f"[Error] Invalid JSON in arguments: {e}. Raw: {args_str}"
            except TypeError as e:
                return f"[Error] Wrong arguments for '{tool_name}': {e}"
            except Exception as e:
                return f"[Error] Exception in '{tool_name}': {e}"

        return f"[Error] Tool '{tool_name}' not found. Available: {[t['name'] for t in self.tools]}"
