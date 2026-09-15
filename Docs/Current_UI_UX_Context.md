# Current UI/UX Context for RAG Chatbot

Here is the complete context of the current frontend implementation for the Mutual Fund FAQ Chatbot.

## The Problems to Solve
1. **Sync State Visibility**: Currently, if the backend is actively scraping and syncing data to Qdrant (which takes 2-3 minutes), the `/api/chat` endpoint rejects queries and simply returns a hardcoded text string: `"The knowledge base is currently being updated. Please try again in a few minutes."` There is no visual indicator in the UI (like a banner, a progress bar, or a disabled state) to warn the user that syncing is happening in the background. The backend has an endpoint `GET /api/admin/sync/status` which returns `{"is_syncing": true/false}` that the frontend could poll.
2. **Outdated Chat UI**: The current UI uses a very basic layout with simple bubbles and an avatar. We want to ideate a highly modern, premium, "glassmorphism" or sleek aesthetic chat interface.

---

## 1. index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mutual Fund FAQ Assistant</title>
    <meta name="description" content="Facts-only AI assistant for HDFC Mutual Fund scheme information.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="index.css">
</head>
<body>
    <div class="app-background"></div>
    <div class="app-container">
        
        <!-- Floating Sidebar -->
        <aside class="sidebar" id="sidebar">
            <div class="brand">
                <div class="brand-text">
                    <h1>Lumina Finance</h1>
                    <span class="brand-tagline">Mutual Fund FAQ Assistant</span>
                </div>
            </div>

            <!-- Example Queries -->
            <div class="example-questions">
                <h3>Example Queries</h3>
                <div class="action-card" onclick="setQuery('What is the expense ratio of HDFC Mid Cap Fund?')">
                    What is the expense ratio of HDFC Mid Cap Fund?
                </div>
                <div class="action-card" onclick="setQuery('Who is the fund manager of HDFC Small Cap Fund?')">
                    Who is the fund manager of HDFC Small Cap Fund?
                </div>
            </div>
            <div class="sidebar-spacer"></div>
        </aside>

        <!-- Main Content Area -->
        <main class="main-content">
            <!-- Disclaimer Banner -->
            <div class="message-bar warning">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                Facts-only. No investment advice. I am an AI assistant and I only provide factual information from Groww.
            </div>

            <!-- Chat Area -->
            <div class="chat-area" id="chat-area">
                <!-- Chat Header -->
                <header class="chat-header">
                    <div>
                        <h2>Assistant</h2>
                        <span class="status-indicator">
                            <span class="status-dot"></span> Online
                        </span>
                    </div>
                </header>

                <!-- Chat Messages -->
                <div class="chat-window" id="chat-window">
                    <div class="message assistant">
                        <div class="bubble glass-surface">
                            Welcome! I can answer factual questions about HDFC Mutual Fund schemes. How can I help you today?
                        </div>
                    </div>
                </div>

                <!-- Input Area -->
                <div class="input-area">
                    <form id="chat-form">
                        <div class="input-wrapper glass-input">
                            <input type="text" id="query-input" placeholder="Ask a factual question..." autocomplete="off" required>
                            <button type="submit" id="send-btn" class="primary-btn">Send</button>
                        </div>
                    </form>
                </div>
            </div>
        </main>
    </div>
    <script src="index.js"></script>
</body>
</html>
```

## 2. index.js

```javascript
const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const chatWindow = document.getElementById('chat-window');
const sendBtn = document.getElementById('send-btn');
const API_BASE_URL = 'https://hdfc-mutual-fund-faq-groww-production.up.railway.app';

function setQuery(text) {
    queryInput.value = text;
    queryInput.focus();
}

function appendMessage(sender, content, isHtml = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    if (isHtml) bubble.innerHTML = content;
    else bubble.textContent = content;
    msgDiv.appendChild(bubble);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showTyping() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing-msg';
    indicator.innerHTML = `<div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
    chatWindow.appendChild(indicator);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return indicator;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    appendMessage('user', query);
    queryInput.value = '';
    sendBtn.disabled = true;

    const typingIndicator = showTyping();

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await response.json();
        
        if (indicator && indicator.parentNode) indicator.parentNode.removeChild(indicator);

        if (response.ok) {
            let answerHtml = data.answer; // Simplified for brevity
            appendMessage('assistant', answerHtml, true);
        } else {
            appendMessage('assistant', `⚠️ Error: ${data.detail || 'Something went wrong.'}`);
        }
    } catch (error) {
        appendMessage('assistant', '⚠️ Network error. Please ensure the backend server is running.');
    } finally {
        sendBtn.disabled = false;
    }
});
```
