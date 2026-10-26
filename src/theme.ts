// Paper palette with a green accent — see VIDEO-SYSTEM.md, section 7.

export const VIDEO = {
  width: 1080,
  height: 1920,
  fps: 30,
} as const;

// Text must stay inside this box: social app UI covers the edges.
export const SAFE = {
  left: 90,
  right: 90,
  top: 220,
  bottom: 380,
} as const;

export const COLORS = {
  paper: "#F3EEE3",
  paperDark: "#E6DECD",
  ink: "#1E1D1A",
  inkSoft: "#5B574F",
  accent: "#1F7A4D",
  accentLight: "#CFE6D8",
  line: "#C9BFAA",
} as const;

export const FONTS = {
  heading: "'Unbounded', 'Montserrat', sans-serif",
  body: "'Inter', 'Montserrat', sans-serif",
} as const;
