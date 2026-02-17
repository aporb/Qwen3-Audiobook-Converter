export function HeroSection() {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center relative px-6">
      {/* Logo */}
      <h1 className="text-6xl sm:text-7xl md:text-8xl font-bold tracking-tight text-white animate-fade-in">
        VoxCraft
      </h1>

      {/* Tagline */}
      <p className="mt-4 text-xl sm:text-2xl text-text-secondary font-light tracking-wide animate-fade-in [animation-delay:200ms]">
        Your books, performed.
      </p>

      {/* Subtitle */}
      <p className="mt-3 text-sm text-text-muted max-w-md text-center animate-fade-in [animation-delay:400ms]">
        Local AI or cloud voices. Full audiobook conversion.
        Privacy-first text-to-speech for your library.
      </p>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 flex flex-col items-center gap-2 animate-fade-in [animation-delay:800ms]">
        <span className="text-xs text-text-muted">Scroll to explore</span>
        <svg
          className="w-5 h-5 text-text-muted animate-bounce"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 14l-7 7m0 0l-7-7m7 7V3"
          />
        </svg>
      </div>
    </section>
  );
}
