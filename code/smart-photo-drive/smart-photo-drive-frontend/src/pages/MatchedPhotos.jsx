import { useState } from 'react'
import { useLocation, useParams, Link } from 'react-router-dom'
import { resolvePhotoUrl } from '../config'

export default function MatchedPhotos() {
  const { eventId } = useParams()
  const location = useLocation()
  const matches = location.state?.matches
  const checked = location.state?.checked
  const totalPhotos = location.state?.totalPhotos
  const closest = location.state?.closestConfidence
  const [minScore, setMinScore] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 12
  const filteredMatches = matches?.filter((photo) => photo.confidence * 100 >= minScore) ?? []
  const visibleMatches = filteredMatches.slice((page - 1) * pageSize, page * pageSize)

  if (!matches) {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <p className="text-ash mb-4">No search results to show yet.</p>
        <Link to={`/events/${eventId}`} className="text-safelight hover:underline">
          Go upload a reference photo
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-14">
      <p className="font-mono text-xs uppercase tracking-widest text-safelight mb-2">Search results</p>
      <h1 className="font-display text-4xl mb-8">
        {matches.length === 0 ? "We couldn't find you in this event" : 'Your matched photos'}
      </h1>
      {matches.length > 0 && <p className="text-ash text-sm mb-6">Match scores rank photos by face similarity. They are not probabilities of being correct.</p>}

      {matches.length === 0 ? (
        <div className="text-ash text-sm space-y-2">
          {checked === 0 ? (
            <p>
              None of this event's {totalPhotos ?? 0} photos have face data stored, so there was nothing
              to compare against. The photos need to be re-scanned for faces (ask the event manager, or
              run the re-scan script on the backend).
            </p>
          ) : (
            <p>
              Compared against {checked} photo{checked === 1 ? '' : 's'} containing faces
              {totalPhotos != null ? ` (out of ${totalPhotos} uploaded)` : ''}.
              {closest != null && ` The closest face had a display match score of ${Math.round(closest * 100)}%. This is not a probability.`}
            </p>
          )}
          <p>Try a clearer, front-facing reference photo.</p>
        </div>
      ) : (
        <>
        <div className="flex items-center gap-3 mb-6 font-mono text-xs">
          <label htmlFor="min-score">Minimum display match score</label>
          <select id="min-score" value={minScore} onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1) }} className="bg-ink-soft border border-chrome rounded px-2 py-1">
            {[0, 50, 60, 70, 80, 90].map((score) => <option key={score} value={score}>{score}%</option>)}
          </select>
          <span className="text-ash">{filteredMatches.length} of {matches.length} photos</span>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {visibleMatches.map((photo) => {
            const src = resolvePhotoUrl(photo.url)
            return (
              <div key={photo.filename} className="relative bg-paper rounded overflow-hidden">
                <img src={src} alt="" className="w-full aspect-[4/3] object-cover" />
                <div className="stamp absolute top-2 right-2 border-2 border-safelight text-safelight font-mono text-[10px] font-bold uppercase px-2 py-0.5 rounded-sm bg-ink/10">
                  Match
                </div>
                <div className="flex items-center justify-between px-3 py-2">
                  <span className="font-mono text-[11px] text-ink/60">
                    Match score: {Math.round(photo.confidence * 100)}%
                  </span>
                  <a
                    href={`${src}&download=1`}
                    download
                    className="font-mono text-[11px] uppercase tracking-wide text-safelight-dim hover:text-safelight"
                  >
                    Download
                  </a>
                </div>
              </div>
            )
          })}
        </div>
        {filteredMatches.length === 0 && <p className="text-ash text-sm mt-6">No photos meet this score filter.</p>}
        {filteredMatches.length > pageSize && <div className="flex items-center justify-center gap-4 mt-8 font-mono text-xs">
          <button disabled={page === 1} onClick={() => setPage((p) => p - 1)} className="disabled:opacity-40">Previous</button>
          <span>Page {page} of {Math.ceil(filteredMatches.length / pageSize)}</span>
          <button disabled={page * pageSize >= filteredMatches.length} onClick={() => setPage((p) => p + 1)} className="disabled:opacity-40">Next</button>
        </div>}
        </>
      )}
    </div>
  )
}
