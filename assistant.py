import time
from typing import Dict, Any, Optional
from openai import OpenAI

class AssistantSession:
    def __init__(self, api_key: str, assistant_id: str):
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id
        self.thread = self.client.beta.threads.create()

    def ask(self, context: Dict[str, Any], question: str, poll_seconds: float = 0.6) -> str:
        self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=f"StructuredContext: {context}\nQuestion: {question}",
        )
        run = self.client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant_id,
        )
        while True:
            status = self.client.beta.threads.runs.retrieve(thread_id=self.thread.id, run_id=run.id).status
            if status in ("completed", "failed", "requires_action", "cancelled", "expired"):
                break
            time.sleep(poll_seconds)
        if status != "completed":
            return f"(Run status: {status})"
        msgs = self.client.beta.threads.messages.list(thread_id=self.thread.id)
        for m in reversed(msgs.data):
            if m.role == "assistant":
                parts = [c.text.value for c in m.content if getattr(c, "type", None) == "text"]
                return "\n".join(parts) if parts else "(no text)"
        return "(no assistant reply)"
