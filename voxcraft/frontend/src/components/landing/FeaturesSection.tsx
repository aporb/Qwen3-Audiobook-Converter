const features = [
  {
    title: "Quick Clip",
    description: "Paste text, pick a voice, click Perform. Instant high-quality audio in seconds.",
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    title: "Studio",
    description: "Rich text editor with selection-based TTS. Highlight a passage and hear it performed.",
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
      </svg>
    ),
  },
  {
    title: "Audiobook",
    description: "Upload EPUB, PDF, or TXT. Select chapters, assign voices, and export a full audiobook.",
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
  },
];

export function FeaturesSection() {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-6 py-20">
      <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4 text-center">
        Three ways to create
      </h2>
      <p className="text-text-secondary mb-12 text-center max-w-lg">
        From a quick snippet to a full-length audiobook, VoxCraft scales with your needs.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        {features.map((feature, i) => (
          <div
            key={feature.title}
            className="glass-panel-solid p-6 flex flex-col gap-4 hover:scale-[1.02] transition-transform duration-300 animate-slide-up"
            style={{ animationDelay: `${i * 150}ms`, animationFillMode: "backwards" }}
          >
            <div className="text-white/70">{feature.icon}</div>
            <h3 className="text-lg font-semibold text-text-primary">{feature.title}</h3>
            <p className="text-sm text-text-secondary leading-relaxed">{feature.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
