# Mutual Fund FAQ Assistant — Problem Statement

## Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant answers objective, verifiable queries related to mutual funds by retrieving information exclusively from **official public sources** — such as AMC (Asset Management Company) websites, AMFI, and SEBI.

> [!IMPORTANT]
> The system must **strictly avoid** providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

---

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:

- Answers **factual queries** about mutual fund schemes
- Uses a **curated corpus** of official documents
- Provides **concise, source-backed** responses with **strict citation integrity**:
  - All hyperlinks in responses must be **extracted verbatim** from the retrieved context — the LLM must never generate, infer, or construct URLs on its own
  - **Zero-generation policy for links**: if a verified URL is not present in the retrieved context, the assistant must fall back to **text-only citations** (e.g., document name, section title, or page number)
  - This ensures **zero hallucinated links** and maintains full traceability to official sources

---

## Target Users

| User Segment | Use Case |
|---|---|
| **Retail Investors** | Comparing mutual fund schemes using verified facts |
| **Customer Support / Content Teams** | Handling repetitive mutual fund queries efficiently |

---

## Scope of Work

### 1. Corpus Definition

- **Selected AMC**: HDFC Mutual Fund
- **Corpus**: The following **5 official URLs** from Groww (serving as the reference product context):

| # | Scheme | URL |
|---|---|---|
| 1 | HDFC Mid Cap Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |
| 2 | HDFC Large Cap Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | HDFC Small Cap Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 4 | HDFC Gold ETF Fund of Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth |
| 5 | HDFC Defence Fund – Direct Growth | https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth |

---

### 2. FAQ Assistant Requirements

The assistant must answer **facts-only queries**, such as:

| Query Type | Example |
|---|---|
| Expense ratio | *"What is the expense ratio of XYZ fund?"* |
| Exit load | *"What is the exit load for ABC scheme?"* |
| Minimum SIP amount | *"What is the minimum SIP amount?"* |
| ELSS lock-in period | *"What is the lock-in period for ELSS funds?"* |
| Riskometer classification | *"What is the risk category of this fund?"* |
| Benchmark index | *"What benchmark does this fund track?"* |
| Fund management | *"Who is the fund manager of HDFC Mid Cap Fund?"* / *"What is the AUM of this fund?"* |
| Process / How-to | *"How do I download my capital gains report?"* |

**Response Constraints:**

- Each response is limited to a **maximum of 3 sentences**
- Each response includes **exactly one citation link**
- Each response includes a footer:
  > `"Last updated from sources: <date>"`

---

### 3. Refusal Handling

The assistant must **refuse** non-factual or advisory queries, such as:

- *"Should I invest in this fund?"*
- *"Which fund is better?"*

**Refusal responses should:**

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., an AMFI or SEBI resource)

---

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A **welcome message**
- **Three example questions** to guide the user
- A visible **disclaimer**:
  > *"Facts-only. No investment advice."*

---

## Constraints

### Data & Sources
- Use **only official public sources** (AMC, AMFI, SEBI)
- Do **not** use third-party blogs or aggregator websites

### Privacy & Security

> [!CAUTION]
> The system must **never** collect, store, or process:
> - PAN or Aadhaar numbers
> - Account numbers
> - OTPs
> - Email addresses or phone numbers

### Content Restrictions
- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a **link to the official factsheet only**

### Transparency
- Responses must be short, factual, and verifiable
- Every answer must include a **source link** and **last updated date**

---

## Expected Deliverables

| Deliverable | Details |
|---|---|
| **README Document** | Setup instructions, selected AMC & schemes, architecture overview (RAG approach), known limitations |
| **Disclaimer Snippet** | *"Facts-only. No investment advice."* |

---

## Success Criteria

- [x] Accurate retrieval of factual mutual fund information
- [x] Strict adherence to facts-only responses
- [x] Consistent inclusion of valid source citations
- [x] Proper refusal of advisory queries
- [x] Clean, minimal, and user-friendly interface

---

## Summary

> The goal is to build a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that prioritizes **accuracy over intelligence**. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.
