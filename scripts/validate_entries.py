"""Validate API entries in the README.md file.

Checks that each entry in the public-apis list follows the correct format,
has required fields, and meets content guidelines.
"""

import re
import sys
from pathlib import Path

# Expected table header format
TABLE_HEADER = "| API | Description | Auth | HTTPS | CORS |"
TABLE_SEPARATOR = "|---|---|---|---|---|"

# Valid values for specific columns
VALID_AUTH_VALUES = {"", "apiKey", "OAuth", "X-Mashape-Key", "No"}
VALID_HTTPS_VALUES = {"Yes", "No"}
VALID_CORS_VALUES = {"Yes", "No", "Unknown"}

# Regex to match a table row
ROW_PATTERN = re.compile(
    r"^\|\s*\[.+\]\(.+\)\s*"
    r"\|\s*.+\s*"
    r"\|\s*(apiKey|OAuth|X-Mashape-Key|No|)\s*"
    r"\|\s*(Yes|No)\s*"
    r"\|\s*(Yes|No|Unknown)\s*\|$"
)


def find_readme(base_path: Path = None) -> Path:
    """Locate the README.md file."""
    if base_path is None:
        base_path = Path(__file__).parent.parent
    readme = base_path / "README.md"
    if not readme.exists():
        raise FileNotFoundError(f"README.md not found at {readme}")
    return readme


def parse_table_rows(content: str) -> list[dict]:
    """Extract all table rows from the README content.

    Returns a list of dicts with row data and line numbers.
    """
    rows = []
    lines = content.splitlines()

    in_table = False
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("| API |"):
            in_table = True
            continue

        if in_table and stripped.startswith("|---"):
            continue

        if in_table and stripped.startswith("|") and stripped.endswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            # parts[0] is empty (before first |), parts[-1] is empty (after last |)
            parts = parts[1:-1]
            if len(parts) == 5:
                rows.append({
                    "line": line_num,
                    "raw": stripped,
                    "api": parts[0],
                    "description": parts[1],
                    "auth": parts[2],
                    "https": parts[3],
                    "cors": parts[4],
                })
        elif in_table and not stripped.startswith("|"):
            in_table = False

    return rows


def validate_row(row: dict) -> list[str]:
    """Validate a single table row.

    Returns a list of error messages (empty if valid).
    """
    errors = []
    line = row["line"]

    # Check API name is a markdown link
    if not re.match(r"^\[.+\]\(https?://.+\)$", row["api"]):
        errors.append(f"Line {line}: API name must be a markdown link with https/http URL")

    # Check description is not empty and not too long
    if not row["description"]:
        errors.append(f"Line {line}: Description cannot be empty")
    elif len(row["description"]) > 100:
        errors.append(f"Line {line}: Description too long ({len(row['description'])} chars, max 100)")

    # Check description starts with capital letter
    if row["description"] and not row["description"][0].isupper():
        errors.append(f"Line {line}: Description should start with a capital letter")

    # Validate Auth field
    if row["auth"] not in VALID_AUTH_VALUES:
        errors.append(
            f"Line {line}: Invalid Auth value '{row['auth']}'. "
            f"Must be one of: {', '.join(repr(v) for v in VALID_AUTH_VALUES)}"
        )

    # Validate HTTPS field
    if row["https"] not in VALID_HTTPS_VALUES:
        errors.append(
            f"Line {line}: Invalid HTTPS value '{row['https']}'. Must be 'Yes' or 'No'"
        )

    # Validate CORS field
    if row["cors"] not in VALID_CORS_VALUES:
        errors.append(
            f"Line {line}: Invalid CORS value '{row['cors']}'. "
            f"Must be one of: {', '.join(VALID_CORS_VALUES)}"
        )

    return errors


def validate_entries(readme_path: Path = None) -> bool:
    """Run all entry validations against the README.

    Returns True if all entries are valid, False otherwise.
    """
    readme = find_readme(readme_path)
    content = readme.read_text(encoding="utf-8")

    rows = parse_table_rows(content)
    if not rows:
        print("WARNING: No table rows found in README.md")
        return True

    print(f"Validating {len(rows)} entries...")

    all_errors = []
    for row in rows:
        errors = validate_row(row)
        all_errors.extend(errors)

    if all_errors:
        print(f"\nFound {len(all_errors)} error(s):")
        for error in all_errors:
            print(f"  - {error}")
        return False

    print("All entries are valid!")
    return True


if __name__ == "__main__":
    success = validate_entries()
    sys.exit(0 if success else 1)
