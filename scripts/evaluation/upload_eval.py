"""Upload eval results to the shared `roboarena-sim` S3 bucket.

Credentials are read from the environment so they can be handed out without
baking anything into the repo. Set these before running:

    export ROBOARENA_ACCESS_KEY_ID=...      # the access key you were given
    export ROBOARENA_SECRET_ACCESS_KEY=...  # the matching secret

Then point it at a file or directory of eval results:

    python scripts/evaluation/upload_eval.py path/to/eval_output
    python scripts/evaluation/upload_eval.py results.json

The eval output already has a self-describing layout
(institution/task_id/policy_name/timestamp/), so it is mirrored as-is at the
bucket root. Point this at the eval output directory and that whole tree is
uploaded unchanged.
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BUCKET = "roboarena-sim"
REGION = "us-west-2"


def _require_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        sys.exit(
            f"Missing required environment variable: {var}\n"
            "See the docstring at the top of this script for setup."
        )
    return val


def _make_client():
    return boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=_require_env("ROBOARENA_ACCESS_KEY_ID"),
        aws_secret_access_key=_require_env("ROBOARENA_SECRET_ACCESS_KEY"),
        # Optional: only set if you were given temporary (STS) credentials.
        aws_session_token=os.environ.get("ROBOARENA_SESSION_TOKEN"),
    )


def _iter_files(path: Path):
    """Yield (local_file, relative_key) pairs for a file or directory."""
    if path.is_file():
        yield path, path.name
    elif path.is_dir():
        for f in sorted(path.rglob("*")):
            if f.is_file():
                yield f, f.relative_to(path).as_posix()
    else:
        sys.exit(f"Path does not exist: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload eval results to the roboarena-sim bucket.")
    parser.add_argument("path", type=Path, help="File or directory of eval results to upload.")
    args = parser.parse_args()

    client = _make_client()
    files = list(_iter_files(args.path))
    if not files:
        sys.exit(f"No files found to upload under: {args.path}")

    print(f"Uploading {len(files)} file(s) to s3://{BUCKET}/")
    try:
        for local_file, rel_key in files:
            client.upload_file(str(local_file), BUCKET, rel_key)
            print(f"  ✓ {rel_key}")
    except (BotoCoreError, ClientError) as e:
        sys.exit(f"Upload failed: {e}")

    print(f"Done. Uploaded {len(files)} file(s) to s3://{BUCKET}/")


if __name__ == "__main__":
    main()
