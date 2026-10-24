export default function PhotoCard({ photo }) {
  return (
    <div className="relative bg-paper rounded overflow-hidden">
      <img src={photo.url} alt="" className="w-full aspect-[4/3] object-cover" />
      <div className="stamp absolute top-2 right-2 border-2 border-safelight text-safelight font-mono text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm bg-ink/10">Match</div>
      <div className="flex items-center justify-between px-3 py-2">
        <span className="font-mono text-[11px] text-ink/60">Match score: {Math.round(photo.confidence * 100)}%</span>
        <a href={photo.url} download className="font-mono text-[11px] uppercase tracking-wide text-safelight-dim hover:text-safelight">Download</a>
      </div>
    </div>
  )
}
