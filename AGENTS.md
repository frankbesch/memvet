# AGENTS.md — how an agent should use memvet

memvet checks properties you declare must stay true across a repository of
markdown that an agent runtime reads as memory. Think `go vet` or `fsck`. It
never edits files. There is no `--fix`.

## Commands

```bash
memvet check [--strict] [--format text|json|github] [--changed] [--base <ref>] [--expect-tree <fp>] [--no-color] [path]
memvet init [--dry-run] [path]     # writes .memvet.toml once; refuses to overwrite
memvet fingerprint [path]          # prints the tree fingerprint for --expect-tree
memvet <command> --help
memvet --version
```

`path` defaults to `.`. With no `.memvet.toml`, `check` runs the inferred
config and reports that as a YELLOW `config/inferred` finding.

## Exit codes

| code | meaning |
| --- | --- |
| 0 | no RED findings |
| 1 | RED findings, or YELLOW findings with `--strict` |
| 2 | usage error, or a missing or invalid `.memvet.toml` |

Exit 2 always means "memvet could not run", never "the repo failed".

## For an agent

- Run `memvet check --strict --format json .` before you claim a memory
  repo is clean. Quote the finding ids (for example `mirrors/differ`,
  `append_only/rewritten`) in your receipt, not a summary.
- Use `--changed` in a pre-commit or wrap step to see only findings that
  touch files you modified.
- `memvet init` refuses when `.memvet.toml` exists; treat that as correct
  and edit the existing file.
- memvet does not judge prose, does not store memory, and does not call
  any model. Do not ask it whether content is true.
- Rules are declared in `.memvet.toml`. The rule set is frozen (FBOS
  D-143; the admission bar is in CONTRIBUTING.md). Do not propose new
  rules through this file.

Full reference: [docs/cli.md](docs/cli.md), [docs/rules.md](docs/rules.md),
[docs/findings.md](docs/findings.md). This file is for agents that *use*
the tool. Changing memvet itself? Read [CLAUDE.md](CLAUDE.md) first; its
hard rules bind every agent, whatever the runtime.
