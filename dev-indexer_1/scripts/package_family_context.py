"""Package Family context + dataset generator into a portable tarball.

Features:
 - Deterministic file list (see FILES list)
 - SHA256 manifest (family_package_manifest.json)
 - Optional verification mode against existing manifest

Usage:
  python scripts/package_family_context.py --out dist            # create tarball
  python scripts/package_family_context.py --verify family_package_manifest.json  # verify
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, tarfile, time, sys
from typing import List, Dict

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Curated file set (relative to repo root)
FILES: List[str] = [
    # Domain / API
    "app/family/context.py",
    "app/family/router.py",
    "app/family/repo.py",
    "app/family/pg_repo.py",
    "app/family/seed_data.json",
    # Persistence / security
    "sql/family_schema.sql",
    "sql/family_rls.sql",
    # Dataset generation
    "scripts/export_family_finetune_dataset.py",
    "scripts/export_family_conversations.py",
    "scripts/build_family_dataset.py",
    # Packaging script itself (self-describing)
    "scripts/package_family_context.py",
    # Docs
    "docs/DATASET_EXPORT.md",
    "docs/FAMILY_CONTEXT_DESIGN.md",
    "docs/FAMILY_REMOTE_TRANSFER.md",
    # Tests
    "tests/test_conversation_generators.py",
]


def sha256_path(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def build_manifest() -> Dict[str, Dict[str, str]]:
    manifest: Dict[str, Dict[str, str]] = {}
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():  # skip missing (defensive)
            continue
        manifest[rel] = {"sha256": sha256_path(path)}
    return manifest


def create_tar(out_dir: pathlib.Path) -> pathlib.Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    top = {
        "created_ts": int(time.time()),
        "files": manifest,
        "count": len(manifest),
        "root": str(ROOT.name),
        "description": "Family context + dataset generator package",
    }
    manifest_path = ROOT / 'family_package_manifest.json'
    manifest_path.write_text(json.dumps(top, indent=2), encoding='utf-8')

    ts = time.strftime('%Y%m%d_%H%M%S')
    tar_name = f"family_package_{ts}.tar.gz"
    tar_path = out_dir / tar_name
    with tarfile.open(tar_path, 'w:gz') as tar:
        # add manifest first
        tar.add(manifest_path, arcname='family_package_manifest.json')
        for rel in manifest.keys():
            tar.add(ROOT / rel, arcname=rel)
    return tar_path


def verify(manifest_file: pathlib.Path) -> int:
    data = json.loads(manifest_file.read_text())
    failures = []
    for rel, meta in data.get('files', {}).items():
        path = ROOT / rel
        if not path.exists():
            failures.append(f"MISSING:{rel}")
            continue
        actual = sha256_path(path)
        if actual != meta.get('sha256'):
            failures.append(f"HASH_MISMATCH:{rel}")
    if failures:
        print(json.dumps({"status": "FAIL", "failures": failures}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "OK", "files": len(data.get('files', {}))}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='dist', help='output directory for tarball')
    ap.add_argument('--verify', help='path to existing family_package_manifest.json to verify current workspace')
    args = ap.parse_args()

    if args.verify:
        return verify(pathlib.Path(args.verify))

    tar_path = create_tar(pathlib.Path(args.out))
    print(json.dumps({"package": str(tar_path)}))
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
