# domain-checker

A tiny, dependency-free terminal tool that generates brandable names from a word
pool and checks domain availability in bulk across the extensions you care about.

No API keys, no accounts, just Python. Works on its own or driven by an AI coding
agent (see [Using with an AI agent](#using-with-an-ai-agent)).

```
example              .com ✘ taken  .net ✘ taken  .co ✘ taken  .ai ✘ taken  .io ✘ taken  .xyz ✔ AVAILABLE  .fun ✔ AVAILABLE  .finance ✔ AVAILABLE  .money ✔ AVAILABLE
sample               .com ✘ taken  .net ✘ taken  .co ✘ taken  .ai ✘ taken  .io ✘ taken  .xyz ✘ taken  .fun ✘ taken  .finance ✔ AVAILABLE  .money ✔ AVAILABLE
```

---

## Default extensions

Checked when you pass no `--tlds`:

```
.com  .net  .co  .ai  .io  .xyz  .fun  .finance  .money
```

Add more on top with `--extra` (for example `--extra app dev gg`), or replace
the whole list with `--tlds`.

## How it works

Availability is resolved per TLD using the most reliable public source:

| Source | Used for | Signal |
|--------|----------|--------|
| RDAP (endpoint from IANA's bootstrap registry) | most TLDs (`.ai`, `.xyz`, `.fun`, `.io`, `.finance`, `.money`, ...) | HTTP `404` = available, `200` = taken |
| `whois` | `.com`, `.net`, `.co` and any TLD without a public RDAP server | `NOT FOUND` / `No match` = available |

Checks run concurrently via a thread pool (keep `--workers` low to stay friendly
with `whois` rate limits).

## Requirements

- Python 3.9+
- `whois` CLI (for `.com` / `.net` / `.co` and RDAP fallbacks)
  - macOS: preinstalled, or `brew install whois`
  - Debian/Ubuntu: `sudo apt install whois`

No pip packages required, standard library only.

## Install

```bash
git clone https://github.com/utkurock/domainchecker.git
cd domainchecker
python3 domain_checker.py --words example sample
```

## Usage

```bash
# basic: a few words, default extensions
python3 domain_checker.py --words example sample

# add extra extensions to the default list
python3 domain_checker.py --words example --extra app dev gg

# generation: combos + tech suffixes, only show available
python3 domain_checker.py --words alpha beta --combos --suffixes --available-only

# from a file (one word per line)
python3 domain_checker.py --file examples/words.txt

# from stdin
echo "example sample" | python3 domain_checker.py --stdin --prefixes

# only specific extensions
python3 domain_checker.py --words example --tlds com ai
```

### Flags

| Flag | Description |
|------|-------------|
| `--words w1 w2 ...` | base words |
| `--file PATH` | read words from a file (one per line) |
| `--stdin` | read words from stdin |
| `--combos` | word pairs (`alpha` + `beta` → `alphabeta`) |
| `--suffixes` | append tech suffixes (`app, hq, ly, go, hub, get, try, use, labs, kit, ify, ai`) |
| `--prefixes` | prepend prefixes (`get, my, go, try, join, use`) |
| `--tlds ...` | extensions to check, replaces the default list |
| `--extra ...` | extensions appended to the list (e.g. `app dev gg`) |
| `--available-only` | only print names with at least one free extension |
| `--max N` | cap the number of names checked |
| `--workers N` | concurrent requests (default `6`, keep low for whois TLDs) |

## Using with an AI agent

The repo ships an [`AGENTS.md`](AGENTS.md) (also loaded through `CLAUDE.md`) that
tells a coding agent such as Claude Code, Codex or Cursor how to run a naming
session:

1. Ask what the project is and collect a few seed words.
2. Show the default extension list and ask which extra extensions to add
   (`.app`, `.dev`, `.gg`, `.org`, `.so`, `.tech`, ...).
3. Generate candidates, run the checker, and report only the useful results.

Open the repo in your agent and say something like:

```
Find me a domain for a budgeting app. Seed words: example, sample.
```

## Caveats

- **"Available" ≠ registrable at base price.** Premium / reserved domains may show
  as free via RDAP/whois but cost more or be restricted. Always confirm the final
  price at a registrar.
- **whois can rate-limit / time out.** If you see `⚠ error` or `? unknown`,
  re-run those names with `--tlds <tld> --workers 1`.
- Results are a point-in-time snapshot; domains can be registered at any moment.

## License

MIT, see [LICENSE](LICENSE).
