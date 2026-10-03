#!/usr/bin/env python3
"""Draw the README diagrams as light and dark SVG.

Usage: python3 docs/diagrams/charts.py
Writes four diagrams as <name>-light.svg and <name>-dark.svg, in two pairs of
equal height (PAIRS, D-262): what memvet checks against what beside the push
gate, and the example config beside the example output quoted in the README.
The drawing code is quoin_readme.py, a copy kept in step by
promptkits/quoin/github/sync.py. The example output is copied from the README
block that TestReadmeOutputMatchesExample holds to the real run; the example
config is copied from the README toml block, and main() checks it still is.
"""
import re
from pathlib import Path

from quoin_readme import (THEMES, GREEN, BLUE, OCHRE, RED, STEEL, M, R, CH, text, note, head, svg,
                          arrow, tag, box, box_h, legend, pair)

HERE = Path(__file__).resolve().parent
README = HERE.parent.parent / "README.md"

# memvet check examples/broken, wrapped for a phone. (column, text, colour key)
OUTPUT = [
    [(0, "$ memvet check examples/broken", "ink")],
    [(0, "pointers", "ink"), (10, "RED", RED), (18, "MEMORY.md:6", "ink")],
    [(4, "dead reference: memory/preferences.md", "ink2")],
    [(4, "does not exist [pointers/dead-ref]", "ink2")],
    [(0, "tokens", "ink"), (10, "YELLOW", OCHRE), (18, "memory/acme.md", "ink")],
    [(4, "794 estimated tokens exceeds budget of", "ink2")],
    [(4, "400 [tokens/over-budget]", "ink2")],
    [(0, "docs: https://github.com/frankbesch/", "ink2")],
    [(4, "memvet/blob/main/docs/findings.md", "ink2")],
    [(0, "memvet: 1 red, 1 yellow (tree a5e8a264f658)", "ink")],
]
# examples/broken/.memvet.toml, as the README quotes it. (column, text, colour key)
CONFIG = [
    [(0, "examples/broken/.memvet.toml", "ink2")],
    [(0, "[pointers]", "ink")],
    [(0, 'files = ["MEMORY.md"]', "ink")],
    [(0, 'roots = ["memory"]', "ink")],
    [],
    [(0, "[tokens]", "ink")],
    [(0, 'watch = ["MEMORY.md", "memory/*.md"]', "ink")],
    [(0, "budget = 400", "ink")],
]
CONFIG_DESC = ("The config of examples/broken declares two rules. pointers: files MEMORY.md, roots "
               "memory. tokens: watch MEMORY.md and memory/*.md, budget 400.")

OUTPUT_DESC = ("memvet check examples/broken prints two findings. pointers RED MEMORY.md:6 dead "
               "reference: memory/preferences.md does not exist [pointers/dead-ref]. tokens YELLOW "
               "memory/acme.md 794 estimated tokens exceeds budget of 400 [tokens/over-budget]. Then "
               "the docs link and the summary: 1 red, 1 yellow, tree a5e8a264f658.")

POSITIONING_DESC = ("Three inputs go into memvet check: the declared invariants in .memvet.toml, the "
                    "memory repo as it is in the working tree, and git history for authorship and the "
                    "base. check reads them and writes nothing. Three things come out: a RED finding, "
                    "which fails the run with exit 1; a YELLOW finding, which warns and fails only "
                    "under --strict; and a tree fingerprint, the receipt of the tree it judged. RED and "
                    "YELLOW go to the human, who edits the repo, the only fix path. The fingerprint goes "
                    "to CI or a push gate, which acts on the exit status and can hold a later run to "
                    "the receipt with --expect-tree. No arrow returns to the repo.")

PUSH_GATE_DESC = ("A gate script runs memvet check --strict; RED means exit 1 and stop. On a clean run "
                  "it runs memvet fingerprint and writes a marker, .git/push-ok, naming the checks "
                  "passed, the time, and the tree. On git push origin main the pre-push hook reads the "
                  "marker and fingerprints the tree again. A marker under 10 minutes old with a "
                  "matching tree allows one plain push and is consumed. Anything else, a stale marker, "
                  "a moved tree, or a push that is not plain, asks a human.")


