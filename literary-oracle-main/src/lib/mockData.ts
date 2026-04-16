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
}

export interface MockResponse {
  responder: Responder;
  answer: string;
  evidence: EvidenceCard[];
  themes: string[];
}

export const mockResponses: Record<string, MockResponse> = {
  default: {
    responder: {
      name: "Augustine",
      work: "Confessions",
      author: "Saint Augustine",
      descriptor: "Responding through themes of loss, memory, and inward searching",
      era: "4th Century",
    },
    answer: `You speak of lost keys, but what you truly seek is the order that once held your world in place. In my own wanderings, I discovered that what we lose in the outer world is often a mirror of what we have neglected within.\n\nConsider: the keys were not lost in the moment you noticed their absence. They were lost in the moment your attention drifted — when the mind, restless and scattered, failed to mark the small act of setting them down. This is the nature of all loss. It begins not with the thing departing, but with us ceasing to be present.\n\nRetrace not only your steps, but your thoughts. Where was your mind when your hands last held what you now seek? The path back to what is lost always runs through memory — and memory, as I have written, is a vast palace, deeper than we dare to fathom.\n\nPerhaps the keys will be found beside the door. But the deeper finding is this: attend to the small things. For in them, the larger order of your life is kept or broken.`,
    evidence: [
      {
        work: "Confessions",
        author: "Augustine",
        section: "Book X, Chapter 8",
        excerpt: "Great is the power of memory, a fearful thing, O my God, a deep and boundless manifoldness; and this thing is the mind, and this am I myself.",
        relevance: "Memory & Search",
      },
      {
        work: "Inferno",
        author: "Dante Alighieri",
        section: "Canto I, Lines 1–3",
        excerpt: "Midway upon the journey of our life / I found myself within a forest dark, / For the straightforward pathway had been lost.",
        relevance: "Being Lost",
      },
      {
        work: "To the Lighthouse",
        author: "Virginia Woolf",
        section: "Part I, Chapter 11",
        excerpt: "What is the meaning of life? That was all — a simple question; one that tended to close in on one with years. The great revelation had never come.",
        relevance: "Domestic Order",
      },
      {
        work: "Song of Solomon",
        author: "Toni Morrison",
        section: "Chapter 15",
        excerpt: "You wanna fly, you got to give up the shit that weighs you down.",
        relevance: "Letting Go",
      },
    ],
    themes: ["Memory", "Attention", "Loss", "Self-Knowledge"],
  },
  betrayal: {
    responder: {
      name: "King Lear",
      work: "King Lear",
      author: "William Shakespeare",
      descriptor: "Responding through themes of betrayal, loyalty, and the storm within",
      era: "17th Century",
    },
    answer: `Betrayal! I know its shape better than any living soul. I gave my kingdom to serpents who wore the faces of daughters, and cast out the one whose love was true but whose tongue refused to flatter.\n\nYou ask how to deal with betrayal, and I tell you: first, survive the storm. There will be a tempest — in your mind, in your chest, in the sleepless hours. Do not seek shelter from it too quickly. The storm teaches. It strips away every pretense and forces you to see clearly what you could not before.\n\nSecond: examine your own hand in it. I do not say this to wound you further, but because I learned too late that my own vanity invited the very treachery I suffered. We are not always innocent in our betrayals.\n\nThird, and this is the hardest wisdom: let the betrayal change you, but do not let it harden you. I lost everything and found, at the very end, the only love that mattered — but I found it too late. You need not make the same error. The world is not composed entirely of treachery. There are still those who are faithful.`,
    evidence: [
      {
        work: "King Lear",
        author: "William Shakespeare",
        section: "Act III, Scene 2",
        excerpt: "Blow, winds, and crack your cheeks! rage! blow! / You cataracts and hurricanoes, spout / Till you have drench'd our steeples, drown'd the cocks!",
        relevance: "Inner Storm",
      },
      {
        work: "The Odyssey",
        author: "Homer",
        section: "Book XI",
        excerpt: "There is nothing more dreadful and more shameless than a woman who plans such deeds in her heart as the foul deed which she plotted.",
        relevance: "Betrayal",
      },
      {
        work: "Confessions",
        author: "Augustine",
        section: "Book II, Chapter 2",
        excerpt: "I was in love with my own ruin, in love with decay: not with the thing for which I was decaying, but with decay itself.",
        relevance: "Self-Deception",
      },
    ],
    themes: ["Betrayal", "Loyalty", "Self-Knowledge", "Forgiveness"],
  },
};

export const allResponders: Responder[] = [
  { name: "Augustine", work: "Confessions", author: "Saint Augustine", descriptor: "Themes of memory, faith, and the restless heart", era: "4th Century" },
  { name: "Dante", work: "Inferno", author: "Dante Alighieri", descriptor: "Themes of journey, justice, and divine order", era: "14th Century" },
  { name: "King Lear", work: "King Lear", author: "William Shakespeare", descriptor: "Themes of pride, loyalty, and the storm within", era: "17th Century" },
  { name: "Elizabeth Bennet", work: "Pride and Prejudice", author: "Jane Austen", descriptor: "Themes of wit, judgment, and social truth", era: "19th Century" },
  { name: "Lily Briscoe", work: "To the Lighthouse", author: "Virginia Woolf", descriptor: "Themes of art, perception, and the passage of time", era: "20th Century" },
  { name: "Milkman Dead", work: "Song of Solomon", author: "Toni Morrison", descriptor: "Themes of identity, flight, and ancestral memory", era: "20th Century" },
];

export function getMockResponse(question: string): MockResponse {
  const lower = question.toLowerCase();
  if (lower.includes("betray") || lower.includes("trust") || lower.includes("lie")) {
    return mockResponses.betrayal;
  }
  return mockResponses.default;
}
