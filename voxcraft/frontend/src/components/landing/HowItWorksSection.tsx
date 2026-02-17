const steps = [
  { number: "01", title: "Upload", description: "Drop in your text, paste a snippet, or upload an entire book." },
  { number: "02", title: "Configure", description: "Choose an engine, pick a voice, and tweak text processing settings." },
  { number: "03", title: "Export", description: "Generate audio and download as WAV, MP3, or M4B with subtitles." },
];

export function HowItWorksSection() {
  return (
    <section className="min-h-[70vh] flex flex-col items-center justify-center px-6 py-20">
      <h2 className="text-3xl sm:text-4xl font-bold text-text-primary mb-4 text-center">
        How it works
      </h2>
      <p className="text-text-secondary mb-16 text-center max-w-lg">
        Three steps from text to audio. No accounts, no subscriptions to manage.
      </p>

      <div className="flex flex-col md:flex-row items-center gap-8 md:gap-4 max-w-3xl w-full">
        {steps.map((step, i) => (
          <div key={step.number} className="flex items-center gap-4 md:flex-col md:items-center md:text-center flex-1">
            {/* Step card */}
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold text-white">
                {step.number}
              </span>
              <h3 className="text-lg font-semibold text-text-primary mt-2">{step.title}</h3>
              <p className="text-sm text-text-secondary mt-1 max-w-[200px]">{step.description}</p>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className="hidden md:block w-full h-px bg-gradient-to-r from-white/20 to-white/10 mt-4" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
