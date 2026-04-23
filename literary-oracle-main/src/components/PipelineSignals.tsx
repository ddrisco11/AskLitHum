import { motion } from "framer-motion";
import type { PipelineSignals as Signals, Citation } from "@/lib/mockData";

interface Props {
  question: string;
  pipeline?: Signals;
  citations?: Citation[];
}

function fmtPct(v?: number): string {
  if (v === undefined || v === null || Number.isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}

const PipelineSignals = ({ question, pipeline, citations }: Props) => {
  if (!pipeline && (!citations || citations.length === 0)) return null;

  const rewrote =
    pipeline?.rewritten_query &&
    pipeline.rewritten_query.trim() !== question.trim();

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 1.4 }}
      className="max-w-3xl mx-auto"
    >
      <div className="border border-border bg-card/60 p-6 sm:p-8">
        <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest mb-5 text-center">
          Granite RAG Signals
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-5 text-center">
          <Signal
            label="Answerability"
            value={fmtPct(pipeline?.answerability_score)}
            hint="How well the retrieved passages cover your question"
          />
          <Signal
            label="Hallucination Risk"
            value={fmtPct(pipeline?.hallucination_score)}
            hint="Fraction of the response not grounded in passages"
            inverted
          />
          <Signal
            label="Citations"
            value={String(citations?.length ?? 0)}
            hint="Sentences traced to specific passages"
          />
        </div>

        {rewrote && (
          <div className="mt-6 pt-5 border-t border-border">
            <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest mb-2">
              Query Rewritten For Retrieval
            </p>
            <p className="font-body text-sm text-foreground italic">
              "{pipeline?.rewritten_query}"
            </p>
          </div>
        )}

        {citations && citations.length > 0 && (
          <div className="mt-6 pt-5 border-t border-border space-y-3">
            <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest">
              Supporting citations
            </p>
            {citations.slice(0, 4).map((c, i) => (
              <div key={i} className="text-sm">
                <p className="font-body text-foreground/80 italic">
                  "{c.response_text.trim()}"
                </p>
                <p className="font-ui text-xs text-muted-foreground mt-1">
                  → {c.work}, {c.section}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.section>
  );
};

interface SignalProps {
  label: string;
  value: string;
  hint: string;
  inverted?: boolean;
}

const Signal = ({ label, value, hint }: SignalProps) => (
  <div>
    <p className="font-display text-2xl text-foreground mb-1">{value}</p>
    <p className="font-ui text-[10px] small-caps tracking-widest text-gold">
      {label}
    </p>
    <p className="font-body text-[11px] text-muted-foreground mt-2 leading-snug">
      {hint}
    </p>
  </div>
);

export default PipelineSignals;