def terminal(heading, rows, foot, title, desc, c, spread=0.0, h=0):
    """A terminal panel wrapped for a phone. spread opens the gap between rows."""
    b, y = head(heading, c)
    y -= 6
    for line in rows:
        for col, s, k in line:
            x = M + 4 + col * 12 * CH
            if isinstance(k, str):
                b.append(text(x, y, s, 12, c[k]))
                continue
            # A series key marks a severity or a section: the colour goes on a
            # swatch before the word, and the word wears ink (FBOS D-273).
            b.append(f'<rect x="{x - 8.5:g}" y="{y - 8:g}" width="6" height="6" rx="1.5" fill="{c["series"][k]}"/>')
            b.append(text(x, y, s, 12, c["ink"], weight=600))
        y += 19 + round(10 * spread)
    lines, y = note(y + 8, foot, c)
    return svg(max(y, h), title, desc, b + lines, c)


def example_output(c, spread=0.0, h=0):
    """The README's quoted run."""
    return terminal("The 60-second example", OUTPUT, "RED fails the run. YELLOW fails it only with --strict.",
                    "memvet check examples/broken", OUTPUT_DESC, c, spread, h)


def example_config(c, spread=0.0, h=0):
    """The README's example config, which the run beside it reads."""
    return terminal("Its config", CONFIG, "Two rules. Each finding in the run names its rule.",
                    "examples/broken/.memvet.toml", CONFIG_DESC, c, spread, h)


def positioning(c, spread=0.0, h=0):
    """What is checked against what: three inputs, memvet check, three outputs, two actors.
    spread opens the gaps between the rows of boxes."""
    g = round(20 * spread)
    bw, xs = 108, (12, 126, 240)
    cx = [x + bw / 2 for x in xs]
    inputs = [("Invariants", ".memvet.toml", "you write it", "database"),
              ("Memory repo", "CLAUDE.md, notes", "working tree", "database"),
              ("Git history", "commits, authors", "base commit", "database")]
    outputs = [("RED", "invariant broken", "exit 1", "security"),
               ("YELLOW", "needs attention", "exit 1 with --strict", "cloud"),
               ("Fingerprint", "tree it judged", "receipt", "bus")]
    y1 = 16
    h1 = max(box_h(s, e, bw) for _, s, e, _ in inputs)
    y2 = y1 + h1 + 44 + g
    check = ("memvet check", "reads the three, writes nothing", "no --fix, exit 0 or 1")
    h2 = box_h(check[1], check[2], 336)
    y3 = y2 + h2 + 36 + g
    h3 = max(box_h(s, e, bw) for _, s, e, _ in outputs)
    y4 = y3 + h3 + 48 + g
    actors = [("You edit the repo", "the only fix path", "human", "external"),
              ("CI or push gate", "acts on exit status", "holds the receipt", "external")]
    h4 = max(box_h(s, e, 164) for _, s, e, _ in actors)
    b = []
    for (label, sub, extra, k), x, cxx, t in zip(inputs, xs, cx, ("declared", "files", "history")):
        b += box(x, y1, bw, h1, label, sub, extra, k, c)
        b.append(arrow([(cxx, y1 + h1), (cxx, y2)], c["ink2"], c))
        b.append(tag(cxx, y1 + h1 + 26, t, c["ink2"], c))
    b += box(12, y2, 336, h2, *check, "backend", c)
    for (label, sub, extra, k), x, cxx in zip(outputs, xs, cx):
        b.append(arrow([(cxx, y2 + h2), (cxx, y3)], c["ink2"], c))
        b += box(x, y3, bw, h3, label, sub, extra, k, c)
    ym = y3 + h3 + 22 + g // 2
    b.append(arrow([(cx[0], y3 + h3), (cx[0], y4)], c["series"][RED], c, width=2))
    b.append(arrow([(cx[1], y3 + h3), (cx[1], ym), (130, ym), (130, y4)], c["series"][OCHRE], c))
    b.append(arrow([(cx[2], y3 + h3), (cx[2], y4)], c["series"][BLUE], c, dashed=True))
    b.append(tag(cx[2], ym + 4, "--expect-tree", c["series"][BLUE], c))
    for (label, sub, extra, k), x in zip(actors, (12, 184)):
        b += box(x, y4, 164, h4, label, sub, extra, k, c)
    lines, y = note(y4 + h4 + 28, "No arrow returns to the repo: check never writes a file.", c)
    leg, y = legend(y + 14, [("database", "Input"), ("backend", "memvet"), ("security", "RED: run fails"),
                             ("cloud", "YELLOW: warning"), ("bus", "Receipt"), ("external", "Human or gate")], c)
    return svg(max(y, h), "What memvet checks against what", POSITIONING_DESC, b + lines + leg, c)


