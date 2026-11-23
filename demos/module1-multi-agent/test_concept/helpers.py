"""Shared helpers for the Module 1 concept tests: colour-coded stages, checks, summary."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

RESET = "\033[0m"
DIM = "\033[2m"
PASS = "\033[1;32m"
FAIL = "\033[1;31m"
# One colour per stage number: banner background, text foreground.
STAGE_BG = {
    1: "\033[1;97;44m",  # blue
    2: "\033[1;30;43m",  # yellow
    3: "\033[1;97;46m",  # cyan
    4: "\033[1;97;45m",  # magenta
    5: "\033[1;97;41m",  # red
    6: "\033[1;30;47m",  # white (summary)
}
STAGE_FG = {1: "\033[34m", 2: "\033[33m", 3: "\033[36m", 4: "\033[35m", 5: "\033[31m", 6: "\033[37m"}


class Suite:
    """Collects checks across colour-coded stages and prints a final summary."""

    def __init__(self, title: str):
        self.title = title
        self.results = []  # (stage, name, ok)
        self.stage = 1
        self.start = time.time()
        print(f"\n{STAGE_BG[6]}{'#' * 72}{RESET}")
        print(f"{STAGE_BG[6]}  CONCEPT TEST: {title:<56}{RESET}")
        print(f"{STAGE_BG[6]}{'#' * 72}{RESET}")

    def banner(self, stage: int, title: str):
        self.stage = stage
        print(f"\n{STAGE_BG[stage]}{'=' * 72}{RESET}")
        print(f"{STAGE_BG[stage]}  STAGE {stage}: {title:<62}{RESET}")
        print(f"{STAGE_BG[stage]}{'=' * 72}{RESET}")

    def info(self, msg: str):
        print(f"  {STAGE_FG[self.stage]}{msg}{RESET}")

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        ok = bool(ok)
        self.results.append((self.stage, name, ok))
        icon, color = ("✅", PASS) if ok else ("❌", FAIL)
        print(f"  {icon} {color}{name}{RESET} {DIM}{detail}{RESET}")
        return ok

    def snippet(self, text, n: int = 3):
        lines = [l for l in str(text).strip().split("\n") if l.strip()]
        for l in lines[:n]:
            print(f"    {DIM}{l[:100]}{RESET}")
        if len(lines) > n:
            print(f"    {DIM}... ({len(lines) - n} more lines){RESET}")

    def finish(self):
        self.banner(6, "SUMMARY")
        failed = [r for r in self.results if not r[2]]
        for stage, name, ok in self.results:
            icon, color = ("✅", PASS) if ok else ("❌", FAIL)
            print(f"  {icon} {STAGE_FG[stage]}[stage {stage}]{RESET} {color}{name}{RESET}")
        passed = len(self.results) - len(failed)
        print(f"\n  {DIM}{passed}/{len(self.results)} passed in {time.time() - self.start:.1f}s{RESET}")
        if failed:
            print(f"\n  {FAIL}❌ {self.title}: FAILED{RESET}\n")
            sys.exit(1)
        print(f"\n  {PASS}✅ {self.title}: PASSED{RESET}\n")
        sys.exit(0)


def silent(fn, *args, **kwargs):
    """Run fn with stdout muted (Strands streams tokens to stdout)."""
    real = sys.stdout
    sys.stdout = open(os.devnull, "w")
    try:
        return fn(*args, **kwargs)
    finally:
        sys.stdout.close()
        sys.stdout = real


def has_aws_credentials() -> bool:
    import boto3
    return boto3.Session().get_credentials() is not None


def tools_called(result) -> set:
    """Names of tools invoked during one agent call (from Strands metrics)."""
    try:
        return {n for n, m in result.metrics.tool_metrics.items() if m.call_count > 0}
    except Exception:
        return set()


def any_in(text, words) -> bool:
    t = str(text).lower()
    return any(w.lower() in t for w in words)


def run(main):
    """Entry point wrapper: graceful Ctrl+C."""
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {FAIL}Interrupted. Goodbye!{RESET}")
        sys.exit(130)
