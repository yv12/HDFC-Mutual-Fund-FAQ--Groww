// Configuration
const API_BASE_URL = 'https://hdfc-mutual-fund-faq-groww-production.up.railway.app';
const SCHEMES = ["Mid Cap", "Small Cap", "Flexi Cap", "Balanced Advantage", "Top 100"];

// DOM Elements
const chatThread = document.getElementById('chat-thread');
const chatForm = document.getElementById('chat-form');
const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');
const queuedNote = document.getElementById('queued-note');
const statusPill = document.getElementById('status-pill');
const statusIcon = document.getElementById('status-icon');
const statusLabel = document.getElementById('status-label');
const progressBar = document.getElementById('progress-bar-container');
const historyList = document.getElementById('history-list');
const popularList = document.getElementById('popular-list');
const newChatBtn = document.getElementById('new-chat-btn');
const hamburgerBtn = document.getElementById('hamburger-btn');
const rightRail = document.getElementById('right-rail');
const railBackdrop = document.getElementById('rail-backdrop');

// State
let isSyncing = false;
let queuedQuestion = null;
let syncPollInterval = null;
let currentSessionId = null;
let sessions = []; // Array of session objects
let typingIndicatorElement = null;

// ==========================================
// Initialization & Storage
// ==========================================

function init() {
    loadSessions();
    if (sessions.length > 0) {
        // Load the most recent session
        loadSession(sessions[0].id);
    } else {
        startNewSession();
    }
    
    renderHistoryRail();
    renderPopular();
    
    // Initial sync check
    checkSyncStatus();
    startPolling(60000); // 60s idle
}

// Generate a simple UUID
function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function loadSessions() {
    const data = localStorage.getItem('lumina_sessions');
    if (data) {
        try {
            sessions = JSON.parse(data);
        } catch (e) {
            sessions = [];
        }
    }
}

function saveSessions() {
    localStorage.setItem('lumina_sessions', JSON.stringify(sessions));
    renderHistoryRail();
}

function startNewSession() {
    currentSessionId = uuidv4();
    renderEmptyState();
    if (window.innerWidth <= 900) {
        closeMobileRail();
    }
}

function detectSchemes(text) {
    const found = [];
    const lowerText = text.toLowerCase();
    for (const scheme of SCHEMES) {
        if (lowerText.includes(scheme.toLowerCase())) {
            found.push(scheme);
        }
    }
    return found;
}

function updateSession(query, isNew = false, appendMessageObj = null) {
    let session = sessions.find(s => s.id === currentSessionId);
    
    if (!session) {
        session = {
            id: currentSessionId,
            title: query.substring(0, 40) + (query.length > 40 ? '...' : ''),
            createdAt: new Date().toISOString(),
            messageCount: 0,
            schemes: [],
            messages: []
        };
        sessions.unshift(session);
    }
    
    if (appendMessageObj) {
        session.messages.push(appendMessageObj);
        session.messageCount++;
    }
    
    // Add any new schemes detected
    const newSchemes = detectSchemes(query);
    for (const s of newSchemes) {
        if (!session.schemes.includes(s)) {
            session.schemes.push(s);
        }
    }
    
    saveSessions();
}

// ==========================================
// Sync & Queue Logic
// ==========================================

async function checkSyncStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/admin/sync/status`);
        if (!res.ok) throw new Error('Failed to fetch status');
        const data = await res.json();
        
        const previousState = isSyncing;
        isSyncing = data.is_syncing;
        
        updateSyncUI();
        
        // Polling interval logic
        if (isSyncing) {
            startPolling(10000); // 10s while syncing
        } else {
            startPolling(60000); // 60s while idle
            
            // Auto-send queued question if it just flipped to false
            if (previousState === true && queuedQuestion) {
                const q = queuedQuestion;
                queuedQuestion = null;
                queuedNote.classList.add('hidden');
                sendBtn.textContent = 'Send';
                sendBtn.classList.remove('queue-mode');
                sendMessageToAPI(q);
            }
        }
    } catch (e) {
        console.error("Sync status check failed", e);
        setOfflineState();
    }
}

function startPolling(ms) {
    if (syncPollInterval) clearInterval(syncPollInterval);
    syncPollInterval = setInterval(checkSyncStatus, ms);
}

function updateSyncUI() {
    if (isSyncing) {
        statusPill.className = 'status-pill syncing';
        statusIcon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.27l5.43 5.43"/></svg>`;
        statusLabel.textContent = 'Syncing knowledge base';
        progressBar.classList.add('active');
        
        sendBtn.textContent = 'Queue';
        sendBtn.classList.add('queue-mode');
    } else {
        statusPill.className = 'status-pill';
        statusIcon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        statusLabel.textContent = `Synced ${new Date().toLocaleDateString()}`;
        progressBar.classList.remove('active');
        
        sendBtn.textContent = 'Send';
        sendBtn.classList.remove('queue-mode');
    }
}

