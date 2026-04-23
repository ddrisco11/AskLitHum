import OrnamentDivider from "./OrnamentDivider";

const steps = [
  {
    number: "I",
    title: "Pose your question",
    description: "Ask anything about life, love, loss, or meaning.",
  },
  {
    number: "II",
    title: "Refine the query",
    description:
      "IBM Granite's Query Rewrite adapter normalizes your phrasing so the retriever can reach the right passages.",
  },
  {
    number: "III",
    title: "Search the canon",
    description:
      "MiniLM embeddings retrieve candidate passages across five works; Granite's Context Relevance adapter filters them.",
  },
  {
    number: "IV",
    title: "Discover a voice",
    description:
      "The dominant work chooses its speaker — Dante, Augustine, Lear, Elizabeth, Anna, or Montaigne.",
  },
  {
    number: "V",
    title: "Answer in character",
    description:
      "Mistral 7B, running locally through Ollama, writes the response in the chosen voice.",
  },
  {
    number: "VI",
    title: "Verify and cite",
    description:
      "Granite's Hallucination Detection and Citation Generation adapters ground every sentence back to the text.",
  },
];

const HowItWorks = () => (
  <section className="py-24 px-6">
    <div className="max-w-3xl mx-auto">
      <OrnamentDivider className="mb-12" />

      <h3 className="font-display text-2xl sm:text-3xl text-foreground text-center mb-2">
        How It Works
      </h3>
      <p className="font-body text-sm text-muted-foreground text-center mb-12">
        A literary oracle, grounded in open-source RAG
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
