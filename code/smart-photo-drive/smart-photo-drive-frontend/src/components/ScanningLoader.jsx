export default function ScanningLoader({ label = 'Scanning event photographs…' }) {
  return (
    <div className="relative w-full h-56 bg-ink-soft border border-chrome rounded-lg overflow-hidden flex items-center justify-center">
      <div className="absolute inset-x-0 h-0.5 bg-safelight shadow-[0_0_12px_2px_rgba(193,39,45,0.7)] animate-[scan_1.8s_ease-in-out_infinite]" />
      <p className="font-mono text-xs uppercase tracking-widest text-ash">{label}</p>
      <style>{`@keyframes scan { 0% { top: 8%; } 50% { top: 88%; } 100% { top: 8%; } }`}</style>
    </div>
  )
}
