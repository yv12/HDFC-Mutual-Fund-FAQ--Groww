"""
Query classifier module — detects small-talk, advisory, factual, and out-of-scope queries.

Uses keyword-based heuristics to route incoming user queries. Consistently
prioritizes security and compliance by routing mixed or opinion-seeking
queries to the refusal path.

Route order: small_talk → advisory → factual → out_of_scope
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ── Small-talk / meta patterns ────────────────────────────────────
# Greetings, meta questions ("what can you do"), gratitude.
# These get a friendly fixed response — no retrieval, no citation.
SMALL_TALK_PATTERNS = [
    # Greetings
    r"^\s*(?:hi|hello|hey|yo|hola|namaste|howdy|sup|hii+)\s*[!.?]*\s*$",
    r"^\s*(?:good\s+(?:morning|afternoon|evening|night|day))\s*[!.?]*\s*$",
    r"^\s*(?:what'?s?\s+up|how\s+are\s+you|how\s+do\s+you\s+do)\s*[!.?]*\s*$",
    # Meta — "what can you do", "who are you", "help"
    r"\bwhat\s+(?:can|do)\s+you\s+(?:do|help|answer|know)\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+are\s+you\b",
    r"^\s*help\s*[!.?]*\s*$",
    r"\btell\s+me\s+about\s+yourself\b",
    r"\bwhat\s+(?:is|are)\s+your\s+(?:capabilities|features|purpose)\b",
    # Gratitude
    r"^\s*(?:thanks?|thank\s+you|thx|ty|cheers|appreciated|great)\s*[!.?]*\s*$",
    r"\b(?:thanks?|thank\s+you)\s+(?:a\s+lot|so\s+much|very\s+much)\b",
    # Farewell
    r"^\s*(?:bye|goodbye|see\s+you|later|take\s+care)\s*[!.?]*\s*$",
    # Acknowledgment
    r"^\s*(?:ok|okay|got\s+it|understood|nice|cool|awesome|perfect|great|alright)\s*[!.?]*\s*$",
]

# Heuristic keywords for factual mutual fund queries
FACTUAL_KEYWORDS = [
    r"\bnav\b", r"\bnet asset value\b", r"\baum\b", r"\basset under management\b",
    r"\bfund size\b", r"\bexpense ratio\b", r"\bfees?\b", r"\bcharges?\b", r"\bcost\b",
    r"\bexit load\b", r"\bredemption charge\b", r"\bsip\b", r"\blumpsum\b",
    r"\bminimum investment\b", r"\bminimum (?:sip|lumpsum)\b", r"\binitial investment\b",
    r"\block-in\b", r"\block in\b", r"\belss\b",
    r"\btax saving\b", r"\btax saver\b", r"\briskometer\b", r"\brisk level\b",
    r"\brisk category\b", r"\brisk rating\b", r"\bbenchmark\b", r"\bindex\b",
    r"\btrack\b", r"\btracks?\b", r"\bmanagers?\b",
    r"\bmanaged by\b", r"\bfund house\b", r"\blaunch date\b", r"\binception\b",
    r"\ballotment date\b", r"\bcategory\b", r"\bsub category\b", r"\breturns?\b",
    r"\bperformance\b", r"\bdescription\b", r"\bobjectives?\b",
    r"\bwho manages\b", r"\bwho runs\b", r"\bwhat is the size\b", r"\bhow much is\b",
    r"\bminimum for sip\b", r"\brating\b", r"\bstamp duty\b", r"\btax impact\b",
    r"\btaxes?\b", r"\btell me (?:about|more)\b", r"\bhow long\b", r"\bwithdraw(?:al)?\b",
    r"\ballocation\b", r"\bportfolio\b", r"\bscheme\b", r"\bwhat is the (?:nav|aum|expense|exit|fund|scheme|minimum|benchmark|risk)\b",
    r"\bwhat are the (?:returns|charges|fees|holdings|schemes|funds)\b", r"\bfund details\b", r"\bfactsheet\b",
    r"\babout (?:hdfc|fund|scheme|mutual)\b"
]

# Heuristic keywords for advisory queries (including calculators, returns projections, and comparison requests)
# NOTE: Keep these SPECIFIC — avoid single common words (like 'best', 'invest', 'better') that also
# appear naturally in factual questions. Use multi-word phrases wherever possible.
ADVISORY_KEYWORDS = [
    # ── Suitability & Advice ──────────────────────────────────────
    r"\bshould i\b", r"\bshould we\b", r"\bought to\b", r"\brecommend\b", r"\brecommendation\b",
    r"\bshould i invest\b", r"\bshould i buy\b", r"\binvestment advice\b",
    r"\bsuggest\b", r"\bsuggestion\b", r"\bwhich fund should\b", r"\bbuy or sell\b",
    r"\badvisable\b", r"\bgood choice\b", r"\badvise me\b",
    r"\bwould you choose\b",
    r"\bis (?:this|it|that) (?:good|safe|suitable|right)\s+(?:for me|for)\b",
    r"\bsuitable for\b", r"\bgood for me\b", r"\bsafe\s*\?",
    r"\bis .* safe\b",

    # ── Comparison framed as "which is better" / fund vs fund ─────
    r"\bwhich is better\b", r"\bwhich is best\b", r"\bbetter option\b", r"\bbest fund\b",
    r"\bcompare\s+.*(?:and|vs|versus)\b",
    r"\bcompare\s+(?:the\s+)?(?:funds?|schemes?)\b",
    r"\b(?:fund|scheme)\s+comparison\b",
    r"\bcomparison\s+between\b",
    r"\bperformance\s+comparison\s+between\b",
    r"\bwhich one should\b", r"\bbetter than\b",

    # ── Future value / Return projections ─────────────────────────
    # This is the critical SEBI-compliance block. Extrapolating past returns
    # into future amounts is exactly what regulators prohibit.
    r"\bcalculat(?:e|or)\b", r"\bestimat(?:e|ed)\s+returns?\b", r"\bproject(?:ed|ions?)\s+returns?\b",
    r"\bexpect(?:ed)?\s+returns?\b", r"\bfuture\s+returns?\b",
    r"\bhow\s+much\s+(?:will\s+)?(?:i|my\s+money)\s+(?:grow|make|earn|get|gain)\b",
    r"\bhow\s+much\s+(?:can\s+(?:i|one|we)\s+)?(?:make|earn|get|gain|profit)\b",
    r"\bhow\s+much\s+(?:returns?|profit)\b",
    r"\bsip\s+calculator\b", r"\breturns?\s+calculator\b",
    r"\bwhat\s+(?:will|would)\s+.*\s+be\s+worth\b",
    r"\bwhat\s+if\s+i\s+invest\b",
    r"\bif\s+i\s+invest\b",
    r"\bwhat\s+(?:will|would|do)\s+i\s+get\b",
    r"\bhow\s+much\s+(?:will|would|can)\s+.*\s+(?:grow|become|be)\b",
    r"\b(?:₹|rs\.?|inr)\s*[\d,]+.*(?:invest|put|deposit)\b",
    r"\b(?:invest|put|deposit).*(?:₹|rs\.?|inr)\s*[\d,]+\b",

    # ── Timing ────────────────────────────────────────────────────
    r"\bshould i invest now\b", r"\bright time\b", r"\bgood time to\b",
    r"\bwhen should i\b", r"\bwhen to invest\b", r"\bwhen to buy\b",
    r"\bis (?:it|this|now) (?:a )?(?:good|right|best) time\b",

    # ── How much to invest ────────────────────────────────────────
    r"\bhow much should i invest\b", r"\bhow much to invest\b",
    r"\bhow much (?:money )?(?:do i|should i) (?:need|put|invest)\b",
]


def classify_query(query: str) -> str:
    """
    Classify a query string into a routing category:
    - 'small_talk':   greeting / meta / thanks (friendly fixed response)
    - 'advisory':     advice-seeking or projection query (refusal handler)
    - 'factual':      factual mutual fund query (RAG pipeline)
    - 'out_of_scope': unrelated query (polite redirect)

    Route order: small_talk → advisory → factual → out_of_scope
    """
    s = query.strip().lower()
    
    # 1. Check for empty queries
    if not s:
        return "out_of_scope"

    # 2. Small talk — greetings, meta, thanks (no retrieval needed)
    for pattern in SMALL_TALK_PATTERNS:
        if re.search(pattern, s):
            logger.info("Query '%s' classified as SMALL_TALK matching pattern '%s'", query, pattern)
            return "small_talk"
        
    # 3. Check for advisory keywords (mixed queries with any advisory triggers route to refusal)
    for pattern in ADVISORY_KEYWORDS:
        if re.search(pattern, s):
            logger.info("Query '%s' classified as ADVISORY matching pattern '%s'", query, pattern)
            return "advisory"
            
    # 4. Check for factual keywords
    for pattern in FACTUAL_KEYWORDS:
        if re.search(pattern, s):
            logger.info("Query '%s' classified as FACTUAL matching pattern '%s'", query, pattern)
            return "factual"
            
    # 5. Fallback to out_of_scope
    logger.info("Query '%s' classified as OUT_OF_SCOPE (no matching patterns)", query)
    return "out_of_scope"
