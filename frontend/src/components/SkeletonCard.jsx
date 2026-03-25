export default function SkeletonCard() {
  return (
    <div className="bg-slate-900 border border-slate-700/60 rounded-2xl overflow-hidden flex flex-col">
      {/* Image area */}
      <div className="aspect-[16/9] relative overflow-hidden bg-slate-800">
        <div className="absolute inset-0 shimmer" />
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col gap-3">
        {/* Title */}
        <div className="space-y-2">
          <div className="h-3 rounded bg-slate-800 relative overflow-hidden" style={{ width: "80%" }}>
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-3 rounded bg-slate-800 relative overflow-hidden" style={{ width: "60%" }}>
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>

        {/* Summary */}
        <div className="space-y-1.5 pt-1">
          {["100%", "92%", "70%"].map((w, i) => (
            <div key={i} className="h-2.5 rounded bg-slate-800/70 relative overflow-hidden" style={{ width: w }}>
              <div className="absolute inset-0 shimmer" />
            </div>
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex gap-1.5 pt-1">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700/50 relative overflow-hidden">
              <div className="absolute inset-0 shimmer" />
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex justify-between pt-0.5">
          <div className="h-2.5 rounded bg-slate-800 relative overflow-hidden" style={{ width: 56 }}>
            <div className="absolute inset-0 shimmer" />
          </div>
          <div className="h-2.5 rounded bg-slate-800 relative overflow-hidden" style={{ width: 48 }}>
            <div className="absolute inset-0 shimmer" />
          </div>
        </div>
      </div>
    </div>
  );
}
