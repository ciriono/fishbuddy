# app.py
import os
import json
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import tools
from tools import (
    geocode_place, canton_from_place, get_weather_by_place,
    get_water_data, list_species_by_place, check_rules
)

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")

if not api_key:
    raise ValueError("OPENAI_API_KEY not set in environment")
if not assistant_id:
    raise ValueError("ASSISTANT_ID not set in environment")

print(f"[INFO] Using API Key: {api_key[:20]}...")
print(f"[INFO] Using Assistant ID: {assistant_id}")

client = OpenAI(api_key=api_key)

# Keep track of uploaded files per session
session_files = {}

def dispatch_tools(thread_id, run_id, max_retries=5):
    """Execute all tool calls for a run and submit outputs."""
    retry_count = 0
    
    while retry_count < max_retries:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        
        if run.status != "requires_action":
            return run
        
        retry_count += 1
        ra = getattr(run, "required_action", None)
        if not ra or getattr(ra, "type", None) != "submit_tool_outputs":
            return run

        print(f"[DEBUG] Processing {len(ra.submit_tool_outputs.tool_calls)} tool calls (retry {retry_count})...")
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
                
                print(f"[DEBUG] Tool {name} returned: {str(out)[:100]}...")
            except Exception as e:
                print(f"[ERROR] Tool {name} failed: {e}")
                out = json.dumps({"error": f"tool_execution_failed: {str(e)}"})
            
            outs.append({"tool_call_id": call.id, "output": out})

        # Submit tool outputs and continue the run
        print(f"[DEBUG] Submitting {len(outs)} tool outputs...")
        client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=outs
        )
        time.sleep(0.5)
    
    if retry_count >= max_retries:
        print(f"[ERROR] Max retries ({max_retries}) reached for run {run_id}")
    
    return run

@app.route("/api/thread", methods=["POST"])
def create_thread():
    """Create a new thread for this session."""
    try:
        thread = client.beta.threads.create()
        print(f"[INFO] Created thread: {thread.id}")
        return jsonify({"thread_id": thread.id})
    except Exception as e:
        print(f"[ERROR] Failed to create thread: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["GET"])
def chat():
    """
    Stream assistant response using Server-Sent Events.
    Query params: thread_id, message, context
    """
    try:
        thread_id = request.args.get("thread_id")
        message = request.args.get("message")
        context_str = request.args.get("context", "{}")
        
        if not thread_id or not message:
            return jsonify({"error": "Missing thread_id or message"}), 400

        try:
            context = json.loads(context_str)
        except:
            context = {}

        print(f"[INFO] Chat request: thread={thread_id}, message={message[:50]}...")

        # Add user message
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=f"StructuredContext: {context}\nQuestion: {message}",
        )

        # Start run
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )
        print(f"[INFO] Run created: {run.id}")

        def stream_response():
            """Poll run, handle tools, yield streaming response."""
            terminal = {"completed", "failed", "cancelled", "expired"}
            poll_count = 0
            
            while poll_count < 50:  # Max 50 polls = ~25 seconds
                poll_count += 1
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                print(f"[DEBUG] Poll #{poll_count}: run status = {run_status.status}")
                
                if run_status.status == "requires_action":
                    run_status = dispatch_tools(thread_id, run.id, max_retries=3)
                    time.sleep(0.5)
                    continue
                
                if run_status.status in terminal:
                    print(f"[INFO] Run reached terminal state: {run_status.status}")
                    break
                
                time.sleep(0.5)
            
            if poll_count >= 50:
                print(f"[WARN] Poll limit reached, stopping stream")

            # Fetch latest assistant message
            msgs = client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=20,
            )
            
            latest = next(
                (m for m in msgs.data if m.role == "assistant" and getattr(m, "run_id", None) == run.id),
                None
            ) or next((m for m in msgs.data if m.role == "assistant"), None)

            if latest:
                for c in latest.content:
                    if getattr(c, "type", None) == "text" and getattr(c, "text", None):
                        text = c.text.value or ""
                        # Simulate streaming by yielding line by line
                        for line in text.split("\n"):
                            if line.strip():
                                yield f"data: {json.dumps({'text': line})}\n\n"
            
            yield "data: {\"done\": true}\n\n"

        return Response(stream_response(), mimetype="text/event-stream")
    
    except Exception as e:
        print(f"[ERROR] Chat endpoint failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload a file to OpenAI."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files["file"]
        filename = file.filename
        
        print(f"[INFO] Uploading file to OpenAI: {filename}")
        
        # Convert Flask FileStorage to bytes
        file_bytes = file.read()
        
        # Upload to OpenAI Files API using bytes
        file_response = client.files.create(
            file=(filename, file_bytes),
            purpose="assistants"
        )
        
        file_id = file_response.id
        print(f"[INFO] File uploaded to OpenAI: {file_id}")
        
        # Attach file to assistant
        try:
            client.beta.assistants.update(
                assistant_id=assistant_id,
                file_ids=[file_id]
            )
            print(f"[INFO] File attached to assistant: {file_id}")
        except Exception as e:
            print(f"[WARN] Could not attach file to assistant: {e}")
        
        # Track the file in current session only
        session_files[file_id] = {
            "id": file_id,
            "filename": filename,
            "uploaded_at": time.time()
        }
        
        return jsonify({
            "file_id": file_id,
            "filename": filename,
            "status": "uploaded"
        })
    
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/files", methods=["GET"])
def list_files():
    """List files uploaded in current session only."""
    try:
        # Return only files from current session
        files_list = [
            {
                "id": file_id,
                "filename": data["filename"]
            }
            for file_id, data in session_files.items()
        ]
        
        print(f"[INFO] Returning {len(files_list)} session files")
        
        return jsonify({"files": files_list})
    except Exception as e:
        print(f"[ERROR] List files failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """Delete a file from current session and OpenAI."""
    try:
        # Delete from OpenAI
        client.files.delete(file_id)
        print(f"[INFO] File deleted from OpenAI: {file_id}")
        
        # Remove from session tracking
        if file_id in session_files:
            del session_files[file_id]
            print(f"[INFO] File removed from session: {file_id}")
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"[ERROR] Delete file failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "FishBuddy backend is running"})

if __name__ == "__main__":
    print("[INFO] Starting FishBuddy Flask backend...")
    print("[INFO] CORS enabled for http://localhost:5173")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
