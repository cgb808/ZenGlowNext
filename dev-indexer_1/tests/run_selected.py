"""Manual test runner workaround when pytest global collection is empty.

Executes a curated subset of important tests programmatically so CI can still
exercise critical functionality until root cause of empty collection is fixed.
"""
import subprocess, sys

FILES = [
    "tests/test_metrics_facade.py",
    "tests/test_transcription_jobs.py",
]

def main():
    failures = 0
    for f in FILES:
        print(f"\n=== Running {f} ===", flush=True)
        r = subprocess.run([sys.executable, "-m", "pytest", f, "-q"], text=True)
        if r.returncode != 0:
            failures += 1
    if failures:
        print(f"Failures: {failures}")
        sys.exit(1)
    print("All selected tests passed.")

if __name__ == "__main__":
    main()
