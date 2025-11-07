#!/usr/bin/env python3
"""
ping_scan.py

Usage:
    python ping_scan.py input_hosts.txt
    python ping_scan.py input_hosts.txt --mode thread --concurrency 200 --timeout 2

Reads hostnames or IP addresses (one per line) from the given text file and pings them concurrently.
Outputs:
    - online.txt   (hosts that responded)
    - offline.txt  (hosts that did not)
    - report.txt   (combined summary)

Two modes:
    - async  (default): uses asyncio + async subprocesses (fast, non-blocking)
    - thread : uses ThreadPoolExecutor wrapping subprocess.run (also useful on some platforms)
"""

import asyncio
import sys
import argparse
import platform
import shlex
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess

# ------------------------------
# Utilities for ping command
# ------------------------------
IS_WINDOWS = platform.system().lower().startswith("win")

def build_ping_command(host: str, timeout: float):
    """
    Return a list/tuple for subprocess command to ping `host` once with specified timeout.
    timeout is in seconds.
    Note: ping flags vary between systems. We use:
      - Windows: ping -n 1 -w <timeout_ms> host
      - Unix (Linux, mac): ping -c 1 -W <timeout_seconds> host   (works on many Linux distros)
    If you target macOS and have issues with -W semantics, you may adjust here.
    """
    if IS_WINDOWS:
        timeout_ms = int(timeout * 1000)
        return ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        # On many Linux distributions, -W accepts seconds (integer). For safety we round up to int.
        # Some BSD/mac variants differ. If you see odd behavior on macOS, reduce timeout or use thread mode.
        timeout_sec = str(int(max(1, round(timeout))))
        return ["ping", "-c", "1", "-W", timeout_sec, host]

# ------------------------------
# Async ping
# ------------------------------
async def async_ping(host: str, timeout: float, sem: asyncio.Semaphore) -> bool:
    """
    Ping using asyncio subprocess. Returns True if host is reachable (exit code 0).
    """
    cmd = build_ping_command(host, timeout)
    async with sem:
        # Use create_subprocess_exec for safety (avoid shell injection)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            # Wait for process to complete with a hard timeout (in case ping ignores -W on some platforms)
            try:
                await asyncio.wait_for(proc.communicate(), timeout=timeout + 2)
            except asyncio.TimeoutError:
                # Kill the process and consider host unreachable
                proc.kill()
                await proc.communicate()
                return False
            return proc.returncode == 0
        except Exception:
            return False

# ------------------------------
# Threaded (blocking) ping
# ------------------------------
def blocking_ping(host: str, timeout: float) -> bool:
    cmd = build_ping_command(host, timeout)
    try:
        # provide a global timeout to subprocess.run (seconds)
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout + 2)
        return res.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

# ------------------------------
# Main scanning functions
# ------------------------------
async def run_async_mode(hosts, concurrency, timeout):
    sem = asyncio.Semaphore(concurrency)
    tasks = [async_ping(h, timeout, sem) for h in hosts]
    # gather results while preserving order
    results = await asyncio.gather(*tasks)
    return results

def run_thread_mode(hosts, concurrency, timeout):
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as exe:
        futures = [exe.submit(blocking_ping, h, timeout) for h in hosts]
        for f in futures:
            results.append(f.result())
    return results

# ------------------------------
# CLI and orchestration
# ------------------------------
def load_hosts(path: Path):
    if not path.exists():
        print(f"Input file not found: {path}")
        sys.exit(2)
    lines = path.read_text(encoding="utf-8").splitlines()
    hosts = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        hosts.append(s)
    # remove duplicates while preserving order
    seen = set()
    uniq = []
    for h in hosts:
        if h not in seen:
            uniq.append(h)
            seen.add(h)
    return uniq

def save_lists(online, offline, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "online.txt").write_text("\n".join(online) + ("\n" if online else ""))
    (out_dir / "offline.txt").write_text("\n".join(offline) + ("\n" if offline else ""))
    lines = []
    lines.append(f"Online ({len(online)}):")
    lines.extend(online)
    lines.append("")
    lines.append(f"Offline ({len(offline)}):")
    lines.extend(offline)
    (out_dir / "report.txt").write_text("\n".join(lines) + "\n")

def parse_args():
    p = argparse.ArgumentParser(description="Ping hosts from a file (async + threaded options).")
    p.add_argument("input_file", help="Path to text file with one host per line (IP or hostname).")
    p.add_argument("--mode", choices=("async","thread"), default="async",
                   help="Use async subprocesses (async) or ThreadPool blocking pings (thread). Default: async")
    p.add_argument("--concurrency", "-c", type=int, default=200, help="Number of parallel pings (default 200).")
    p.add_argument("--timeout", "-t", type=float, default=2.0, help="Ping timeout in seconds (default 2.0).")
    p.add_argument("--outdir", "-o", default=".", help="Output directory for online.txt and offline.txt (default current).")
    return p.parse_args()

def main():
    args = parse_args()
    hosts = load_hosts(Path(args.input_file))
    if not hosts:
        print("No hosts found in input file.")
        return

    print(f"Scanning {len(hosts)} hosts with mode={args.mode}, concurrency={args.concurrency}, timeout={args.timeout}s")
    if args.mode == "async":
        try:
            results = asyncio.run(run_async_mode(hosts, args.concurrency, args.timeout))
        except Exception as e:
            print("Async mode failed:", e)
            print("Falling back to thread mode.")
            results = run_thread_mode(hosts, min(args.concurrency, 200), args.timeout)
    else:
        results = run_thread_mode(hosts, args.concurrency, args.timeout)

    online = [h for h, ok in zip(hosts, results) if ok]
    offline = [h for h, ok in zip(hosts, results) if not ok]

    outdir = Path(args.outdir)
    save_lists(online, offline, outdir)

    print(f"Done. Online: {len(online)}, Offline: {len(offline)}")
    print(f"Files written to {outdir.resolve()}/online.txt , offline.txt , report.txt")

if __name__ == "__main__":
    main()
