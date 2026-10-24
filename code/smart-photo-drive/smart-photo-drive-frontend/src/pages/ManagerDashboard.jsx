import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import SprocketStrip from '../components/SprocketStrip'
import { API_BASE, resolvePhotoUrl } from '../config'
import { getAuth, clearAuth } from '../auth'

export default function ManagerDashboard() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newEvent, setNewEvent] = useState({ name: '', date: '', location: '' })
  const [uploadingId, setUploadingId] = useState(null)
  const [uploadProgress, setUploadProgress] = useState('')

  const { token, role } = getAuth()
  const authHeader = { Authorization: `Bearer ${token}` }

  // A 401 means the login token expired (they last 12 hours).
  function handleExpired() {
    clearAuth()
    setError('Your session expired. Please log in again.')
    setEvents([])
  }

  useEffect(() => {
    if (!token || role !== 'manager') return
    const controller = new AbortController()
    fetch(`${API_BASE}/api/manager/events`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    }).then(async (res) => {
      if (res.status === 401) {
        clearAuth()
        throw new Error('Your session expired. Please log in again.')
      }
      if (!res.ok) throw new Error('Could not load your events.')
      return res.json()
    }).then((data) => setEvents(data))
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [token, role])

  async function createEvent(e) {
    e.preventDefault()
    if (!newEvent.name.trim()) return
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/manager/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader },
        body: JSON.stringify(newEvent),
      })
      if (res.status === 401) return handleExpired()
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Could not create the event.'); return }
      setEvents((prev) => [data, ...prev])
      setNewEvent({ name: '', date: '', location: '' })
    } catch {
      setError('Could not reach the server.')
    }
  }

  async function handleUpload(eventId, fileList) {
    const files = Array.from(fileList)
    if (files.length === 0) return
    setUploadingId(eventId)
    setUploadProgress(`0/${files.length}`)
    setError('')
    let completed = 0
    const skipped = []
    const scanFailures = []
    const cloudFailures = []
    try {
      for (let index = 0; index < files.length; index += 3) {
        const batch = files.slice(index, index + 3)
        const formData = new FormData()
        batch.forEach((file) => formData.append('photos', file))
        const res = await fetch(`${API_BASE}/api/manager/events/${eventId}/photos`, {
          method: 'POST', headers: authHeader, body: formData,
        })
        if (res.status === 401) return handleExpired()
        const data = await res.json()
        if (!res.ok) {
          setError(`${completed} of ${files.length} files processed. ${data.error || 'Upload failed.'}`)
          return
        }
        setEvents((prev) => prev.map((ev) => (ev.id === eventId ? data.event : ev)))
        skipped.push(...data.skipped)
        scanFailures.push(...data.scan_failures)
        cloudFailures.push(...data.cloud_failures)
        completed += batch.length
        setUploadProgress(`${completed}/${files.length}`)
        if (!data.face_matching_available) {
          setError('Photos uploaded, but face matching is not installed on the server yet — see backend README.')
        }
      }
      if (skipped.length) setError(`${skipped.length} file(s) skipped: ${skipped.join(', ')}`)
      else if (scanFailures.length) setError(`${scanFailures.length} photo(s) uploaded but could not be scanned for faces: ${scanFailures.join(', ')}`)
      else if (cloudFailures.length) setError(`${cloudFailures.length} photo(s) stayed on local disk because cloud upload failed.`)
    } catch {
      setError(`${completed} of ${files.length} files processed. Could not reach the server during upload.`)
    } finally {
      setUploadingId(null)
      setUploadProgress('')
    }
  }

  async function deleteEvent(event) {
    const ok = window.confirm(
      `Delete "${event.name}" and all ${event.photoCount} of its photos? This cannot be undone.`
    )
    if (!ok) return
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/manager/events/${event.id}`, {
        method: 'DELETE',
        headers: authHeader,
      })
      if (res.status === 401) return handleExpired()
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'Could not delete the event.'); return }
      setEvents((prev) => prev.filter((ev) => ev.id !== event.id))
    } catch {
      setError('Could not reach the server.')
    }
  }

  if (!token || role !== 'manager') {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <p className="text-ash mb-4">
          {error || (token
            ? 'This page is for event manager accounts. You are logged in as an attendee.'
            : 'You need to be logged in as an event manager to see this page.')}
        </p>
        <Link to="/manager/login" className="text-safelight hover:underline">Go to event manager login</Link>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-14">
      <p className="font-mono text-xs uppercase tracking-widest text-safelight mb-2">Event manager</p>
      <h1 className="font-display text-4xl mb-8">Your events</h1>

      <form onSubmit={createEvent} className="grid sm:grid-cols-4 gap-3 mb-6 max-w-2xl">
        <input value={newEvent.name} onChange={(e) => setNewEvent((n) => ({ ...n, name: e.target.value }))} placeholder="Event name" className="sm:col-span-2 bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" />
        <input value={newEvent.date} onChange={(e) => setNewEvent((n) => ({ ...n, date: e.target.value }))} type="date" className="bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" />
        <button type="submit" className="px-4 py-2 bg-safelight rounded font-mono text-xs uppercase tracking-wide hover:bg-safelight-dim transition-colors">Create event</button>
        <input value={newEvent.location} onChange={(e) => setNewEvent((n) => ({ ...n, location: e.target.value }))} placeholder="Location" className="sm:col-span-2 bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" />
      </form>

      {error && <p className="text-sm text-safelight mb-6">{error}</p>}

      {loading ? (
        <p className="font-mono text-xs text-ash">Loading events…</p>
      ) : events.length === 0 ? (
        <p className="font-mono text-xs text-ash">You haven't created any events yet — create one above.</p>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <div key={event.id} className="bg-ink-soft border border-chrome rounded-lg overflow-hidden">
              <div className="flex items-center justify-between gap-4 px-5 py-4">
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-16 h-12 rounded bg-chrome overflow-hidden shrink-0">
                    {event.cover && <img src={resolvePhotoUrl(event.cover)} alt="" className="w-full h-full object-cover" />}
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-display text-xl truncate">{event.name}</h3>
                    <p className="font-mono text-xs text-ash">{event.date || 'No date set'} &middot; {event.photoCount.toLocaleString()} photos</p>
                    {event.scannedCount != null && <p className="font-mono text-xs text-ash">{event.scannedCount.toLocaleString()} scanned &middot; {(event.faceCount ?? 0).toLocaleString()} faces found{event.scanFailureCount ? ` · ${event.scanFailureCount} scan failures` : ''}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <label className="px-3 py-1.5 border border-chrome rounded font-mono text-xs uppercase tracking-wide cursor-pointer hover:border-safelight transition-colors">
                    {uploadingId === event.id ? `Processing ${uploadProgress}` : 'Upload photos'}
                    <input type="file" multiple accept="image/*" className="hidden" disabled={uploadingId === event.id} onChange={(e) => handleUpload(event.id, e.target.files)} />
                  </label>
                  <button onClick={() => deleteEvent(event)} className="px-3 py-1.5 border border-chrome rounded font-mono text-xs uppercase tracking-wide text-ash hover:border-safelight hover:text-safelight transition-colors">
                    Delete
                  </button>
                </div>
              </div>
              <SprocketStrip />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
