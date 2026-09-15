# Antigravity build prompt

Paste everything below the line into Antigravity with Gemini Pro (High).

---

You are rebuilding the frontend of an existing RAG chatbot called "Lumina Finance", a facts-only FAQ assistant for 5 HDFC mutual fund schemes. The backend already exists and is deployed. Do not change or mock the backend. Build the frontend only.

## Stack rules

- Vanilla HTML, CSS, and JavaScript. No React, no Tailwind, no build step, no npm.
- Exactly three files: `index.html`, `index.css`, `index.js`.
- No external dependencies except the Inter font from Google Fonts.
- All colours as CSS custom properties in `:root`.

## Backend contract

Base URL: `https://hdfc-mutual-fund-faq-groww-production.up.railway.app`

- `POST /api/chat` with body `{ "query": "..." }`. Returns `{ "answer": "..." }` on success, or a non-200 with `{ "detail": "..." }`. It returns an error while a sync is running.
- `GET /api/admin/sync/status` returns `{ "is_syncing": true|false }`.

There is no endpoint for popular questions yet. Stub it behind a single function named `fetchPopularQuestions()` that currently returns hardcoded data, with a comment marking where the real fetch goes.

## Hard layout constraint

The entire app fits in one viewport. The page itself never scrolls.

- `html, body { height: 100dvh; overflow: hidden; }`. Use `dvh`, never `vh`.
- Only two elements scroll internally: the chat thread and the chat history list. Both use `overflow-y: auto`.
- Desktop layout is a CSS grid: fixed 56px header across the top, then two columns below it. Left column is the chat, right column is a 320px rail. Left column is `1fr`, rail is fixed width.
- Left column is a flex column: chat thread takes `flex: 1` and scrolls, input area is fixed at the bottom and never scrolls away.
- Right rail splits into two boxes: "Your chats" on top taking the remaining space and scrolling, "Popular this week" below it at a fixed height showing exactly 4 items.
- Below 900px viewport width, hide the right rail behind a hamburger icon in the header that slides it over as an overlay. Chat takes full width.

## Theme

Dark, near-black with green as the single accent.

```
--bg-page:    #0C110E
--bg-card:    #141B17
--border:     #253029
--text:       #E9EFEB
--text-muted: #8D9C93
--accent:     #2E9E6B
--accent-bg:  #16281E
--accent-text:#4FCF8B
--warning:    #C98A2B
--warning-bg: #2A2113
--danger:     #C25450
--danger-bg:  #2A1615
```

Critical rule: green never appears on a number or a data value. All figures render in `--text`. Green is only for the status pill, the send button, focus rings, and links. Green on a percentage reads as investment advice, which this product must avoid.

Body text 14px, line-height 1.7. Metadata 12px. Nothing below 11px. Font weights 400 and 500 only.

## Components

### Header (56px, fixed)

Left: "Lumina Finance" at 14px weight 500. Right: a status pill plus an info icon.

Status pill has three states driven by one variable:
- Idle: green background `--accent-bg`, text `--accent-text`, check icon, label "Synced <date>"
- Syncing: amber, spinning refresh icon, label "Syncing knowledge base"
- Offline: red, label "Connection lost"

The info icon opens a small tooltip on hover and click containing: "Facts only, no investment advice. Answers come from published scheme pages."

Under the header, a 3px progress bar that is only visible while syncing. Animate it as an indeterminate sliding bar.

### Empty state

Shown when the thread has no messages. Centred in the chat pane:
- One line: "Ask factual questions about 5 HDFC schemes."
- A muted line listing coverage: "Mid Cap, Small Cap, Flexi Cap, Balanced Advantage, Top 100"
- A muted line: "Last updated <date from sync status>"
- Three starter chips that fill the input on click: "Expense ratio of HDFC Mid Cap Fund", "Minimum SIP amount", "Exit load on early redemption"

### User message

Right aligned, background `--accent-bg`, text `--accent-text`, 12px radius, max-width 75%.

### Assistant answer card

Left aligned, background `--bg-card`, 12px radius, padding 14px, max-width 85%. Contains:
- The answer text
- A footer row with a source chip (link icon plus source label) and an "As of <date>" stamp in `--text-muted`

Below each assistant answer, render 2 to 3 follow-up chips as small outlined buttons that send that question on click. For now derive them from a simple keyword map in JS, with a comment noting they should later come from the backend.

### Input area (fixed)

Text input plus a button. Button label and behaviour change with sync state:
- Idle: "Send", posts to `/api/chat`
- Syncing: "Queue", stores the question and does not post

### Sync and queue behaviour

This is the most important interaction. Get it right.

1. On page load, call `/api/admin/sync/status` and set the pill.
2. Poll every 10 seconds while syncing, every 60 seconds while idle.
3. If any `/api/chat` call fails, immediately check sync status once and start fast polling.
4. When the user submits while syncing, do not send. Store the question, show it as a user message in the thread, and append an inline note styled with `--warning-bg` and a left border in `--warning`: "Queued. This sends automatically when the sync finishes." Only one question can be queued at a time. A second submission replaces the first and updates the note.
5. When polling flips `is_syncing` from true to false, automatically send the queued question, remove the note, and show the typing indicator.
6. Never disable the input. The user should always be able to type.

### Typing indicator

Three dots animating while awaiting a response. Remove it before appending the answer.

### Chat history (right rail)

Persist to `localStorage` under key `lumina_sessions`. Schema per session:

```json
{
  "id": "uuid",
  "title": "first 40 chars of the first question",
  "createdAt": "ISO string",
  "messageCount": 4,
  "schemes": ["Mid Cap"],
  "messages": []
}
```

Detect scheme names in questions with a simple string match against the 5 known scheme names to populate `schemes`.

Render grouped by "Today", "Last 7 days", "Older". Each row shows the title on one line, then a metadata line with message count, time for today's items or date for older ones, and a small chip per detected scheme. The active session row has a `--bg-card` background. Clicking a row loads that thread. A "New chat" button sits in the rail header.

### Popular this week (right rail, fixed height)

Exactly 4 rows, each a question on the left and an ask count on the right in `--text-muted`, separated by hairline borders. Clicking a row sends that question. Data comes from `fetchPopularQuestions()`.

## Error handling

- Non-200 from `/api/chat`: show an assistant-styled card with a red left border and the `detail` message. No emoji, no "Error:" prefix.
- Network failure: "Couldn't reach the assistant. Retrying." Then retry once after 3 seconds.
- Never leave a typing indicator on screen after a failure.

## Known bug in the current code

The existing `index.js` assigns the typing indicator to a variable named `typingIndicator` but then references an undefined `indicator` when removing it, which throws and pushes every message into the network error branch. Do not reproduce this.

## Accessibility

- The chat thread is `role="log"` with `aria-live="polite"`.
- The status pill has an `aria-label` describing the current state.
- Icon-only buttons have `aria-label`.
- Visible focus rings in `--accent` on all interactive elements.
- Contrast of `--text-muted` on `--bg-page` must pass WCAG AA at 12px.

## Do not

- Do not scroll the body.
- Do not use `100vh`.
- Do not use pure `#000` or pure `#fff`.
- Do not use gradients, glassmorphism, blur, or drop shadows.
- Do not use emoji anywhere.
- Do not use Title Case. Sentence case everywhere.
- Do not colour any number green.
- Do not add a features that require backend changes, such as scheme comparison tables or change detection.

## Deliverable

The three files, complete and runnable by opening `index.html` directly. Include brief comments only where the sync and queue logic is non-obvious.