# Motion: Guardia AI v2.0.0 Tactical Animation Spec

Locked summary: micro-motion tokens and scripted transitions for the GCS interface. Emphasizes low GPU overhead, hardware accelerated transforms, and zero decorative fluff.

## 1. Motion Tokens
- Duration:
  - `--motion-duration-fast`: 120ms (button press, reticle lock snap)
  - `--motion-duration-normal`: 240ms (panel expansion, drawer open)
  - `--motion-duration-deliberate`: 450ms (emergency modal reveal)
- Easing:
  - `--motion-ease-out`: cubic-bezier(0.16, 1, 0.3, 1) (rapid responsive deceleration)
  - `--motion-ease-spring`: cubic-bezier(0.34, 1.56, 0.64, 1) (reticle acquisition snap)
  - `--motion-ease-linear`: linear (continuous radar rotation)

## 2. HUD Instrumentation Motion
1. Artificial Horizon Pitch and Roll:
   - Updated at 20 Hz from MAVLink ATTITUDE messages.
   - Interpolated using CSS transforms `transform: translateY({pitch_px}px) rotate({roll_deg}deg)` with `transition: transform 50ms linear`.
   - Never update layout properties (top, left, margin) to avoid browser reflow.
2. Target Lock Reticle:
   - When candidate detected: dashed border box fades in with scale from 1.15 to 1.00 (`--motion-duration-fast`).
   - When confirmed locked: corner brackets snap inward by 4px (`--motion-ease-spring`), color shifts from amber to neon green, and a subtle single-pulse ring expands outward and dissolves over 300ms.
   - When target occluded: box border transitions to a slow 1 Hz blinking opacity (1.0 to 0.3).
3. Search Radar Sweep:
   - When drone is in expanding square or circular search mode, the mini-map radar displays a 360-degree rotating gradient sector with 2.0s period (`animation: radar-sweep 2s linear infinite`).
4. Alert and Emergency Banner:
   - Failsafe warnings slide down from screen top with `--motion-duration-deliberate` using `--motion-ease-out`.
   - Red hazard stripes on the emergency kill button have a subtle continuous diagonal scroll (20px per second) to signal dangerous state.
