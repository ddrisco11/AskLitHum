import { motion } from "framer-motion";

const loadingPhrases = [
  "Consulting the texts…",
  "Searching the canon…",
  "A voice emerges…",
];

const LoadingState = () => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="flex flex-col items-center justify-center py-32 px-6"
  >
    <div className="flex gap-2 mb-8">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gold"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.8, repeat: Infinity, delay: i * 0.3 }}
        />
      ))}
    </div>

    <motion.p
      className="font-display text-2xl sm:text-3xl text-foreground italic"
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 3, repeat: Infinity }}
    >
      {loadingPhrases[0]}
    </motion.p>

    <p className="font-ui text-xs small-caps text-muted-foreground mt-4 tracking-widest">
      Searching across the Literature Humanities canon
    </p>
  </motion.div>
);

export default LoadingState;
