export default function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-slate-100 p-5 animate-pulse">
      <div className="h-3 w-24 bg-slate-200 rounded mb-3" />
      <div className="h-8 w-16 bg-slate-200 rounded mb-2" />
      <div className="h-3 w-32 bg-slate-100 rounded" />
    </div>
  );
}
