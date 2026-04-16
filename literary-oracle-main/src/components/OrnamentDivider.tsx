const OrnamentDivider = ({ className = "" }: { className?: string }) => (
  <div className={`flex items-center justify-center gap-4 ${className}`}>
    <div className="h-px flex-1 bg-border" />
    <svg width="16" height="16" viewBox="0 0 16 16" className="text-gold">
      <path d="M8 0L9.5 6.5L16 8L9.5 9.5L8 16L6.5 9.5L0 8L6.5 6.5L8 0Z" fill="currentColor" opacity="0.6" />
    </svg>
    <div className="h-px flex-1 bg-border" />
  </div>
);

export default OrnamentDivider;
