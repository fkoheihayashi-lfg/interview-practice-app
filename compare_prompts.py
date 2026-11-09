"""Run the bounded developer comparison; never retries or prints credentials."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from guards import InputError

from llm_client import (
    GenerationError,
    MAX_OUTPUT_TOKENS,
    MODEL,
    PROMPT_DIR,
    PROMPT_FILES,
    generate_questions,
)

ROOT = Path(__file__).parent
CASES = [("Python Developer", 0), ("Python Developer", 5)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Send 10 generations and up to 10 safety checks.")
    if not parser.parse_args().run:
        parser.error("Use --run only after reviewing the input cases, settings and key budget.")

    started = datetime.now(timezone.utc)
    prompts = []
    for name in PROMPT_FILES:
        content = (PROMPT_DIR / name).read_text(encoding="utf-8")
        prompts.append({"file": name, "sha256": hashlib.sha256(content.encode()).hexdigest(), "text": content})

    output_dir = ROOT / "docs" / "comparison_runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"run_{started.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    record = {
        "started_utc": started.isoformat(),
                "priority": "Realistic interview questions; preserve accepted baseline difficulty.",
        "model": MODEL,
        "temperature": "Provider default; this endpoint does not support temperature",
        "max_tokens": MAX_OUTPUT_TOKENS,
        "provider": {"only": ["anthropic"], "allow_fallbacks": False, "require_parameters": True},
        "planned_calls": len(CASES) * len(PROMPT_FILES),
        "additional_safety_checks": len(CASES) * len(PROMPT_FILES),
        "output_contract": "Strict JSON schema with local Pydantic validation",
        "sampling": "One output per prompt/input; no automatic retry; not a universal ranking.",
        "prompts": prompts,
        "results": [],
    }
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for job_title, years in CASES:
        for name in PROMPT_FILES:
            result = {"job_title": job_title, "years": years, "prompt_file": name,
                      "started_utc": datetime.now(timezone.utc).isoformat()}
            try:
                result["questions"] = generate_questions(job_title, years, prompt_file=name)
                result["status"] = "ok"
            except (GenerationError, InputError) as error:
                result["status"] = "error"
                result["error"] = str(error)
            record["results"].append(result)
            output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            print(f"{len(record['results']):02}/{record['planned_calls']} {name} years={years}: {result['status']}", flush=True)
            if result["status"] == "error":
                print(f"Stopped after error. Results saved to {output.relative_to(ROOT)}", flush=True)
                return 1
    print(f"Results saved to {output.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
