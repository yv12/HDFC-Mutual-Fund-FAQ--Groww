"""
Query classifier module — detects factual, advisory, and out-of-scope queries.

Uses keyword-based heuristics to route incoming user queries. Consistently
prioritizes security and compliance by routing mixed or opinion-seeking
queries to the refusal path.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

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
    r"\bperformance\b", r"\babout\b", r"\bdescription\b", r"\bobjectives?\b",
    r"\bwho manages\b", r"\bwho runs\b", r"\bwhat is the size\b", r"\bhow much is\b",
    r"\bminimum for sip\b", r"\brating\b", r"\bstamp duty\b", r"\btax impact\b",
    r"\btaxes?\b", r"\btell me\b", r"\bhow long\b", r"\bwithdraw(?:al)?\b",
    r"\ballocation\b", r"\bportfolio\b", r"\bscheme\b", r"\bwhat is the\b",
    r"\bwhat are the\b", r"\bfund details\b", r"\bfactsheet\b"
]

# Heuristic keywords for advisory queries (including calculators, returns projections, and comparison requests)
# NOTE: Keep these SPECIFIC — avoid single common words (like 'best', 'invest', 'better') that also
# appear naturally in factual questions. Use multi-word phrases wherever possible.
ADVISORY_KEYWORDS = [
    r"\bshould i\b", r"\bshould we\b", r"\bought to\b", r"\brecommend\b", r"\brecommendation\b",
    r"\bwhich is better\b", r"\bwhich is best\b", r"\bbetter option\b", r"\bbest fund\b",
    r"\bshould i invest\b", r"\bshould i buy\b", r"\binvestment advice\b",
    r"\bsuggest\b", r"\bsuggestion\b", r"\bwhich fund should\b", r"\bbuy or sell\b",
    r"\bcompare\b", r"\bcomparison\b", r"\badvisable\b", r"\bgood choice\b", r"\badvise me\b",
    r"\bwould you choose\b", r"\bperformance comparison\b",
    r"\bcalculat(?:e|or)\b", r"\bestimat(?:e|ed)\s+returns?\b", r"\bproject(?:ed|ions?)\s+returns?\b",
    r"\bexpect(?:ed)?\s+returns?\b", r"\bfuture\s+returns?\b",
    r"\bhow\s+much\s+(?:will\s+)?my\s+money\s+(?:grow|be)\b", r"\bhow\s+much\s+(?:returns?|profit)\b",
    r"\bsip\s+calculator\b", r"\breturns?\s+calculator\b"
]


def classify_query(query: str) -> str:
    """
    Classify a query string into a routing category:
    - 'advisory': mixed or advice-seeking query (refusal handler routes this)
    - 'factual': factual mutual fund schema query (RAG pipeline routes this)
    - 'out_of_scope': unrelated query (polite redirect routes this)
    """
    s = query.strip().lower()
    
    # 1. Check for empty queries
    if not s:
        return "out_of_scope"
        
    # 2. Check for advisory keywords (mixed queries with any advisory triggers route to refusal)
    for pattern in ADVISORY_KEYWORDS:
        if re.search(pattern, s):
            logger.info("Query '%s' classified as ADVISORY matching pattern '%s'", query, pattern)
            return "advisory"
            
    # 3. Check for factual keywords
    for pattern in FACTUAL_KEYWORDS:
        if re.search(pattern, s):
            logger.info("Query '%s' classified as FACTUAL matching pattern '%s'", query, pattern)
            return "factual"
            
    # 4. Fallback to out_of_scope
    logger.info("Query '%s' classified as OUT_OF_SCOPE (no matching patterns)", query)
    return "out_of_scope"