function setOfflineState() {
    statusPill.className = 'status-pill offline';
    statusIcon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;
    statusLabel.textContent = 'Connection lost';
    progressBar.classList.remove('active');
}

// ==========================================
// Chat UI
// ==========================================

function renderEmptyState() {
    chatThread.innerHTML = `
        <div class="empty-state">
            <h3>Ask factual questions about 5 HDFC schemes.</h3>
            <p>Mid Cap, Small Cap, Flexi Cap, Balanced Advantage, Top 100</p>
            <p>Last updated ${new Date().toLocaleDateString()}</p>
            <div class="chips-container">
                <button class="action-chip" onclick="setQueryAndFocus('Expense ratio of HDFC Mid Cap Fund')">Expense ratio of HDFC Mid Cap Fund</button>
                <button class="action-chip" onclick="setQueryAndFocus('Minimum SIP amount')">Minimum SIP amount</button>
                <button class="action-chip" onclick="setQueryAndFocus('Exit load on early redemption')">Exit load on early redemption</button>
            </div>
        </div>
    `;
}

function setQueryAndFocus(text) {
    queryInput.value = text;
    queryInput.focus();
}

window.setQueryAndFocus = setQueryAndFocus; // Make available for inline onclick

function appendUserMessage(text) {
    // Remove empty state if present
    const emptyState = chatThread.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const msg = document.createElement('div');
    msg.className = 'message user';
    msg.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatThread.appendChild(msg);
    scrollToBottom();
}

function appendAssistantMessage(text, sourceUrl, sourceScheme) {
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    
    let footerHtml = '';
    if (sourceUrl && sourceScheme) {
        footerHtml = `
            <div class="message-footer">
                <a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener" class="source-link">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                    Source: ${escapeHtml(sourceScheme)}
                </a>
                <span>As of ${new Date().toLocaleDateString()}</span>
            </div>
        `;
    }

    msg.innerHTML = `
        <div class="message-bubble">
            ${parseMarkdown(text)}
            ${footerHtml}
        </div>
    `;
    
    // Follow up chips (hardcoded for now as per spec)
    const lowerText = text.toLowerCase();
    const chips = [];
    if (lowerText.includes('expense ratio')) chips.push('What is the exit load?');
    if (lowerText.includes('fund manager')) chips.push('What is the AUM?');
    if (chips.length === 0) chips.push('Tell me more about this scheme');
    
    const chipsDiv = document.createElement('div');
    chipsDiv.style.marginTop = '8px';
    chipsDiv.style.display = 'flex';
    chipsDiv.style.gap = '8px';
    chipsDiv.style.flexWrap = 'wrap';
    
    chips.forEach(c => {
        const btn = document.createElement('button');
        btn.className = 'action-chip';
        btn.textContent = c;
        btn.onclick = () => {
            queryInput.value = c;
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        };
        chipsDiv.appendChild(btn);
    });
    
    msg.appendChild(chipsDiv);
    
    chatThread.appendChild(msg);
    scrollToBottom();
}

function appendErrorMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message assistant error';
    msg.innerHTML = `<div class="message-bubble">${escapeHtml(text)}</div>`;
    chatThread.appendChild(msg);
    scrollToBottom();
}

function showTyping() {
    if (typingIndicatorElement) return;
    
    // Remove empty state if present
    const emptyState = chatThread.querySelector('.empty-state');
    if (emptyState) emptyState.remove();
    
    typingIndicatorElement = document.createElement('div');
    typingIndicatorElement.className = 'message assistant';
    typingIndicatorElement.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatThread.appendChild(typingIndicatorElement);
    scrollToBottom();
}

function removeTyping() {
    if (typingIndicatorElement && typingIndicatorElement.parentNode) {
        typingIndicatorElement.parentNode.removeChild(typingIndicatorElement);
    }
    typingIndicatorElement = null;
}

function scrollToBottom() {
    chatThread.scrollTop = chatThread.scrollHeight;
}

// ==========================================
// Core Chat Action
// ==========================================

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    queryInput.value = '';
    
    // Append user message immediately
    appendUserMessage(query);
    updateSession(query, false, { role: 'user', content: query });

    // Handle queueing
    if (isSyncing) {
        queuedQuestion = query;
        queuedNote.classList.remove('hidden');
        return;
    }

    // Otherwise send
    await sendMessageToAPI(query);
});

