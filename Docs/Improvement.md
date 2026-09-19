Four separate bugs here. Quick read on each:

1. Greeting hits the guardrail
Your classifier has only two buckets: fund question, or refuse. Add a third — small talk / meta ("hi", "what can you do", "thanks") — and answer it with a fixed friendly line, no retrieval, no citation, no AMFI disclaimer. Route order: small talk → advice → fund question → out of scope.

2. Empty answer, just the follow-up chip
When you asked "Tell me more about this scheme", the answer body came back blank and only the chip rendered. Two likely causes: the query has no subject ("this scheme") so retrieval returned nothing, and your code still renders the card instead of falling back. Fix both:

Carry the last fund name in session state and rewrite pronouns before embedding: "this scheme" → "HDFC Mid Cap Fund".
If retrieval confidence is below threshold or the LLM returns empty, show "I could not find that in my sources" instead of a blank card.

3. The chip repeats on every reply
It is hardcoded after each message. Make it conditional: only show when a fund was actually identified in the answer, and not when the last reply was a refusal or the user already asked for details on that fund. Also make it specific — "Tell me more about HDFC Mid Cap" — otherwise it reads as filler.

4. Guardrail is inconsistent, and it is inconsistent in the wrong direction
"How much should I invest" got refused. Good. But "how much can I make from ₹1,00,000" got answered with a projection. That one is worse. You extrapolated a past 1-year return into a future amount, which is exactly what SEBI rules prohibit and what the AMFI disclaimer exists to prevent.

Add these to the refusal class:

future value / return projections ("how much will I make", "what if I invest X")
suitability ("should I", "is this good for me", "safe?")
comparisons framed as which is better
timing ("should I invest now")

Allowed: stated facts from your sources — AUM, NAV, expense ratio, past returns as historical numbers, holdings, exit load, fund manager.

Rule of thumb for the classifier prompt: if answering requires a number that does not exist in the source document, refuse.

Bonus, for the twisted-question problem
Before embedding, run a cheap rewrite step: resolve pronouns from history, expand abbreviations, normalise to a plain question. Then do hybrid search (keyword + vector) rather than vector alone. Fund names and metric words like "AUM" are exact-match terms and pure semantic search handles them badly.

For your portfolio write-up, this is the strongest part of the story: you caught that the chatbot was giving a return projection and closed it. That is a real product safety decision, not just a bug fix.