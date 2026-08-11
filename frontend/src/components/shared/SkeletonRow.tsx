interface SkeletonRowProps {
  cols?: number;
}

export default function SkeletonRow({ cols = 4 }: SkeletonRowProps) {
  return (
    <tr className="animate-pulse">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-200 rounded-md" style={{ width: `${60 + (i % 3) * 15}%` }} />
        </td>
      ))}
    </tr>
  );
}
