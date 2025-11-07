import React, { useState, useRef, useEffect } from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

function App() {
  const [threadId, setThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [context, setContext] = useState({
    level: "Beginner",
    canton: "",
    waterbody: "",
    place: "",
    user_type: "resident",
  });
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [messageFiles, setMessageFiles] = useState([]); // Files attached to current message
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    fetch("http://localhost:5000/api/thread", { method: "POST" })
      .then(r => r.json())
      .then(d => setThreadId(d.thread_id))
      .catch(e => console.error("Failed to create thread:", e));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    fetch("http://localhost:5000/api/files")
      .then(r => r.json())
      .then(d => setAttachedFiles(d.files || []))
      .catch(e => console.error("Failed to load files:", e));
  }, []);

  // Auto-resize textarea smoothly
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "24px";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = Math.min(scrollHeight, 150) + "px";
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !threadId || loading) return;

    const userMsg = { 
      role: "user", 
      text: input,
      files: messageFiles.length > 0 ? messageFiles : null
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setMessageFiles([]); // Clear message files after sending
    setAttachedFiles([]); // Clear from UI
    if (textareaRef.current) {
      textareaRef.current.style.height = "24px";
    }
    setLoading(true);

    try {
      // Only include non-empty context values
      const filteredContext = {
        level: context.level || "Beginner",
        canton: context.canton || null,
        waterbody: context.waterbody || null,
        place: context.place || null,
        user_type: context.user_type || "resident",
      };
      
      // Remove null values
      Object.keys(filteredContext).forEach(key => {
        if (filteredContext[key] === null || filteredContext[key] === "") {
          delete filteredContext[key];
        }
      });

      const params = new URLSearchParams({
        thread_id: threadId,
        message: input,
        context: JSON.stringify(filteredContext)
      });

      const eventSource = new EventSource(
        `http://localhost:5000/api/chat?${params.toString()}`
      );

      let assistantText = "";
      let assistantMsgAdded = false;

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.done) {
          eventSource.close();
          setLoading(false);
        } else if (data.text) {
          assistantText += data.text + "\n";
          setMessages(prev => {
            const copy = [...prev];
            if (copy[copy.length - 1]?.role === "assistant" && copy[copy.length - 1]?.text === "") {
              copy[copy.length - 1].text = assistantText;
              assistantMsgAdded = true;
            } else if (!assistantMsgAdded && (copy.length === 0 || copy[copy.length - 1]?.role !== "assistant")) {
              copy.push({ role: "assistant", text: assistantText });
              assistantMsgAdded = true;
            } else if (assistantMsgAdded) {
              copy[copy.length - 1].text = assistantText;
            }
            return copy;
          });
        }
      };

      eventSource.onerror = (err) => {
        console.error("Stream error:", err);
        eventSource.close();
        setLoading(false);
      };

      setMessages(prev => [...prev, { role: "assistant", text: "" }]);
    } catch (err) {
      console.error("Chat error:", err);
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log(`[INFO] Uploading file: ${file.name}`);
      const res = await fetch("http://localhost:5000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      
      if (data.file_id) {
        console.log(`[INFO] File uploaded: ${data.file_id}`);
        const newFile = { id: data.file_id, filename: data.filename };
        setAttachedFiles(prev => [...prev, newFile]);
        setMessageFiles(prev => [...prev, newFile]); // Add to message files
      } else {
        console.error(`[ERROR] Upload failed: ${data.error}`);
        alert(`Upload failed: ${data.error}`);
      }
    } catch (err) {
      console.error(`[ERROR] Upload failed: ${err.message}`);
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      fileInputRef.current.value = "";
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await fetch(`http://localhost:5000/api/files/${fileId}`, { method: "DELETE" });
      setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
      setMessageFiles(prev => prev.filter(f => f.id !== fileId));
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  return (
    <div className="app">
      <div className="chat-container">
        <div className="chat-header">
          <h1>FishBuddyGPT</h1>
        </div>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>Start a conversation about fishing in Switzerland</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              msg.text || msg.role === "user" ? (
                <div key={i} className={`message ${msg.role}`}>
                  <div className={`message-bubble ${msg.role}`}>
                    {msg.text}
                    {msg.files && msg.files.length > 0 && (
                      <div className="message-files">
                        {msg.files.map(f => (
                          <div key={f.id} className="message-file-badge">
                            📎 {f.filename}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : null
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="message-bubble assistant typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <div className="attached-files">
            {attachedFiles.map(f => (
              <div key={f.id} className="file-chip">
                <span>{f.filename}</span>
                <button onClick={() => handleDeleteFile(f.id)}>×</button>
              </div>
            ))}
          </div>

          <div className="input-wrapper">
            <button 
              className="file-button" 
              onClick={() => fileInputRef.current.click()}
              title="Attach file"
              disabled={uploading}
            >
              {uploading ? "..." : "+"}
            </button>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              style={{ display: "none" }}
              accept=".pdf,.txt,.doc,.docx,.md"
            />
            
            <textarea
              ref={textareaRef}
              className="message-input"
              value={input}
              onChange={handleInputChange}
              onKeyPress={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder=""
              disabled={loading}
              rows="1"
            />
            
            <button 
              className={`send-button ${input.trim() ? "active" : ""}`}
              onClick={handleSend} 
              disabled={loading}
              title="Send"
            >
              ↑
            </button>
          </div>
        </div>
      </div>

      <div className="sidebar">
        <div className="sidebar-content">
          <h3>Context</h3>
          
          <div className="settings-group">
            <label>Level</label>
            <select value={context.level} onChange={e => setContext({...context, level: e.target.value})}>
              <option>Beginner</option>
              <option>Intermediate</option>
              <option>Expert</option>
            </select>
          </div>

          <div className="settings-group">
            <label>Canton</label>
            <input 
              value={context.canton} 
              onChange={e => setContext({...context, canton: e.target.value})} 
              placeholder="e.g., ZH, BE, LU..."
            />
          </div>

          <div className="settings-group">
            <label>Water Body</label>
            <input 
              value={context.waterbody} 
              onChange={e => setContext({...context, waterbody: e.target.value})} 
              placeholder="e.g., Zürichsee, Reuss..."
            />
          </div>

          <div className="settings-group">
            <label>Place</label>
            <input 
              value={context.place} 
              onChange={e => setContext({...context, place: e.target.value})} 
              placeholder="e.g., Zürich, Lucerne..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
