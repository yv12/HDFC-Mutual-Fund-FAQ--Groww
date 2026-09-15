# Mutual Fund FAQ Assistant: Product Design Specification

This document provides comprehensive product design specifications to enable the creation of high-fidelity Lumina Finance (Premium Financial Glass) mockups for the Mutual Fund FAQ Assistant.

---

## 1. PRODUCT OVERVIEW

**Product Name:** Mutual Fund FAQ Assistant
**Product Vision:** To build a trustworthy, transparent, and compliant mutual fund FAQ assistant that prioritizes accuracy over intelligence.
**Product Mission:** To ensure users receive only verified, source-backed financial information, without any advisory bias or speculative content.
**Problem Statement:** Users need objective, verifiable information about mutual funds, but AI assistants often hallucinate or provide unwarranted investment advice.
**Value Proposition:** A facts-only chatbot that retrieves data exclusively from official public sources (AMC, AMFI, SEBI via Groww) with strict citation integrity and zero hallucinated links.
**Target Audience:** Retail Investors, Customer Support / Content Teams.
**Primary Personas:** Retail Investor (Standard User), Support Agent.
**Secondary Personas:** None.
**User Goals:** Compare mutual fund schemes using verified facts, handle repetitive mutual fund queries efficiently.
**Business Goals:** Ensure 100% compliance by providing zero investment advice and accurate, strictly cited factual answers.
**Success Metrics:** Accurate retrieval, strict adherence to facts-only responses, consistent inclusion of valid source citations, proper refusal of advisory queries.
**Desktop/Mobile Requirements:** Responsive Web (Desktop and Mobile viewports).
**Internal or External Users:** External (Retail Investors) and Internal (Support Teams).
**Industry/Domain:** FinTech / Wealth Management.

---

## 2. USER PERSONAS

### Persona 1: Rahul, Retail Investor
*   **Role:** Individual Investor
*   **Responsibilities:** Researching and comparing mutual funds for personal investment.
*   **Technical Expertise:** Basic to Intermediate.
*   **Pain Points:** Finding accurate, up-to-date expense ratios, exit loads, and fund managers without sifting through long factsheets or getting biased advice.
*   **Goals:** Quick factual answers about specific HDFC funds.
*   **Daily Workflow:** Opens the chat, asks a specific question (e.g., "What is the exit load for HDFC Large Cap Fund?"), reads the short answer, and clicks the citation link.
*   **Key Tasks Performed:** Chatting, reading citations.
*   **Permissions:** Standard Chat.
*   **Expected Usage Frequency:** Occasional (few times a month).

### Persona 2: Priya, Customer Support
*   **Role:** Support Agent
*   **Responsibilities:** Answering customer queries about fund details.
*   **Technical Expertise:** Intermediate.
*   **Pain Points:** Memorizing or looking up specific metrics for various schemes.
*   **Goals:** Quickly fetch verifiable data to relay to customers.
*   **Daily Workflow:** Uses the assistant to quickly grab the expense ratio or min SIP amount for a customer.
*   **Key Tasks Performed:** Chatting, copying answers.
*   **Permissions:** Standard Chat.
*   **Expected Usage Frequency:** High (daily).

---

## 3. USER JOURNEYS

### 1. Standard User Journey (Factual Query)
*   **Entry Point:** Chat interface load.
*   **Navigation Flow:** Views welcome message & disclaimer -> Clicks one of the 3 example questions.
*   **User Decisions:** Selects "What is the expense ratio of HDFC Mid Cap Fund?"
*   **Success Path:** AI shows loading indicator -> AI replies with a short (<3 sentences) factual answer, a source link, and "Last updated from sources" footer.
*   **Exit Point:** User clicks the citation link to verify on Groww.

### 2. Standard User Journey (Advisory Query)
*   **Entry Point:** Chat interface load.
*   **Navigation Flow:** Types "Should I invest in HDFC Small Cap?"
*   **User Decisions:** Submits query.
*   **Failure Path (Refusal):** AI detects advisory intent -> Politely refuses -> Provides an educational link to AMFI/SEBI.
*   **Exit Point:** User reads refusal and clicks the educational link.

---

## 4. INFORMATION ARCHITECTURE

**Global Navigation & Structure:**
*   **Header:** App Title + HDFC Mutual Fund badge + Persistent Disclaimer Banner ("Facts-only. No investment advice.").
*   **Main Chat Area:** Welcome Message, 3 Clickable Example Questions, Scrollable Chat Window.
*   **Input Area:** Text box, Send button.
*   **Architecture:** This is a minimal, single-page application with zero complex hierarchies.

---

