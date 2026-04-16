import OrnamentDivider from "./OrnamentDivider";

const Footer = () => (
  <footer className="py-16 px-6">
    <div className="max-w-3xl mx-auto">
      <OrnamentDivider className="mb-10" />
      <div className="text-center space-y-3">
        <p className="font-display text-lg text-foreground">Ask Lit Hum</p>
        <p className="font-body text-sm text-muted-foreground leading-relaxed max-w-md mx-auto">
          A literary oracle built on the Columbia University Literature Humanities canon.
          The wisdom of the texts, made conversational.
        </p>
        <p className="font-ui text-[10px] small-caps tracking-widest text-muted-foreground/50 pt-4">
          Not affiliated with Columbia University · For educational exploration
        </p>
      </div>
    </div>
  </footer>
);

export default Footer;
