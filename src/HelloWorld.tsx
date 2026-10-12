import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const HelloWorld: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "white",
        justifyContent: "center",
        alignItems: "center",
        fontSize: 100,
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ opacity }}>Hello, Remotion!</div>
    </AbsoluteFill>
  );
};
