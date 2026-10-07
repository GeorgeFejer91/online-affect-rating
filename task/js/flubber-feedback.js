import { buildFlubberPath, createProfiles, createProjectionOffsets } from "./flubber/math.js";
import { createDefaultFlubberMappings, evaluateFlubberMappings } from "./flubber/mappings.js";

const profiles = createProfiles();
const offsets = createProjectionOffsets("online-affect-rating-flubber");
const mappings = createDefaultFlubberMappings();
const palette = { up: "#f2c94c", down: "#2f80ed", left: "#eb5757", right: "#27ae60" };
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

/** Visual feedback only. The jsPsych plugin continues to own input and samples. */
export function createFlubberFeedback(svg) {
  const halo = svg.querySelector(".cr-flubber-halo");
  const shape = svg.querySelector(".cr-flubber-shape");
  const outline = svg.querySelector(".cr-flubber-outline");
  let x = 0;
  let y = 0;
  let phase = 0;
  let lastFrame = performance.now();
  let frameId = 0;

  function frame(now) {
    const values = evaluateFlubberMappings(mappings, { x, y });
    if (!reducedMotion.matches) {
      phase = (phase + Math.min(0.1, Math.max(0, (now - lastFrame) / 1000)) * Math.PI * 2 * values.oscillationFrequency) % (Math.PI * 2);
    }
    lastFrame = now;
    const rendered = buildFlubberPath({
      profiles, offsets, x, y, phase, palette,
      projectionAmplitude: values.projectionAmplitude,
      edgeSmoothness: values.edgeSmoothness,
      pulseSynchrony: values.pulseSynchrony,
      amplitudeVariation: values.waveSizeVariation,
      colorSaturation: values.saturation,
      reducedMotion: reducedMotion.matches,
    });
    for (const path of [halo, shape, outline]) path.setAttribute("d", rendered.path);
    shape.setAttribute("fill", Math.hypot(x, y) < 0.005 ? "#9ca3af" : rendered.color);
    frameId = requestAnimationFrame(frame);
  }

  return {
    setRating(valueX, valueY) {
      x = Math.max(-1, Math.min(1, (valueX - 50) / 50));
      y = Math.max(-1, Math.min(1, (valueY - 50) / 50));
    },
    start() { if (!frameId) frameId = requestAnimationFrame(frame); },
    stop() { cancelAnimationFrame(frameId); frameId = 0; },
  };
}

window.createFlubberFeedback = createFlubberFeedback;