## 5. COMPLETE SCREEN INVENTORY

| Screen Name | Purpose | Primary Actions | Secondary Actions | Data Displayed | Allowed Roles | States |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Main Chat Interface** | Primary interaction | Send message, Click example questions | Click citation links | Chat history, Disclaimer, Welcome | All | Empty/Welcome, Loading (Typing), Error |

---

## 6. CHAT EXPERIENCE SPECIFICATION

### Input Area
*   **Prompt Box:** Single-line or small multi-line text input.
*   **Send Button:** Submits query (Enter key supported).
*   **Limitations:** No file uploads, no voice input, no slash commands. Strictly text queries.

### Conversation Experience
*   **Disclaimer Banner:** A persistent yellow/amber bar at the top: *"Facts-only. No investment advice."*
*   **Welcome Message:** Initial state shows: *"Welcome! I can answer factual questions about HDFC Mutual Fund schemes."*
*   **Example Questions:** 3 clickable cards to guide the user for a fast start:
    1. "What is the expense ratio of HDFC Mid Cap Fund?"
    2. "Who is the fund manager of HDFC Small Cap Fund?"
    3. "What is the exit load for HDFC Large Cap Fund?"
*   **Typing Indicators:** Animated dots or spinner while awaiting the backend API (< 3 seconds expected).
*   **Response Constraints:** Maximum 3 sentences per response. No conversational memory beyond the session.

---

## 7. CHAT RESPONSE ANATOMY

*   **Plain Text:** Factual answers.
*   **Citation Links:** Exactly one citation link per response. It must be extracted verbatim from the retrieved context. If no URL is present, it falls back to a text-only citation (Document name + section).
*   **Footer:** Every AI response MUST end with: `"Last updated from sources: <date>"`
*   **No Rich Media:** No tables, charts, images, or PDFs. Text and links only.
*   **Refusal Messages:** Polite refusal texts with links to AMFI/SEBI for advisory queries.
*   **PII Block Warnings:** E.g., *"For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers."*

---

## 8. CITATION SYSTEM

*   **Format:** Standard hyperlink inline or at the end of the text.
*   **Constraint:** Zero-generation policy. The LLM cannot generate links. The UI simply renders the single verified URL provided by the backend citation validator.
*   **Click Behavior:** Opens in a new tab to the exact Groww mutual fund page.

---

## 9. SOURCE EXPLORER

*(Not Applicable - The system links directly to the public Groww URLs rather than hosting a custom document viewer).*

---

## 10. RAG RETRIEVAL EXPERIENCE

*   **Loading State:** Simple animated dots while the backend performs similarity search (Qdrant Cloud) and generation (Groq API).
*   **No-result States:** If the database lacks info (e.g., Asset allocation breakdown), the AI explicitly states: *"I don't have this information in my current sources."*
*   **No complex filters:** Searching is purely semantic based on the user's query against the 5 pre-approved schemes.

---

## 11. KNOWLEDGE BASE MANAGEMENT

*   **Supported Sources:** 5 pre-approved Groww web URLs (HDFC Mid Cap, Large Cap, Small Cap, Gold ETF, Defence Fund).
*   **Operations:** Handled via the backend scraper/Playwright script.
*   *(No UI required for uploading PDFs, connecting databases, etc.)*

---

## 12. AI CAPABILITIES

*   **Core RAG:** Queries factual data about expense ratios, exit loads, SIP minimums, fund managers, AUM, riskometer, benchmarks, etc.
*   **Query Rewrite:** Normalizes aliases (e.g., "Top 100" -> Large Cap Fund).
*   **Strict Constraints:** No summarization of external docs, no recommendations, no web search beyond the indexed 5 URLs.

---

## 13. ANALYTICS & REPORTING

*(Not Applicable - Minimal scope MVP. No analytics dashboard defined in architecture).*

---

## 14. ADMIN EXPERIENCE

*(Not Applicable - Handled entirely via backend CLI/server configuration).*

---

## 15. ROLES & PERMISSIONS

*   **Standard User:** Can ask questions and view answers.

---

## 16. NOTIFICATIONS

*   **System Alerts:** Graceful error messages in the chat UI for network timeouts or API limits.

---

## 17. SEARCH EXPERIENCE

*   **Semantic Search:** Handled entirely by the backend RAG pipeline (BAAI/bge-large-en-v1.5 embeddings). No global search bar UI needed outside the chat.

---

## 18. ERROR STATES

