"""CLI tool to evaluate saved coordinator response JSON files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.framework import ResearchEvaluationFramework


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate coordinator response output JSON")
    parser.add_argument("input_json", type=str, help="Path to saved response JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_json)
    payload = json.loads(input_path.read_text(encoding="utf-8"))

    result = ResearchEvaluationFramework().evaluate_response(payload)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
