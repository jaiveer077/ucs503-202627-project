import { useEffect, useState } from 'react'
import EventCard from '../components/EventCard'
import { API_BASE, resolvePhotoUrl } from '../config'

export default function BrowseEvents() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 12

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ q: query, page: String(page), page_size: String(pageSize) })
    fetch(`${API_BASE}/api/events?${params}`, { signal: controller.signal })
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Could not load events.')
        return data
      })
      .then((data) => {
        setEvents(data.events.map((e) => ({ ...e, cover: resolvePhotoUrl(e.cover) })))
        setTotal(data.total)
      })
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, page])

  return (
    <div className="max-w-6xl mx-auto px-6 py-14">
      <p className="font-mono text-xs uppercase tracking-widest text-safelight mb-2">All events</p>
      <h1 className="font-display text-4xl mb-10">Pick an event to search</h1>
      <form onSubmit={(e) => { e.preventDefault(); const nextQuery = draft.trim(); if (nextQuery !== query || page !== 1) { setLoading(true); setError(''); setPage(1); setQuery(nextQuery) } }} className="flex gap-2 mb-8 max-w-lg">
        <input value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={100} placeholder="Search events or locations" aria-label="Search events or locations" className="flex-1 bg-ink-soft border border-chrome rounded px-3 py-2 text-paper" />
        <button type="submit" className="px-4 py-2 bg-safelight rounded font-mono text-xs uppercase">Search</button>
      </form>

      {loading ? (
        <p className="font-mono text-xs text-ash">Loading events…</p>
      ) : error ? (
        <p className="font-mono text-xs text-safelight">{error}</p>
      ) : events.length === 0 ? (
        <p className="font-mono text-xs text-ash">{query ? 'No events match your search.' : 'No events yet — check back once an event manager has created one.'}</p>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {events.map((event) => (<EventCard key={event.id} event={event} />))}
        </div>
      )}
      {!loading && !error && total > pageSize && (
        <div className="flex items-center justify-center gap-4 mt-8 font-mono text-xs">
          <button disabled={page === 1} onClick={() => { setLoading(true); setError(''); setPage((p) => p - 1) }} className="disabled:opacity-40">Previous</button>
          <span>Page {page} of {Math.ceil(total / pageSize)}</span>
          <button disabled={page * pageSize >= total} onClick={() => { setLoading(true); setError(''); setPage((p) => p + 1) }} className="disabled:opacity-40">Next</button>
        </div>
      )}
    </div>
  )
}
