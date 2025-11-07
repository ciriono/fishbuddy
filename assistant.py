import json
import time
from typing import Dict, Any, List
from openai import OpenAI

from tools import (
    geocode_place, canton_from_place, get_weather_by_place,
    get_water_data, list_species_by_place, check_rules
)

class AssistantSession:
    def __init__(self, api_key: str, assistant_id: str):
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        self.thread = self.client.beta.threads.create()

    def _dispatch_tools(self, run):
        """
        Handle requires_action: Execute tool handlers, submit outputs, return updated run.
        """
        if getattr(run, "status", None) != "requires_action":
            return run
        
        ra = getattr(run, "required_action", None)
        if not ra or getattr(ra, "type", None) != "submit_tool_outputs":
            print(f"[DEBUG] required_action type is {getattr(ra, 'type', None)}, skipping")
            return run

        print(f"[DEBUG] Processing {len(ra.submit_tool_outputs.tool_calls)} tool calls...")
        outs = []
        
        for call in ra.submit_tool_outputs.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            print(f"[DEBUG] Executing tool: {name} with args: {args}")
            
            try:
                if name == "geocode_place":
                    out = geocode_place(**args)
                elif name == "canton_from_place":
                    out = canton_from_place(**args)
                elif name == "get_weather_by_place":
                    out = get_weather_by_place(**args)
                elif name == "get_water_data":
                    out = get_water_data(**args)
                elif name == "list_species_by_place":
                    out = list_species_by_place(**args)
                elif name == "check_rules":
                    out = check_rules(**args)
                else:
                    out = json.dumps({"error": f"unknown tool {name}"})
                
                print(f"[DEBUG] Tool {name} returned: {out[:100]}...")  # print first 100 chars
            except Exception as e:
                print(f"[DEBUG] Tool {name} failed: {e}")
                out = json.dumps({"error": f"tool_execution_failed: {str(e)}"})
            
            outs.append({"tool_call_id": call.id, "output": out})

        # Submit tool outputs and continue the run
        print(f"[DEBUG] Submitting {len(outs)} tool outputs...")
        updated_run = self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread.id,
            run_id=run.id,
            tool_outputs=outs
        )
        print(f"[DEBUG] Run status after submit: {updated_run.status}")
        return updated_run

    def ask(self, context: Dict[str, Any], question: str, poll_seconds: float = 0.6) -> str:
        # 1) Add user message
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=f"StructuredContext: {context}\nQuestion: {question}",
        )
        
        # 2) Start run
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_id,
        )
        print(f"[DEBUG] Run created: {run.id} with status {run.status}")
        
        # 3) Poll until completion, handling requires_action
        terminal = {"completed", "failed", "cancelled", "expired"}
        loop_count = 0
        while True:
            loop_count += 1
            run = self.client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=run.id)
            print(f"[DEBUG] Poll #{loop_count}: run status = {run.status}")
            
            if run.status == "requires_action":
                # Handle tool calls
                run = self._dispatch_tools(run)
                time.sleep(poll_seconds)
                continue
            
            if run.status in terminal:
                print(f"[DEBUG] Run reached terminal state: {run.status}")
                break
            
            time.sleep(poll_seconds)

        if run.status != "completed":
            return f"(Run status: {run.status})"

        # 4) Get newest assistant message for THIS run
        msgs = self.client.beta.threads.messages.list(
            thread_id=self.thread.id,
            order="desc",
            limit=20,
        )
        
        latest = next(
            (m for m in msgs.data if m.role == "assistant" and getattr(m, "run_id", None) == run.id),
            None
        )
        if latest is None:
            latest = next((m for m in msgs.data if m.role == "assistant"), None)
        
        if not latest:
            return "(no assistant reply)"
        
        parts: List[str] = []
        for c in latest.content:
            if getattr(c, "type", None) == "text" and getattr(c, "text", None):
                parts.append(c.text.value or "")
        
        return "\n".join([p for p in parts if p]) or "(no text)"