| Scenario | Trigger | Message | Recovery Action |
| :--- | :--- | :--- | :--- |
| **PII Detected** | User types PAN/Aadhaar | "For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers." | User rephrases without PII. |
| **Advisory Query** | "Which fund is better?" | Polite refusal + AMFI/SEBI link | User asks a factual query instead. |
| **Out-of-Scope** | "What's the weather?" | Polite redirect | User asks about mutual funds. |
| **Data Missing** | "Asset allocation?" | "I don't have this information in my current sources." | None. |
| **Network Error** | API unreachable | "Unable to connect to the server. Please try again." | Retry. |

---

## 19. EMPTY STATES

*   **New Session:** Shows the Welcome Message, Disclaimer Banner, and 3 Clickable Example Questions.
*   **No Chat History:** The chat window is clear except for the welcome content.

---

## 20. LOADING STATES

*   **Chat Loading:** Animated dots/spinner in the Assistant's bubble while waiting for the response.

---

## 21. EDGE CASES

*   **Mixed Queries:** (Factual + Advisory) -> Treated as advisory and refused.
*   **Long Queries:** Handled gracefully (truncated or processed).
*   **Use of Aliases:** User asks about "Top 100" -> Automatically routed to "HDFC Large Cap" without confusing the user.

---

## 22. ACCESSIBILITY REQUIREMENTS

*   **Contrast:** Disclaimer banner (Yellow/Amber) must have readable text contrast.
*   **Keyboard Navigation:** Input box should be focusable, Enter key to send. Example questions must be accessible via Tab/Enter.

---

## 23. MOBILE EXPERIENCE

*   **Responsive Layout:** The single-page chat interface must easily adapt to a vertical mobile layout. The disclaimer banner remains sticky at the top.

---

## 24. LUMINA FINANCE DESIGN REQUIREMENTS (Premium Financial Glass)

*   **Design System:** Lumina Finance.
*   **Aesthetic:** Refined Glassmorphism with a "frosted" look, prioritizing digital clarity and absolute trust. 
*   **Colors:** Deep Navy (`#0F172A`) for primary, Slate for secondary, semi-transparent white (Glass) for surfaces over a neutral light gray background (`#F8FAFC`).
*   **Typography:** Inter font exclusively. Tight letter-spacing for headlines, tabular lining (tnum) for financial data.
*   **Layout:** 8px fluid grid rhythm. Floating glass cards with generous padding (32px - 40px).
*   **Elevation:** 3-tier elevation model (Floor, Surface Level 1, Active Level 2). Every glass card has a top-down inner white highlight and bottom-up dark stroke.
*   **Shapes:** `rounded-lg` (16px) for major containers, `rounded-md` (8px) for buttons/inputs.

---

## 25. COMPONENT INVENTORY

*   **Floating Cards (ActionCards):** Used for the Example Questions. Features 30px backdrop blur, 1px rgba border, and subtle drop shadow.
*   **InputArea:** Transparent input field with a 1px border that darkens on focus, and a subtle `rgba(15, 23, 42, 0.02)` background fill to indicate the clickable area.
*   **ChatBubble (User):** Slate text, simple design. Right-aligned.
*   **ChatBubble (Assistant):** Left-aligned on a slightly more "frosted" glass surface than the main background to highlight AI intelligence. Contains text, link, and footer.
*   **MessageBar (Disclaimer):** Clean warning styling adapted to the Lumina Glassmorphism aesthetic.
*   **Buttons:** Solid Deep Navy (`#0F172A`) with white text for primary actions. Glass-based for secondary actions.
*   **Spinner:** For loading states.

---

## 26. EXAMPLE CONVERSATIONS

**Conversation 1: Factual Query**
*   **User:** "What is the expense ratio of HDFC Mid Cap Fund?"
*   **AI Response:** "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74%. [Link to Groww] Last updated from sources: 2026-06-20."

**Conversation 2: Refusal (Advisory)**
*   **User:** "Should I invest in HDFC Large Cap?"
*   **AI Response:** "I can only provide factual information about mutual fund schemes. For investment guidance, please consult a SEBI-registered advisor or visit [amfiindia.com](https://www.amfiindia.com)."

**Conversation 3: PII Block**
*   **User:** "My PAN is ABCDE1234F, check my fund."
*   **AI Response:** "For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers."

**Conversation 4: Missing Data**
*   **User:** "What is the asset allocation breakdown for HDFC Top 100 Fund?"
*   **AI Response:** "I don't have this information in my current sources."

---

## 27. FUTURE ROADMAP

*   **Expand Scraper:** Add extraction for portfolio breakdown (equity vs debt percentages).
*   **More Funds:** Scale beyond the initial 5 HDFC funds once the Railway Free Tier allows, or upgrade hosting.

---
*End of Document.*
