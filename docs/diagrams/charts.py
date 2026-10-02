#!/usr/bin/env python3
"""Draw the README diagrams as light and dark SVG.

Usage: python3 docs/diagrams/charts.py
Writes three diagrams as <name>-light.svg and <name>-dark.svg: the example
output quoted in the README, what memvet checks against what, and the push
gate. The drawing code is quoin_readme.py, a copy kept in step by
promptkits/quoin/github/sync.py. The example output is copied from the README
block that TestReadmeOutputMatchesExample holds to the real run.
"""
from pathlib import Path

from quoin_readme import (THEMES, GREEN, BLUE, OCHRE, RED, STEEL, M, R, CH, text, note, head, svg,
                          arrow, tag, box, box_h, legend)

HERE = Path(__file__).resolve().parent

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


def example_output(c):
    """The README's quoted run, as a terminal panel wrapped for a phone."""
    b, y = head("The 60-second example", c)
    y -= 6
    for line in OUTPUT:
        for col, s, k in line:
            fill = c[k] if isinstance(k, str) else c["series"][k]
            b.append(text(M + 4 + col * 12 * CH, y, s, 12, fill, weight=600 if k in (RED, OCHRE) else None))
        y += 19
    lines, y = note(y + 8, "RED fails the run. YELLOW fails it only with --strict.", c)
    return svg(y, "memvet check examples/broken", OUTPUT_DESC, b + lines, c)


def positioning(c):
    """What is checked against what: three inputs, memvet check, three outputs, two actors."""
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
    y2 = y1 + h1 + 44
    check = ("memvet check", "reads the three, writes nothing", "no --fix, exit 0 or 1")
    h2 = box_h(check[1], check[2], 336)
    y3 = y2 + h2 + 36
    h3 = max(box_h(s, e, bw) for _, s, e, _ in outputs)
    y4 = y3 + h3 + 48
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
    ym = y3 + h3 + 22
    b.append(arrow([(cx[0], y3 + h3), (cx[0], y4)], c["series"][RED], c, width=2))
    b.append(arrow([(cx[1], y3 + h3), (cx[1], ym), (130, ym), (130, y4)], c["series"][OCHRE], c))
    b.append(arrow([(cx[2], y3 + h3), (cx[2], y4)], c["series"][BLUE], c, dashed=True))
    b.append(tag(cx[2], ym + 4, "--expect-tree", c["series"][BLUE], c))
    for (label, sub, extra, k), x in zip(actors, (12, 184)):
        b += box(x, y4, 164, h4, label, sub, extra, k, c)
    lines, y = note(y4 + h4 + 28, "No arrow returns to the repo: check never writes a file.", c)
    leg, y = legend(y + 14, [("database", "Input"), ("backend", "memvet"), ("security", "RED: run fails"),
                             ("cloud", "YELLOW: warning"), ("bus", "Receipt"), ("external", "Human or gate")], c)
    return svg(y, "What memvet checks against what", POSITIONING_DESC, b + lines + leg, c)


def push_gate(c):
    """One push through a gate built on check and fingerprint."""
    steps = [("Gate script: memvet check --strict", "RED means exit 1 and stop", "clean, exit 0"),
             ("memvet fingerprint", "tree a5e8a264f658", "tree hash"),
             ("Marker written: .git/push-ok", "checks passed, time, tree", "developer or agent pushes"),
             ("git push origin main", "the pre-push hook reads the marker", "marker found"),
             ("Fingerprint the tree again", "marker under 10 min, same tree?", None)]
    b, y = head("Gating a push on memvet", c)
    y -= 12
    for i, (label, sub, nxt) in enumerate(steps):
        edge = c["series"][GREEN] if i == 0 else c["rule"]
        b.append(f'<rect x="{M}" y="{y}" width="{R - M}" height="46" rx="4" fill="{c["tint"]}" stroke="{edge}"/>')
        b.append(text(M + 14, y + 19, label, 13, c["ink"], weight=600))
        b.append(text(M + 14, y + 37, sub, 12, c["ink2"]))
        if nxt:
            b.append(arrow([(M + 24, y + 50), (M + 24, y + 78)], c["ink2"], c))
            b.append(text(M + 42, y + 69, nxt, 12, c["ink2"]))
        y += 82
    y -= 36
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
    return svg(y, "Gating a push on memvet", PUSH_GATE_DESC, b + lines, c)


def main():
    for name, draw in (("example-output", example_output), ("positioning", positioning),
                       ("push-gate", push_gate)):
        for theme, c in THEMES.items():
            (HERE / f"{name}-{theme}.svg").write_text(draw(c))
    print("wrote 6 svg files to", HERE)


if __name__ == "__main__":
    main()
