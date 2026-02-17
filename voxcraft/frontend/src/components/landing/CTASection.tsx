interface CTASectionProps {
  onEnter: () => void;
}

export function CTASection({ onEnter }: CTASectionProps) {
  return (
    <section className="min-h-[50vh] flex flex-col items-center justify-center px-6 py-20">
      <button
        onClick={onEnter}
        className="group relative px-10 py-4 text-lg font-semibold text-white rounded-2xl bg-white/10 border border-white/20 transition-all duration-300 hover:bg-white/15 hover:scale-105 animate-pulse-glow"
      >
        Enter VoxCraft
        <span className="absolute inset-0 rounded-2xl bg-white/5 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-300" />
      </button>
      <p className="mt-4 text-xs text-text-muted">
        Press Enter or click to continue
      </p>
    </section>
  );
}
