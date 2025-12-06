interface SpacingProps {
  size: number;
}

export function Spacing({ size }: SpacingProps) {
  return <div style={{ height: `${size}px` }} />;
}
