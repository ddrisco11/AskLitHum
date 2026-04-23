export interface Responder {
  name: string;
  work: string;
  author: string;
  descriptor: string;
  era: string;
}

export interface EvidenceCard {
  work: string;
  author: string;
  section: string;
  excerpt: string;
  relevance: string;
  retrieval_score?: number;
  relevance_score?: number;
}

export interface Citation {
  response_text: string;
  response_begin?: number;
  response_end?: number;
  citation_text: string;
  work: string;
  section: string;
}

export interface PipelineSignals {
  question?: string;
  rewritten_query?: string;
  answerability_score?: number;
  hallucination_score?: number;
}

export interface MockResponse {
  responder: Responder;
  answer: string;
  evidence: EvidenceCard[];
  themes: string[];
  citations?: Citation[];
  pipeline?: PipelineSignals;
}

export const mockResponses: Record<string, MockResponse> = {
  default: {
    responder: {
      name: "Augustine",
      work: "Confessions",
      author: "Saint Augustine",
      descriptor: "Responding through themes of memory, restlessness, and the seeking heart",
      era: "4th Century",
    },
    answer: `You speak of lost keys, but what you truly seek is the order that once held your world in place. In my own wanderings, I discovered that what we lose in the outer world is often a mirror of what we have neglected within.\n\nConsider: the keys were not lost in the moment you noticed their absence. They were lost in the moment your attention drifted — when the mind, restless and scattered, failed to mark the small act of setting them down. This is the nature of all loss. It begins not with the thing departing, but with us ceasing to be present.`,
    evidence: [
      {
        work: "Confessions",
        author: "Saint Augustine",
        section: "Book X",
        excerpt:
          "Great is the power of memory, a fearful thing, O my God, a deep and boundless manifoldness; and this thing is the mind, and this am I myself.",
        relevance: "Memory & Search",
      },
      {
        work: "The Inferno",
        author: "Dante Alighieri",
        section: "Canto I",
        excerpt:
          "Midway upon the journey of our life / I found myself within a forest dark, / For the straightforward pathway had been lost.",
        relevance: "Being Lost",
      },
    ],
    themes: ["Memory", "Attention", "Loss", "Self-Knowledge"],
  },
};

// The five works currently indexed. Each work maps to one dominant speaker
// who voices responses when that work supplies the strongest passages.
export const allResponders: Responder[] = [
  {
    name: "Augustine",
    work: "Confessions",
    author: "Saint Augustine",
    descriptor: "Themes of memory, restlessness, and the seeking heart",
    era: "4th Century",
  },
  {
    name: "Dante",
    work: "The Inferno",
    author: "Dante Alighieri",
    descriptor: "Themes of journey, justice, and descent into the self",
    era: "14th Century",
  },
  {
    name: "King Lear",
    work: "King Lear",
    author: "William Shakespeare",
    descriptor: "Themes of pride, loyalty, and the storm within",
    era: "17th Century",
  },
  {
    name: "Elizabeth Bennet",
    work: "Pride and Prejudice",
    author: "Jane Austen",
    descriptor: "Themes of wit, judgement, and the correction of first impressions",
    era: "19th Century",
  },
  {
    name: "Montaigne",
    work: "Essays (selections)",
    author: "Michel de Montaigne",
    descriptor: "Themes of self-inquiry, skepticism, and the examined ordinary life",
    era: "16th Century",
  },
  {
    name: "Anna Karenina",
    work: "Anna Karenina",
    author: "Leo Tolstoy",
    descriptor: "Themes of passion, society, and the search for meaning amid love and loss",
    era: "19th Century",
  },
];

export function getMockResponse(): MockResponse {
  return mockResponses.default;
}
