# Project guidance

For text-bearing browser UI changes, use the installed `uncodixfy-pretext`
skill. Measure bounded labels and controls with Pretext, and use its accordion
stretch layout when a main panel must adapt to both width and height.

The continuous-rating plugin owns input, clocks, sampling and interruption
behavior. `task/js/flubber-feedback.js` is visual feedback only. Keep the
existing 2D sample columns stable and record display changes as timed events.
