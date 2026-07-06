#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


def main() -> None:
    payload = json.loads(sys.stdin.read())
    sermon = payload["sermon"]
    print(
        json.dumps(
            {
                "summary": f"{sermon['title']} calls the church to review courage and faithfulness.",
                "themes": ["Courage", "Faithfulness"],
                "topics": ["Discipleship"],
                "related_sermons": [],
                "questionable_claims": ["Summary came from the example command and needs pastoral review."],
            }
        )
    )


if __name__ == "__main__":
    main()
