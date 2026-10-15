"""Run the published fixed inputs; import has no effects."""
from pathlib import Path
import json
from affine_exact import fixed_report


if __name__ == "__main__":
    inputs = Path(__file__).with_name("fixed-inputs.json")
    print(json.dumps(fixed_report(json.loads(inputs.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2))
