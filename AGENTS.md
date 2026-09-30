# Agent guide: domain naming session

This repo is a CLI (`domain_checker.py`) that checks domain availability in bulk.
When a user asks you to find, check or brainstorm a domain, run the session below.
Talk to the user in their own language.

## 1. Understand the project

Ask briefly, only for what the user has not already told you:

- What is the project (one sentence)?
- Any seed words, a name they already like, or a tone (short, playful, serious)?

## 2. Confirm the extensions

The default list, always checked in this order:

```
.com  .net  .co  .ai  .io  .xyz  .fun  .finance  .money
```

Show this list and ask whether they want extra extensions on top of it. Offer
these as options (multi-select if your tool supports it):

- `.app`
- `.dev`
- `.gg`
- `.org`
- `.so`
- `.tech`
- none, the default list is enough

Also let them type any other extension. If they want to drop some defaults,
switch from `--extra` to an explicit `--tlds` list.

## 3. Generate and check

Build 10 to 30 candidates from the seed words (your own ideas plus the tool's
`--combos`, `--suffixes`, `--prefixes`). Write them to a temp file, not into
`examples/`, and run:

```bash
python3 domain_checker.py --file /path/to/candidates.txt --extra <extras> --available-only
```

Keep `--workers` at the default or lower; `.com`, `.net` and `.co` use whois and
rate-limit easily. Re-run `⚠ error` / `? unknown` rows with `--workers 1`.

## 4. Report

- Lead with names that are free on `.com` or on several extensions.
- One line per name: the name and its free extensions.
- Remind the user that "available" can still mean premium pricing; they should
  confirm the price at a registrar.
- Ask if they want another round with different seeds or extensions.

## Rules

- Never commit the user's candidate names, project names or results to this repo.
  `examples/words.txt` stays generic placeholder words only.
- Do not register or buy anything; this tool only checks.