def push_gate(c, spread=0.0, h=0):
    """One push through a gate built on check and fingerprint.
    spread opens the gap between steps."""
    g = round(10 * spread)
    steps = [("Gate script: memvet check --strict", "RED means exit 1 and stop", "clean, exit 0"),
             ("memvet fingerprint", "tree a5e8a264f658", "tree hash"),
             ("Marker written: .git/push-ok", "checks passed, time, tree", "developer or agent pushes"),
             ("git push origin main", "the pre-push hook reads the marker", "marker found"),
             ("Fingerprint the tree again", "marker under 10 min, same tree?", None)]
    b, y = head("Gating a push on memvet", c)
    y -= 12
    for i, (label, sub, nxt) in enumerate(steps):
        edge = c["series"][GREEN] if i == 0 else c["ink2"]
        b.append(f'<rect x="{M}" y="{y}" width="{R - M}" height="46" rx="4" fill="{c["tint"]}" stroke="{edge}"/>')
        b.append(text(M + 14, y + 19, label, 13, c["ink"], weight=600))
        b.append(text(M + 14, y + 37, sub, 12, c["ink2"]))
        if nxt:
            b.append(arrow([(M + 24, y + 50), (M + 24, y + 78 + g)], c["ink2"], c))
            b.append(text(M + 42, y + 69 + g // 2, nxt, 12, c["ink2"]))
        y += 82 + g
    y -= 36 + g
    ends = [("Push allowed", "one plain push; marker consumed", "origin/main", "backend"),
            ("Ask a human", "stale marker, moved tree, or not a plain push", None, "security")]
    h = max(box_h(s, e, 156) for _, s, e, _ in ends)
    b.append(arrow([(94, y), (94, y + 40)], c["series"][GREEN], c, width=2))
    b.append(tag(104, y + 24, "yes", c["series"][GREEN], c, anchor="start"))
    b.append(arrow([(266, y), (266, y + 40)], c["series"][RED], c, dashed=True))
    b.append(tag(276, y + 24, "no", c["series"][RED], c, anchor="start"))
    for (label, sub, extra, k), x in zip(ends, (16, 188)):
        b += box(x, y + 40, 156, h, label, sub, extra, k, c)
    lines, y = note(y + 40 + h + 28, "memvet stores nothing; the gate script keeps the receipt.", c)
    return svg(max(y, h), "Gating a push on memvet", PUSH_GATE_DESC, b + lines, c)


# The README shows these as pairs, one per line, at one height (D-262).
PAIRS = [("positioning", positioning, "push-gate", push_gate),
         ("example-config", example_config, "example-output", example_output)]


def main():
    block = re.search(r"```toml\n(.*?)```", README.read_text(), re.S).group(1).splitlines()
    drawn = ["".join(s for _, s, _ in row) for row in CONFIG[1:]]
    assert drawn == block, f"CONFIG differs from the README toml block:\n{drawn}\n{block}"
    for theme, c in THEMES.items():
        for ln, lf, rn, rf in PAIRS:
            for name, s in zip((ln, rn), pair(lf, rf, c)):
                (HERE / f"{name}-{theme}.svg").write_text(s)
    print("built", ", ".join(f"{ln} | {rn}" for ln, _, rn, _ in PAIRS))


if __name__ == "__main__":
    main()
