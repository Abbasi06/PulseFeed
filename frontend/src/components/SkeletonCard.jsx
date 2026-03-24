export default function SkeletonCard() {
  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-2xl overflow-hidden">
      {/* Image area */}
      <div className="aspect-[16/9] bg-slate-800 relative overflow-hidden">
        <div className="absolute inset-0 shimmer" />
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col gap-3">
        {/* Title lines */}
        <div className="space-y-2">
          <div className="h-3.5 w-4/5 bg-slate-800 rounded-md relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-3.5 w-3/5 bg-slate-800 rounded-md relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>

        {/* Summary lines */}
        <div className="space-y-2 pt-1">
          <div className="h-2.5 w-full bg-slate-800/80 rounded relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-2.5 w-11/12 bg-slate-800/80 rounded relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-2.5 w-4/6 bg-slate-800/80 rounded relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-between pt-1">
          <div className="h-2.5 w-16 bg-slate-800/60 rounded relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-2.5 w-14 bg-slate-800/60 rounded relative overflow-hidden">
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}
