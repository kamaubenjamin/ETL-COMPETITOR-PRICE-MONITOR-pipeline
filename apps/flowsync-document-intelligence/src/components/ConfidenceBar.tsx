interface ConfidenceBarProps {
  value: number;
}

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="confidence" aria-label={`Confidence ${percent}%`}>
      <div className="confidence-track"><span style={{ width: `${percent}%` }} /></div>
      <strong>{percent}%</strong>
    </div>
  );
}
