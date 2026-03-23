export default function SkeletonCard() {
  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-2xl overflow-hidden animate-pulse">
      <div className="aspect-[16/9] bg-slate-800" />
      <div className="p-4 flex flex-col gap-3">
        <div className="h-4 w-3/4 bg-slate-700 rounded" />
        <div className="h-4 w-full bg-slate-700 rounded" />
        <div className="space-y-2">
          <div className="h-3 w-full bg-slate-700/70 rounded" />
          <div className="h-3 w-5/6 bg-slate-700/70 rounded" />
          <div className="h-3 w-4/6 bg-slate-700/70 rounded" />
        </div>
        <div className="flex justify-between pt-1">
          <div className="h-3 w-20 bg-slate-700/50 rounded" />
          <div className="h-3 w-16 bg-slate-700/50 rounded" />
        </div>
      </div>
    </div>
  );
}
