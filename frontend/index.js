// API base URL — points to Render backend
const API_BASE = 'https://hdfc-mutual-fund-rag-chatbot-groww.onrender.com';

const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const chatWindow = document.getElementById('chat-window');
const sendBtn = document.getElementById('send-btn');
const syncBtn = document.getElementById('sync-btn');
const syncStatus = document.getElementById('sync-status');
const chatArea = document.getElementById('chat-area');
const syncOverlay = document.getElementById('sync-overlay');

// Helper to set query from example cards
function setQuery(text) {
    queryInput.value = text;
    queryInput.focus();
}

// Markdown to HTML simple parser (bold text)
function parseMarkdown(text) {
    if (!text) return '';
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return html;
}

// Create assistant avatar SVG
function createAvatarSVG() {
    return `<div class="message-avatar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
            <path d="M2 17l10 5 10-5"></path>
            <path d="M2 12l10 5 10-5"></path>
        </svg>
    </div>`;
}

// Append message to chat
function appendMessage(sender, content, isHtml = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;

    let innerHtml = '';

    if (sender === 'assistant') {
        innerHtml += createAvatarSVG();
    }

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (isHtml) {
        bubble.innerHTML = content;
    } else {
        bubble.textContent = content;
    }

    msgDiv.innerHTML = innerHtml;
    msgDiv.appendChild(bubble);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Show typing indicator
function showTyping() {
    const indicator = document.createElement('div');
    indicator.className = 'message assistant typing-msg';
    indicator.innerHTML = `
        ${createAvatarSVG()}
        <div class="typing-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
        </div>
    `;
    chatWindow.appendChild(indicator);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return indicator;
}

// Remove typing indicator
function removeTyping(indicator) {
    if (indicator && indicator.parentNode) {
        indicator.parentNode.removeChild(indicator);
    }
}

// Build advisory refusal HTML (matches Screen 3 Stitch design)
function buildAdvisoryHtml(answer) {
    return `
        ${parseMarkdown(answer)}
        <div class="advisory-callout">
            <div class="callout-title">
                <span>ℹ️</span> Need Professional Advice?
            </div>
            For personalized investment strategies tailored to your financial goals
            and risk appetite, please consult a SEBI-registered investment advisor.
            You can find more information on <a href="https://www.amfiindia.com" target="_blank" rel="noopener noreferrer">amfiindia.com</a>.
        </div>
    `;
}

// Build PII security alert HTML (matches Screen 3 Stitch design)
function buildSecurityHtml(answer) {
    return `
        <div class="security-callout">
            <div class="callout-title">
                <span>🛡️</span> Security Alert
            </div>
            <p>For your safety, <strong>I cannot process or store personal identifiable information
            (PII)</strong> such as PAN numbers, Aadhaar details, or bank account numbers.</p>
            <p style="margin-top:8px;">The information you provided has been redacted from our system logs. Please
            do not share sensitive financial identifiers in this chat.</p>
            <div class="callout-actions">
                <button class="callout-btn" onclick="window.open('#','_blank')">View Privacy Policy</button>
                <button class="callout-btn" onclick="window.open('https://www.camsonline.com/Investors/Statements/KYC-Status','_blank')">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                    Check KYC via CAMS
                </button>
            </div>
        </div>
    `;
}

// Detect response type from backend answer text
function detectResponseType(answer) {
    if (!answer) return 'factual';
    const lower = answer.toLowerCase();
    if (lower.includes('cannot process personal') || lower.includes('pii') || lower.includes('pan') && lower.includes('safety')) {
        return 'pii';
    }
    if (lower.includes('cannot provide') && (lower.includes('investment advice') || lower.includes('recommendation'))) {
        return 'advisory';
    }
    if (lower.includes('only provide factual') || lower.includes('sebi-registered')) {
        return 'advisory';
    }
    return 'factual';
}

// Chat API Submit
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    // Add user message
    appendMessage('user', query);
    queryInput.value = '';
    sendBtn.disabled = true;

    // Show typing
    const typingIndicator = showTyping();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });

        const data = await response.json();
        removeTyping(typingIndicator);

        if (response.ok) {
            const responseType = detectResponseType(data.answer);

            let answerHtml = '';

            if (responseType === 'pii') {
                answerHtml = buildSecurityHtml(data.answer);
            } else if (responseType === 'advisory') {
                answerHtml = buildAdvisoryHtml(data.answer);
            } else {
                answerHtml = parseMarkdown(data.answer);

                // Add citation if available
                if (data.citation && data.citation.source_url) {
                    answerHtml += `
                        <div class="citation-box">
                            <a href="${data.citation.source_url}" target="_blank" rel="noopener noreferrer">
                                🔗 Source: ${data.citation.scheme_name || 'Groww'}
                            </a>
                        </div>
                    `;
                }

                // Add footer
                if (data.footer) {
                    answerHtml += `<div class="footer-text">${data.footer}</div>`;
                }
            }

            appendMessage('assistant', answerHtml, true);
        } else {
            // Handle error response (like rate limits)
            appendMessage('assistant', `⚠️ Error: ${data.detail || 'Something went wrong. Please try again later.'}`);
        }
    } catch (error) {
        removeTyping(typingIndicator);
        appendMessage('assistant', '⚠️ Network error. Please ensure the backend server is running.');
        console.error('Chat API Error:', error);
    } finally {
        sendBtn.disabled = false;
        queryInput.focus();
    }
});

// ============================================
// ADMIN SYNC
// ============================================
let syncPollInterval = null;

syncBtn.addEventListener('click', async () => {
    syncBtn.classList.add('loading');
    syncBtn.disabled = true;
    syncStatus.classList.remove('hidden', 'success', 'error');
    syncStatus.textContent = 'Syncing...';

    // Blur the chat
    chatArea.classList.add('blur-active');
    syncOverlay.classList.remove('hidden');

    // Update sync button text
    document.querySelector('.sync-label').textContent = 'Syncing...';

    try {
        const response = await fetch(`${API_BASE}/api/admin/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok) {
            // Start polling for status
            syncPollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`${API_BASE}/api/admin/sync/status`);
                    const statusData = await statusRes.json();

                    if (!statusData.is_syncing) {
                        clearInterval(syncPollInterval);
                        syncStatus.textContent = '✅ Sync completed successfully!';
                        syncStatus.classList.add('success');

                        // Unblur chat
                        chatArea.classList.remove('blur-active');
                        syncOverlay.classList.add('hidden');

                        // Reset button
                        document.querySelector('.sync-label').textContent = 'Sync Knowledge Base';
                        setTimeout(() => {
                            syncBtn.classList.remove('loading');
                            syncBtn.disabled = false;
                        }, 1000);
                    }
                } catch (e) {
                    console.error("Error polling sync status:", e);
                }
            }, 2000);
        } else {
            throw new Error(data.detail || 'Failed to trigger sync');
        }
    } catch (error) {
        syncStatus.textContent = `❌ Error: ${error.message}`;
        syncStatus.classList.add('error');
        syncBtn.classList.remove('loading');
        syncBtn.disabled = false;
        document.querySelector('.sync-label').textContent = 'Sync Knowledge Base';

        // Unblur chat on error
        chatArea.classList.remove('blur-active');
        syncOverlay.classList.add('hidden');
    }
});
