import OrnamentDivider from "./OrnamentDivider";

const steps = [
  { number: "I", title: "Pose your question", description: "Ask anything about life, love, loss, or meaning." },
  { number: "II", title: "Search the canon", description: "The app retrieves the most relevant passages across the Lit Hum texts." },
  { number: "III", title: "Discover a voice", description: "The strongest literary figure is chosen to respond." },
  { number: "IV", title: "Receive an answer", description: "A response grounded in textual evidence, in the voice of the canon." },
];

const HowItWorks = () => (
  <section className="py-24 px-6">
    <div className="max-w-3xl mx-auto">
      <OrnamentDivider className="mb-12" />

      <h3 className="font-display text-2xl sm:text-3xl text-foreground text-center mb-2">
        How It Works
      </h3>
      <p className="font-body text-sm text-muted-foreground text-center mb-12">
        A literary oracle in four steps
      </p>

      <div className="grid sm:grid-cols-2 gap-8">
        {steps.map((step) => (
          <div key={step.number} className="text-center sm:text-left">
            <span className="font-display text-3xl text-gold/60 font-semibold">
              {step.number}
            </span>
            <h4 className="font-display text-lg font-semibold text-foreground mt-2 mb-1">
              {step.title}
            </h4>
            <p className="font-body text-sm text-muted-foreground leading-relaxed">
              {step.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default HowItWorks;
