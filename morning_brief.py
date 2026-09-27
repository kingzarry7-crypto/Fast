#!/usr/bin/env python3
"""
CLI entry for overnight → morning signal package.
Run manually or via Railway Cron (UTC), e.g. 06:00 WAT = 05:00 UTC:

  0 5 * * *

Usage:
  python morning_brief.py
  python morning_brief.py --user-id 123
"""
import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="King Zarry morning market brief")
    parser.add_argument("--user-id", default=None, help="Optional user id for learning isolation")
    parser.add_argument("--json", action="store_true", help="Print full JSON brief")
    args = parser.parse_args()

    from agent_core import build_morning_brief, init_agent_db, agent_status

    init_agent_db()
    logging.info("Agent: %s", agent_status())
    brief = build_morning_brief(user_id=args.user_id)
    if args.json:
        print(json.dumps(brief, indent=2, default=str))
    else:
        print(brief.get("summary_text") or "")
        print("---")
        print("brief_id:", brief.get("id"))
        print("actionable:", brief.get("actionable_count"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
