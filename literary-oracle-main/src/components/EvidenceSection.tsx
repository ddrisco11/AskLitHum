import { motion } from "framer-motion";
import type { EvidenceCard } from "@/lib/mockData";
import OrnamentDivider from "./OrnamentDivider";

interface EvidenceSectionProps {
  evidence: EvidenceCard[];
}

const EvidenceSection = ({ evidence }: EvidenceSectionProps) => (
  <motion.section
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.8, delay: 0.8 }}
    className="max-w-3xl mx-auto"
  >
    <OrnamentDivider className="mb-10" />

    <h3 className="font-display text-2xl sm:text-3xl text-foreground text-center mb-2">
      Texts Consulted
    </h3>
    <p className="font-body text-sm text-muted-foreground text-center mb-10">
      The passages that guided this response
    </p>

    <div className="grid gap-5">
      {evidence.map((card, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 1 + i * 0.12 }}
          className="border border-border hover:border-gold/50 bg-card shadow-atmospheric hover:shadow-lifted transition-all duration-500 p-6 sm:p-8 group"
        >
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h4 className="font-display text-lg font-semibold text-foreground">
                {card.work}
              </h4>
              <p className="font-body text-sm text-muted-foreground">
                {card.author} · {card.section}
              </p>
            </div>
            <span className="font-ui text-[10px] small-caps tracking-widest text-gold border border-gold/30 px-2.5 py-1 shrink-0">
              {card.relevance}
            </span>
          </div>

          <blockquote className="font-body text-foreground/80 italic leading-relaxed border-l-2 border-gold/30 pl-5">
            "{card.excerpt}"
          </blockquote>
        </motion.div>
      ))}
    </div>
  </motion.section>
);

export default EvidenceSection;
