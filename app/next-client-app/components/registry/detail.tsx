type DetailProps = { label: string; value: string };

// A label/value pair for use inside a <dl>.
export function Detail({ label, value }: DetailProps) {
  return (
    <div className="min-w-0 space-y-1">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="break-words text-sm text-foreground">{value}</dd>
    </div>
  );
}
