#!/usr/bin/env python3
"""
domain-checker — bulk domain availability checker.

Generates names from a word pool and checks the requested extensions.
  default: .com .net .co .ai .io .xyz .fun .finance .money
  RDAP where the registry serves it (404=available, 200=taken),
  whois otherwise (.com / .net / .co): "NOT FOUND"=available

Examples:
  python3 domain_checker.py --words example sample --combos --suffixes
  python3 domain_checker.py --words example --extra app dev gg
  python3 domain_checker.py --words example --tlds com ai --available-only
  python3 domain_checker.py --file examples/words.txt --max 50
  echo "example sample" | python3 domain_checker.py --stdin --combos
"""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ID_RDAP = "https://rdap.identitydigital.services/rdap/"
IANA_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"

# extensions checked via whois -> server (None = default referral).
# Checked BEFORE RDAP: these registries have no usable public RDAP.
WHOIS_TLDS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "co": None,
    "fi": "whois.fi",
}

# tld -> rdap base url, filled lazily from the IANA bootstrap registry
_rdap_map: dict[str, str] = {}


def rdap_base(tld: str) -> str | None:
    """Resolve a TLD's RDAP endpoint from IANA's bootstrap file (fetched once)."""
    global _rdap_map
    if not _rdap_map:
        try:
            req = urllib.request.Request(
                IANA_BOOTSTRAP, headers={"User-Agent": "domain-checker/1.0"}
            )
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            for tlds, urls in data.get("services", []):
                if not urls:
                    continue
                base = urls[0]
                if not base.endswith("/"):
                    base += "/"
                for t in tlds:
                    _rdap_map[t.lower()] = base
        except Exception:
            _rdap_map = {"__failed__": ""}
    return _rdap_map.get(tld)


DEFAULT_TLDS = ["com", "net", "co", "ai", "io", "xyz", "fun", "finance", "money"]

# Common tech affixes for name generation
SUFFIXES = ["app", "hq", "ly", "hub", "get", "go", "try", "use", "labs", "kit", "ify", "ai"]
PREFIXES = ["get", "my", "go", "try", "join", "use"]

# ANSI colors
G, R, Y, DIM, RST = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"


def check_rdap(domain: str, base: str) -> str:
    url = base + "domain/" + domain
    req = urllib.request.Request(url, headers={"User-Agent": "domain-checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            code = r.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        return "error"
    if code == 404:
        return "available"
    if code == 200:
        return "taken"
    if code == 429:
        return "ratelimited"
    return "unknown"


def check_whois(domain: str, host: str | None = None, retries: int = 2) -> str:
    cmd = ["whois", "-h", host, domain] if host else ["whois", domain]
    out = ""
    for attempt in range(retries + 1):
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=25
            ).stdout.lower()
        except Exception:
            out = ""
        if out:
            break
        time.sleep(2 * (attempt + 1))   # registry rate limit -> back off
    if not out:
        return "error"
    for sig in ("not found", "no match", "does not exist", "no data found", "no object found"):
        if sig in out:
            return "available"
    if "domain name:" in out or "registry domain id" in out:
        return "taken"
    if "status" in out and "registered" in out:   # .fi style key-dot-value output
        return "taken"
    return "unknown"


def check(domain: str, tld: str) -> str:
    if tld in WHOIS_TLDS:
        return check_whois(domain, WHOIS_TLDS[tld])
    base = rdap_base(tld)
    if base:
        st = check_rdap(domain, base)
        if st != "error":
            return st
    return check_whois(domain)


def clean(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == "-").strip("-")


def generate(words: list[str], combos: bool, suffixes: bool, prefixes: bool) -> list[str]:
    words = [clean(w) for w in words if clean(w)]
    names: list[str] = list(words)
    if suffixes:
        names += [w + s for w in words for s in SUFFIXES]
    if prefixes:
        names += [p + w for w in words for p in PREFIXES]
    if combos:
        names += [a + b for a, b in itertools.permutations(words, 2)]
    # dedupe while preserving order
    seen, out = set(), []
    for n in names:
        n = clean(n)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="bulk domain availability checker")
    src = ap.add_argument_group("word source")
    src.add_argument("--words", nargs="+", default=[], help="base words")
    src.add_argument("--file", help="file with one word per line")
    src.add_argument("--stdin", action="store_true", help="read words from stdin")
    gen = ap.add_argument_group("generation")
    gen.add_argument("--combos", action="store_true", help="word pairs (alpha + beta -> alphabeta)")
    gen.add_argument("--suffixes", action="store_true", help="tech suffixes (app, hq, ly, go, ...)")
    gen.add_argument("--prefixes", action="store_true", help="prefixes (get, my, try, ...)")
    ap.add_argument("--tlds", nargs="+", default=DEFAULT_TLDS,
                    help="extensions to check, replaces the default list (" + " ".join(DEFAULT_TLDS) + ")")
    ap.add_argument("--extra", nargs="+", default=[], help="extensions appended to --tlds (e.g. app dev gg)")
    ap.add_argument("--max", type=int, default=0, help="cap number of names checked (0=unlimited)")
    ap.add_argument("--workers", type=int, default=6, help="concurrent requests (keep low for rate limits)")
    ap.add_argument("--available-only", action="store_true", help="only show names with a free TLD")
    args = ap.parse_args()

    words = list(args.words)
    if args.file:
        with open(args.file) as f:
            words += f.read().split()
    if args.stdin:
        words += sys.stdin.read().split()
    if not words:
        ap.error("no words provided (--words / --file / --stdin)")

    names = generate(words, args.combos, args.suffixes, args.prefixes)
    if args.max > 0:
        names = names[: args.max]
    tlds: list[str] = []
    for t in args.tlds + args.extra:
        t = t.lstrip(".").lower()
        if t and t not in tlds:
            tlds.append(t)

    for t in tlds:                    # warm the bootstrap cache before threads start
        rdap_base(t)

    jobs = [(n, t) for n in names for t in tlds]
    print(f"{DIM}{len(names)} names x {len(tlds)} extensions = {len(jobs)} checks...{RST}\n", file=sys.stderr)

    results: dict[tuple[str, str], str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check, f"{n}.{t}", t): (n, t) for n, t in jobs}
        for fut in futs:
            key = futs[fut]
            results[key] = fut.result()

    mark = {
        "available": f"{G}✔ AVAILABLE{RST}",
        "taken": f"{R}✘ taken{RST}",
        "ratelimited": f"{Y}⏳ rate-limited{RST}",
        "unknown": f"{Y}? unknown{RST}",
        "error": f"{Y}⚠ error{RST}",
        "unsupported": f"{DIM}-{RST}",
    }

    total_avail = 0
    for n in names:
        cells = []
        row_has_avail = False
        for t in tlds:
            st = results.get((n, t), "unknown")
            if st == "available":
                row_has_avail = True
                total_avail += 1
            cells.append(f".{t} {mark.get(st, st)}")
        if args.available_only and not row_has_avail:
            continue
        print(f"{n:<20} " + "  ".join(cells))

    print(f"\n{DIM}Total available extensions: {G}{total_avail}{RST}", file=sys.stderr)


if __name__ == "__main__":
    main()
