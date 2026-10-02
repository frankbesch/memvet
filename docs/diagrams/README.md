# Diagrams

Rendered SVG shown in the README, drawn on a 360-unit canvas so the text
keeps its size on a phone. Light and dark variants of each.

- `example-output-*.svg`: the quoted run of `memvet check examples/broken`.
- `positioning-*.svg`: what memvet checks against what (README, "The failure mode").
- `push-gate-*.svg`: one push through a gate built on `check` and `fingerprint` (README, "In CI").
- `architecture.svg`: internal package layout, not linked from the README.

Rebuild with `python3 docs/diagrams/charts.py`. `quoin_readme.py` is the
drawing module, a copy kept in step from its source repository.
