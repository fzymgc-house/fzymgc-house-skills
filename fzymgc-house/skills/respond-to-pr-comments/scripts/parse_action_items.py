#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Parse PR comments and extract prioritized action items.

Usage:
    parse_action_items.py <pr_comments_json>

Input: JSON from fetch_pr_comments.py (via stdin or file)
Output: Structured action items with severity classification
"""

import json
import re
import sys
from collections import defaultdict
from typing import List, Dict, Any


# Severity keyword patterns (ordered by priority)
SEVERITY_PATTERNS = {
    "blocking": [
        r"\bblocking\b",
        r"\bblocker\b",
        r"\bmust\s+fix\b",
        r"\brequired\b",
        r"\bcritical\b",
        r"\bsecurity\b",
        r"\bvulnerability\b",
        r"\bbreaking\b",
    ],
    "important": [
        r"\bimportant\b",
        r"\bshould\s+fix\b",
        r"\bneeds?\s+to\b",
        r"\bplease\s+fix\b",
        r"\bissue\b",
        r"\bbug\b",
        r"\bproblem\b",
        r"\bincorrect\b",
    ],
    "suggestion": [
        r"\bnit\b",
        r"\bminor\b",
        r"\bsuggestion\b",
        r"\bconsider\b",
        r"\bmaybe\b",
        r"\boptional\b",
        r"\bcould\b",
        r"\bmight\s+want\b",
    ]
}


def classify_severity(text: str, review_state: str = None) -> str:
    """
    Classify comment severity based on keywords and review state.

    Priority levels: blocking > important > suggestion > comment
    """
    text_lower = text.lower()

    # Check for explicit severity keywords
    for severity, patterns in SEVERITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return severity

    # Use review state as fallback
    if review_state == "CHANGES_REQUESTED":
        return "important"
    elif review_state == "APPROVED":
        return "comment"

    # Default to suggestion if unclear
    return "suggestion"


def extract_code_reference(comment: Dict[str, Any]) -> Dict[str, str]:
    """Extract file path and line information from review comment."""
    ref = {}

    if "path" in comment:
        ref["file"] = comment["path"]

    if "line" in comment and comment["line"]:
        ref["line"] = comment["line"]
    elif "position" in comment and comment["position"]:
        ref["line"] = f"~{comment['position']}"

    if "diffHunk" in comment:
        ref["context"] = comment["diffHunk"]

    # Include comment ID for reactions
    if "id" in comment:
        ref["comment_id"] = comment["id"]

    return ref


def parse_action_items(pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse PR comments into prioritized action items.

    Returns dict with:
        - summary: High-level PR info
        - action_items: List of items grouped by severity
        - stats: Summary statistics
    """
    action_items = []
    pr_info = pr_data["pr_info"]

    # Process review comments (inline code comments)
    for comment in pr_data.get("review_comments", []):
        if not comment.get("body"):
            continue

        item = {
            "type": "review_comment",
            "author": comment.get("author", {}).get("login", "unknown"),
            "body": comment["body"],
            "created_at": comment.get("createdAt"),
            "url": comment.get("url"),
            "code_ref": extract_code_reference(comment),
            "severity": classify_severity(comment["body"])
        }
        action_items.append(item)

    # Process reviews (approve/request changes/comment)
    for review in pr_data.get("reviews", []):
        if not review.get("body"):
            continue

        item = {
            "type": "review",
            "author": review.get("author", {}).get("login", "unknown"),
            "body": review["body"],
            "state": review.get("state"),
            "created_at": review.get("submittedAt"),
            "url": review.get("url"),
            "review_id": review.get("id"),  # Include review ID for reactions
            "severity": classify_severity(review["body"], review.get("state"))
        }
        action_items.append(item)

    # Sort by severity priority
    severity_order = {"blocking": 0, "important": 1, "suggestion": 2, "comment": 3}
    action_items.sort(key=lambda x: severity_order.get(x["severity"], 99))

    # Calculate stats
    severity_counts = defaultdict(int)
    for item in action_items:
        severity_counts[item["severity"]] += 1

    return {
        "summary": {
            "pr_number": pr_info.get("number"),
            "title": pr_info.get("title"),
            "state": pr_info.get("state"),
            "review_decision": pr_info.get("reviewDecision"),
            "branch": pr_info.get("headRefName"),
            "url": pr_info.get("url")
        },
        "action_items": action_items,
        "stats": {
            "total_items": len(action_items),
            "by_severity": dict(severity_counts)
        }
    }


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            pr_data = json.load(f)
    else:
        pr_data = json.load(sys.stdin)

    result = parse_action_items(pr_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