async function sendMessageToAPI(query) {
    showTyping();
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: query,
                session_id: currentSessionId
            })
        });

        const data = await response.json();
        removeTyping();

        if (response.ok) {
            appendAssistantMessage(data.answer, data.citation?.source_url, data.citation?.scheme_name);
            updateSession(query, false, { 
                role: 'assistant', 
                content: data.answer,
                source_url: data.citation?.source_url,
                scheme_name: data.citation?.scheme_name
            });
        } else {
            // Immediate check sync on failure
            checkSyncStatus();
            startPolling(10000);
            
            appendErrorMessage(data.detail || 'Something went wrong processing your request.');
        }
    } catch (error) {
        removeTyping();
        appendErrorMessage("Couldn't reach the assistant. Retrying.");
        
        // Immediate check sync on network failure
        checkSyncStatus();
        startPolling(10000);
        
        // Retry once after 3 seconds
        setTimeout(async () => {
            showTyping();
            try {
                const response = await fetch(`${API_BASE_URL}/api/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, session_id: currentSessionId })
                });
                const data = await response.json();
                removeTyping();
                if (response.ok) {
                    appendAssistantMessage(data.answer, data.citation?.source_url, data.citation?.scheme_name);
                    updateSession(query, false, { role: 'assistant', content: data.answer });
                } else {
                    appendErrorMessage(data.detail || 'Failed after retry.');
                }
            } catch (retryError) {
                removeTyping();
                appendErrorMessage("Retry failed. Please check your connection.");
            }
        }, 3000);
        
    } finally {
        sendBtn.disabled = false;
        queryInput.focus();
    }
}

// ==========================================
// Right Rail (History & Popular)
// ==========================================

function renderHistoryRail() {
    historyList.innerHTML = '';
    if (sessions.length === 0) return;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);

    const groups = { today: [], week: [], older: [] };

    sessions.forEach(s => {
        const d = new Date(s.createdAt);
        if (d >= today) groups.today.push(s);
        else if (d >= lastWeek) groups.week.push(s);
        else groups.older.push(s);
    });

    const buildGroup = (title, items) => {
        if (items.length === 0) return;
        
        const h = document.createElement('div');
        h.className = 'history-group-title';
        h.textContent = title;
        historyList.appendChild(h);

        items.forEach(item => {
            const row = document.createElement('div');
            row.className = `history-item ${item.id === currentSessionId ? 'active' : ''}`;
            row.tabIndex = 0;
            
            const timeStr = new Date(item.createdAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            const dateStr = new Date(item.createdAt).toLocaleDateString();
            const displayTime = title === 'Today' ? timeStr : dateStr;
            
            let chipsHtml = item.schemes.map(s => `<span class="scheme-chip">${escapeHtml(s)}</span>`).join('');
            
            row.innerHTML = `
                <div class="history-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title) || 'New Chat'}</div>
                <div class="history-meta">
                    <span>${item.messageCount} msgs &bull; ${displayTime}</span>
                    ${chipsHtml}
                </div>
            `;
            
            row.onclick = () => loadSession(item.id);
            row.onkeydown = (e) => { if (e.key === 'Enter') loadSession(item.id); };
            historyList.appendChild(row);
        });
    };

    buildGroup('Today', groups.today);
    buildGroup('Last 7 days', groups.week);
    buildGroup('Older', groups.older);
}

function loadSession(id) {
    const session = sessions.find(s => s.id === id);
    if (!session) return;
    
    currentSessionId = id;
    chatThread.innerHTML = '';
    
    if (session.messages.length === 0) {
        renderEmptyState();
    } else {
        session.messages.forEach(msg => {
            if (msg.role === 'user') {
                appendUserMessage(msg.content);
            } else {
                appendAssistantMessage(msg.content, msg.source_url, msg.scheme_name);
            }
        });
    }
    
    renderHistoryRail(); // update active state
    
    if (window.innerWidth <= 900) {
        closeMobileRail();
    }
}

// Popular this week stub
function fetchPopularQuestions() {
    // TODO: Connect this to a real backend endpoint later.
    return [
        { q: "What is the AUM of HDFC Mid Cap?", count: 120 },
        { q: "Exit load for Small Cap fund", count: 85 },
        { q: "Who manages Flexi Cap?", count: 64 },
        { q: "Minimum SIP for Top 100", count: 42 }
    ];
}

function renderPopular() {
    popularList.innerHTML = '';
    const items = fetchPopularQuestions();
    
    items.forEach(item => {
        const btn = document.createElement('button');
        btn.className = 'popular-item';
        btn.innerHTML = `
            <span>${escapeHtml(item.q)}</span>
            <span class="popular-count">${item.count}</span>
        `;
        btn.onclick = () => {
            queryInput.value = item.q;
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            if (window.innerWidth <= 900) closeMobileRail();
        };
        popularList.appendChild(btn);
    });
}

// ==========================================
// Events & Utilities
// ==========================================

newChatBtn.addEventListener('click', startNewSession);

hamburgerBtn.addEventListener('click', () => {
    const isOpen = rightRail.classList.contains('open');
    if (isOpen) {
        closeMobileRail();
    } else {
        rightRail.classList.add('open');
        railBackdrop.classList.add('open');
        hamburgerBtn.setAttribute('aria-expanded', 'true');
    }
});

railBackdrop.addEventListener('click', closeMobileRail);

function closeMobileRail() {
    rightRail.classList.remove('open');
    railBackdrop.classList.remove('open');
    hamburgerBtn.setAttribute('aria-expanded', 'false');
}

// Utils
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return (unsafe + '').replace(/[&<"'>]/g, function (match) {
        const escape = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return escape[match];
    });
}

function parseMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return html;
}

// Start
init();


