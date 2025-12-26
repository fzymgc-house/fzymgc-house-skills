#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Fetch all comments from a GitHub PR using gh CLI.

Usage:
    fetch_pr_comments.py <pr_number> [repo]

Example:
    fetch_pr_comments.py 123
    fetch_pr_comments.py 123 owner/repo
"""

import json
import subprocess
import sys
from typing import Optional


def fetch_pr_comments(pr_number: str, repo: Optional[str] = None) -> dict:
    """
    Fetch all comment types from a GitHub PR.

    Returns dict with:
        - pr_info: Basic PR information (title, state, review_decision)
        - review_comments: Inline code review comments
        - issue_comments: General PR conversation comments
        - reviews: Review summaries (approve/request changes/comment)
    """

    cmd_base = ["gh", "pr", "view", pr_number]
    if repo:
        cmd_base.extend(["-R", repo])

    # Fetch PR basic info
    pr_info_cmd = cmd_base + [
        "--json", "number,title,state,reviewDecision,body,author,url,headRefName"
    ]

    pr_info_result = subprocess.run(
        pr_info_cmd,
        capture_output=True,
        text=True,
        check=True
    )
    pr_info = json.loads(pr_info_result.stdout)

    # Fetch review comments (inline code comments)
    review_comments_cmd = cmd_base + [
        "--json", "comments",
        "--jq", ".comments"
    ]

    review_comments_result = subprocess.run(
        review_comments_cmd,
        capture_output=True,
        text=True,
        check=True
    )
    review_comments = json.loads(review_comments_result.stdout)

    # Fetch reviews (approve/request changes/comment)
    reviews_cmd = cmd_base + [
        "--json", "reviews",
        "--jq", ".reviews"
    ]

    reviews_result = subprocess.run(
        reviews_cmd,
        capture_output=True,
        text=True,
        check=True
    )
    reviews = json.loads(reviews_result.stdout)

    return {
        "pr_info": pr_info,
        "review_comments": review_comments,
        "reviews": reviews
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_pr_comments.py <pr_number> [repo]", file=sys.stderr)
        sys.exit(1)

    pr_number = sys.argv[1]
    repo = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = fetch_pr_comments(pr_number, repo)
        print(json.dumps(result, indent=2))
    except subprocess.CalledProcessError as e:
        print(f"Error fetching PR comments: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
