import { useState } from "react";
import { motion } from "framer-motion";
import OrnamentDivider from "./OrnamentDivider";

interface HeroSectionProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

const HeroSection = ({ onSubmit, isLoading }: HeroSectionProps) => {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim() && !isLoading) {
      onSubmit(question.trim());
    }
  };

  return (
    <section className="min-h-[85vh] flex flex-col items-center justify-center px-6 py-20">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        className="text-center max-w-3xl mx-auto"
      >
        <p className="font-ui small-caps text-muted-foreground tracking-widest text-sm mb-6">
          Columbia Literature Humanities
        </p>

        <h1 className="font-display text-6xl sm:text-7xl md:text-8xl font-semibold text-foreground leading-[1.05] tracking-tight mb-6 text-balance">
          Ask Lit Hum
        </h1>

        <OrnamentDivider className="max-w-xs mx-auto mb-8" />

        <p className="font-body text-lg sm:text-xl text-muted-foreground leading-relaxed mb-12 max-w-lg mx-auto">
          Pose a question. Let the texts answer.
        </p>

        <form onSubmit={handleSubmit} className="w-full max-w-xl mx-auto">
          <div className="relative mb-6">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What weighs upon your soul, traveler?"
              disabled={isLoading}
              className="w-full bg-transparent border-0 border-b border-foreground/30 focus:border-foreground px-0 py-4 text-center font-body text-lg text-foreground placeholder:text-muted-foreground/50 outline-none transition-colors duration-300"
            />
          </div>

          <motion.button
            type="submit"
            disabled={!question.trim() || isLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="font-ui small-caps text-sm tracking-widest border border-gold text-foreground px-10 py-3 hover:bg-accent/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-300"
          >
            Consult the Canon
          </motion.button>
        </form>
      </motion.div>
    </section>
  );
};

export default HeroSection;
