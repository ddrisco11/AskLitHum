import { motion } from "framer-motion";
import type { Responder } from "@/lib/mockData";

interface ResponderCardProps {
  responder: Responder;
}

const ResponderCard = ({ responder }: ResponderCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
    transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    className="border border-border hover:border-gold bg-card shadow-atmospheric hover:shadow-lifted transition-all duration-500 p-8 sm:p-10 text-center max-w-lg mx-auto"
  >
    {/* Medallion placeholder */}
    <div className="w-20 h-20 mx-auto mb-6 rounded-full border-2 border-gold/40 flex items-center justify-center bg-secondary/50">
      <span className="font-display text-3xl text-foreground font-semibold">
        {responder.name[0]}
      </span>
    </div>

    <p className="font-ui small-caps text-xs text-muted-foreground tracking-widest mb-3">
      A voice emerges from the canon
    </p>

    <h2 className="font-display text-3xl sm:text-4xl font-semibold text-foreground mb-2">
      {responder.name}
    </h2>

    <p className="font-body text-muted-foreground mb-4">
      from <em>{responder.work}</em> by {responder.author}
    </p>

    <div className="h-px bg-gold/30 w-16 mx-auto mb-4" />

    <p className="font-body text-sm text-muted-foreground italic leading-relaxed">
      {responder.descriptor}
    </p>

    <p className="font-ui text-xs text-muted-foreground/60 mt-4 small-caps tracking-wider">
      {responder.era}
    </p>
  </motion.div>
);

export default ResponderCard;
