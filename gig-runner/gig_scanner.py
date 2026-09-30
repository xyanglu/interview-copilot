#!/usr/bin/env python3
"""
Gig Work Scanner — Fetches contract/remote AI/ML gigs from We Work Remotely.
Designed to be run by Hermes cron. Surfaces only worthwhile matches.
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import re

RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
SEEN_FILE = Path(os.environ.get("GIG_SEEN_FILE", str(Path.home() / ".hermes" / "seen_gigs.json")))

# Keywords that signal a good fit
GOOD_KEYWORDS = [
    "ai", "machine learning", "ml", "llm", "rag", "langchain",
    "python", "fastapi", "agent", "gpt", "openai", "claude",
    "full-stack", "full stack", "backend", "back-end",
    "typescript", "react", "node",
]

# Keywords that signal a bad fit (skip these)
BAD_KEYWORDS = [
    "senior staff", "principal", "director", "vp", "chief",
    "blockchain", "solidity", "crypto",
    "c++", "c#", ".net", "java", "embedded", "firmware",
    "devops manager", "engineering manager",
    "sales", "marketing", "recruiter", "product manager",
    "5+ years", "7+ years", "10+ years", "15+ years",
    "customer support", "customer service", "customer success",
    "support representative", "support executive",
]

def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text())
    return []

def save_seen(ids):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(ids))

def fetch_feed():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()

def parse_feed(xml_data):
    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        desc = item.findtext("description", "")
        link = item.findtext("link", "") or item.findtext("guid", "")
        pub_date = item.findtext("pubDate", "")
        region = item.findtext("region", "")
        
        items.append({
            "title": title.strip(),
            "description": desc.strip(),
            "url": link.strip(),
            "date": pub_date.strip(),
            "region": region.strip(),
        })
    return items

def score_gig(gig):
    """Score a gig based on relevance to user's profile. Returns (score, reasons)."""
    text = (gig["title"] + " " + gig["description"]).lower()
    score = 0
    reasons = []

    # Bad keyword check - if any match, score goes negative
    for kw in BAD_KEYWORDS:
        if kw in text:
            return -100, [f"Bad keyword: {kw}"]

    # Good keyword scoring
    for kw in GOOD_KEYWORDS:
        count = text.count(kw)
        if count > 0:
            score += count * 2
            if kw not in [r.split(":")[0] for r in reasons]:
                reasons.append(kw)

    # Title match is worth more
    title_lower = gig["title"].lower()
    for kw in GOOD_KEYWORDS:
        if kw in title_lower:
            score += 5

    # Penalize very senior roles
    for pat in ["staff", "principal", "director"]:
        if pat in title_lower:
            score -= 20

    return score, reasons

def format_gig(gig, score, reasons):
    """Format a gig for display."""
    title = gig["title"][:120]
    region = gig["region"] or "Remote"
    return {
        "title": title,
        "company": gig.get("company", ""),
        "region": region,
        "url": gig["url"],
        "score": score,
        "reasons": reasons[:5],
    }

def main():
    seen = set(load_seen())
    
    print("🔍 Scanning We Work Remotely for AI/ML gigs...\n")
    
    try:
        xml_data = fetch_feed()
    except Exception as e:
        print(f"Error fetching feed: {e}")
        return
    
    items = parse_feed(xml_data)
    
    # Score and filter
    scored = []
    for item in items:
        gig_id = item["url"]
        if gig_id in seen:
            continue
        
        score, reasons = score_gig(item)
        if score >= 5:  # Minimum threshold
            scored.append((score, item, reasons))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Mark ALL feed items as seen (even low-scoring ones, to avoid re-processing)
    new_seen = seen | {item["url"] for item in items}
    save_seen(list(new_seen))
    
    if not scored:
        print("No worthwhile new gigs found.\n")
        return
    
    print(f"Found {len(scored)} worthwhile gig{'s' if len(scored) != 1 else ''}:\n")
    
    for i, (score, item, reasons) in enumerate(scored[:10], 1):
        print(f"{'='*60}")
        print(f"{i}. {item['title']}")
        print(f"   Region: {item.get('region', 'Anywhere')}")
        print(f"   Score: {score}/100 — {', '.join(reasons[:4])}")
        print(f"   {item['url']}")
        print()
    
    # Also output structured JSON for cron delivery
    result = []
    for score, item, reasons in scored[:10]:
        result.append(format_gig(item, score, reasons))
    
    print("---JSON_START---")
    print(json.dumps(result, indent=2))
    print("---JSON_END---")

if __name__ == "__main__":
    main()
