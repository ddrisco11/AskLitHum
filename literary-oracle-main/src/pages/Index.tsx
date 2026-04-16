import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import HeroSection from "@/components/HeroSection";
import LoadingState from "@/components/LoadingState";
import ResponderCard from "@/components/ResponderCard";
import AnswerCard from "@/components/AnswerCard";
import EvidenceSection from "@/components/EvidenceSection";
import HowItWorks from "@/components/HowItWorks";
import Footer from "@/components/Footer";
import type { MockResponse } from "@/lib/mockData";

type AppState = "idle" | "loading" | "result" | "error";

const Index = () => {
  const [state, setState] = useState<AppState>("idle");
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<MockResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(async (q: string) => {
    setQuestion(q);
    setState("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const result: MockResponse = await res.json();
      setResponse(result);
      setState("result");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }, []);

  const handleReset = () => {
    setState("idle");
    setQuestion("");
    setResponse(null);
  };

  return (
    <div className="min-h-screen bg-background">
      <AnimatePresence mode="wait">
        {state === "idle" && (
          <motion.div
            key="idle"
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            <HeroSection onSubmit={handleSubmit} isLoading={false} />
            <HowItWorks />
          </motion.div>
        )}

        {state === "loading" && (
          <motion.div
            key="loading"
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            <LoadingState />
          </motion.div>
        )}

        {state === "error" && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-24 px-6 text-center"
          >
            <p className="font-display text-2xl text-foreground mb-4">Something went wrong</p>
            <p className="font-body text-muted-foreground mb-8">{errorMsg}</p>
            <button
              onClick={() => setState("idle")}
              className="font-ui small-caps text-xs tracking-widest text-muted-foreground hover:text-foreground border border-border hover:border-gold px-6 py-2 transition-all duration-300"
            >
              Try again
            </button>
          </motion.div>
        )}

        {state === "result" && response && (
          <motion.div
            key="result"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="py-16 sm:py-24 px-6"
          >
            <div className="max-w-3xl mx-auto space-y-16">
              {/* Back button */}
              <div className="text-center">
                <button
                  onClick={handleReset}
                  className="font-ui small-caps text-xs tracking-widest text-muted-foreground hover:text-foreground border border-border hover:border-gold px-6 py-2 transition-all duration-300"
                >
                  Ask another question
                </button>
              </div>

              <ResponderCard responder={response.responder} />
              <AnswerCard
                question={question}
                answer={response.answer}
                themes={response.themes}
              />
              <EvidenceSection evidence={response.evidence} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {state === "result" && <Footer />}
      {state === "idle" && <Footer />}
    </div>
  );
};

export default Index;
