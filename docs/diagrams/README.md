# Diagrams

Rendered SVG shown in the README, drawn on a 360-unit canvas so the text
keeps its size on a phone. Light and dark variants of each.

- `positioning-*.svg` beside `push-gate-*.svg`: what memvet checks against
  what, and one push through a gate built on `check` and `fingerprint`
  (README, "The failure mode").
- `example-config-*.svg` beside `example-output-*.svg`: the config of
  `examples/broken` and the quoted run of `memvet check` on it (README,
  "60-second example").
- `architecture.svg`: internal package layout, not linked from the README.

Each pair is drawn at one height, with IBM Plex embedded so the type is the
same on every device.

Rebuild with `python3 docs/diagrams/charts.py`. `quoin_readme.py` is the
drawing module, a copy kept in step from its source repository.
