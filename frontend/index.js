const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const chatWindow = document.getElementById('chat-window');
const sendBtn = document.getElementById('send-btn');
const chatArea = document.getElementById('chat-area');
const syncOverlay = document.getElementById('sync-overlay');

// ============================================
// CONFIGURATION
// ============================================
// Replace this with your actual Railway backend URL
// Example: const API_BASE_URL = 'https://hdfc-mutual-fund-faq--groww.up.railway.app';
// If it's an empty string '', it uses the current domain.
const API_BASE_URL = 'https://hdfc-mutual-fund-faq-groww-production.up.railway.app';

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
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
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


