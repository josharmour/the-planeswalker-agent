"""
The Planeswalker Agent - LAN Web Server

A simple FastAPI server to interact with the agent via a web interface.
Run with: python server.py
Access at: http://<your-ip>:8000
"""

import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import socket

# Import the agent
from mtg_agent import create_agent, run_query

app = FastAPI(title="Planeswalker Agent API")

# Initialize agent globally
print("Initializing Agent...")
agent = create_agent()
print("Agent Ready!")


class QueryRequest(BaseModel):
    query: str


# HTML Template
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Planeswalker Agent</title>
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --accent-color: #9b59b6;
            --user-msg-bg: #2c3e50;
            --agent-msg-bg: #252525;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        header {
            background-color: var(--card-bg);
            padding: 1rem;
            text-align: center;
            border-bottom: 1px solid #333;
            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        }
        h1 { margin: 0; font-size: 1.5rem; color: var(--accent-color); }
        
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
        }
        
        .message {
            max-width: 80%;
            padding: 1rem;
            border-radius: 10px;
            line-height: 1.5;
            position: relative;
            animation: fadeIn 0.3s ease;
        }
        
        .user-message {
            align-self: flex-end;
            background-color: var(--user-msg-bg);
            border-bottom-right-radius: 2px;
        }
        
        .agent-message {
            align-self: flex-start;
            background-color: var(--agent-msg-bg);
            border-bottom-left-radius: 2px;
            border: 1px solid #333;
            white-space: pre-wrap; /* Preserve formatting */
        }
        
        .loading {
            align-self: flex-start;
            color: #888;
            font-style: italic;
            font-size: 0.9rem;
        }

        #input-area {
            background-color: var(--card-bg);
            padding: 1rem;
            display: flex;
            gap: 0.5rem;
            max-width: 800px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
            border-top: 1px solid #333;
        }
        
        input[type="text"] {
            flex: 1;
            padding: 0.8rem;
            border-radius: 5px;
            border: 1px solid #444;
            background-color: #2a2a2a;
            color: white;
            font-size: 1rem;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: var(--accent-color);
        }
        
        button {
            padding: 0 1.5rem;
            background-color: var(--accent-color);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }
        
        button:hover { background-color: #8e44ad; }
        button:disabled { background-color: #555; cursor: not-allowed; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Markdown-like styling for agent responses */
        .agent-message h3 { margin-top: 0.5rem; color: #fff; border-bottom: 1px solid #444; padding-bottom: 0.2rem; }
        .agent-message ul { padding-left: 1.2rem; }
        .agent-message li { margin-bottom: 0.3rem; }
    </style>
</head>
<body>
    <header>
        <h1>Planeswalker Agent</h1>
        <div style="font-size: 0.8rem; color: #888;">Semantic Search + Metagame Intelligence</div>
    </header>

    <div id="chat-container">
        <div class="message agent-message">
            Hello! I am your AI assistant for Magic: The Gathering.
            <br><br>
            I can help you find cards, build decks, and understand the metagame.
            <br>
            Try asking: <i>"What are good cards for an Atraxa deck?"</i> or <i>"Show me trending commanders."</i>
        </div>
    </div>

    <div id="input-area">
        <input type="text" id="query-input" placeholder="Ask a question..." autocomplete="off">
        <button id="send-btn">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const input = document.getElementById('query-input');
        const sendBtn = document.getElementById('send-btn');

        function addMessage(text, isUser, isLoading=false) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user-message' : 'agent-message') + (isLoading ? ' loading' : '');
            if (!isUser && !isLoading) {
                // Simple formatting - just convert newlines to br
                div.innerHTML = text.split('\\n').join('<br>');
            } else {
                div.textContent = text;
            }
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return div;
        }

        async function handleSend() {
            const query = input.value.trim();
            if (!query) return;

            // Add user message
            addMessage(query, true);
            input.value = '';
            input.disabled = true;
            sendBtn.disabled = true;

            // Add loading indicator
            const loadingDiv = addMessage("Thinking...", false, true);

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });

                const data = await response.json();
                
                // Remove loading
                loadingDiv.remove();

                if (data.response) {
                    addMessage(data.response, false);
                } else {
                    addMessage("Error: No response from agent.", false);
                }

            } catch (err) {
                loadingDiv.remove();
                addMessage("Error connecting to server.", false);
                console.error(err);
            } finally {
                input.disabled = false;
                sendBtn.disabled = false;
                input.focus();
            }
        }

        sendBtn.addEventListener('click', handleSend);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleSend();
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_home():
    return HTML_CONTENT


@app.post("/api/query")
async def query_agent(request: QueryRequest):
    start_time = time.time()
    try:
        # Use existing run_query logic from mtg_agent.py
        # run_query takes (agent, query) and returns dict with "final_response"
        result = run_query(agent, request.query)
        response_text = result.get("final_response", "I couldn't generate a response.")

        return {"response": response_text, "time": time.time() - start_time}
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}", "error": True}


def get_local_ip():
    try:
        # Connect to a public DNS to get the local interface IP used for routing
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    local_ip = get_local_ip()
    print(f"\n" + "=" * 50)
    print(f"PLANESWALKER AGENT SERVER")
    print(f"=" * 50)
    print(f"Server starting...")
    print(f"Local Access: http://localhost:8000")
    print(f"LAN Access:   http://{local_ip}:8000")
    print(f"=" * 50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
