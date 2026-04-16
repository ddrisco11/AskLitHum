import { motion } from "framer-motion";

interface AnswerCardProps {
  question: string;
  answer: string;
  themes: string[];
}

const AnswerCard = ({ question, answer, themes }: AnswerCardProps) => {
  const paragraphs = answer.split("\n").filter(Boolean);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="max-w-2xl mx-auto"
    >
      {/* Original question */}
      <div className="mb-8 text-center">
        <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest mb-2">
          Your question
        </p>
        <p className="font-display text-xl sm:text-2xl text-foreground italic">
          "{question}"
        </p>
      </div>

      {/* Answer manuscript */}
      <div className="border border-border bg-card shadow-atmospheric p-8 sm:p-12">
        <div className="space-y-5">
          {paragraphs.map((para, i) => (
            <motion.p
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 + i * 0.15 }}
              className="font-body text-base sm:text-lg text-foreground leading-[1.75]"
            >
              {i === 0 && (
                <span className="font-display text-5xl float-left mr-3 mt-1 leading-none text-gold font-semibold">
                  {para[0]}
                </span>
              )}
              {i === 0 ? para.slice(1) : para}
            </motion.p>
          ))}
        </div>

        {/* Themes */}
        <div className="mt-10 pt-6 border-t border-border">
          <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest mb-3">
            Themes
          </p>
          <div className="flex flex-wrap gap-3">
            {themes.map((theme) => (
              <span
                key={theme}
                className="font-ui text-xs small-caps tracking-wider text-muted-foreground border border-border px-3 py-1"
              >
                {theme}
              </span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default AnswerCard;
