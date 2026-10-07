The Flubber shape and mapping code in this directory comes from
[Affect Tracker Research](https://github.com/GeorgeFejer91/affect-tracker-research)
(`site/src/math.js` and `site/src/research/mappings.js` at
`3c6db83e0742ccd1c9b89d1dbc601059363e8f2f`, copied 2026-10-07).
It is BSD-3-Clause licensed; see [LICENSE](LICENSE).

`../flubber-feedback.js` adapts that renderer to the two 0–100 axes already
recorded by the continuous-rating plugin. It only draws SVG. The existing
plugin still owns pointer input, clocks, sampling, interruptions, and data.
