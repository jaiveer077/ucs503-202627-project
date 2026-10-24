import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { API_BASE } from '../config'
import { getAuth } from '../auth'

export default function EventDetail() {
  const { eventId } = useParams()
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')

  const { token, role } = getAuth()

  function handleFile(e) {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setPreview(URL.createObjectURL(f))
    }
  }

  async function handleSearch(e) {
    e.preventDefault()
    if (!file) {
      setError('Choose a reference photo first.')
      return
    }
    setError('')
    setSearching(true)

    const formData = new FormData()
    formData.append('reference', file)

    try {
      const res = await fetch(`${API_BASE}/api/user/events/${eventId}/search`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.error || 'Search failed.')
        setSearching(false)
        return
      }

      navigate(`/events/${eventId}/results`, {
        state: {
          matches: data.matches,
          checked: data.checked,
          totalPhotos: data.total_photos,
          closestConfidence: data.closest_confidence,
        },
      })
    } catch {
      setError('Could not reach the server. Is the backend running on port 5000?')
      setSearching(false)
    }
  }

  if (!token || role !== 'user') {
    return (
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <p className="text-ash mb-4">You need to be logged in as an attendee to search for your photos.</p>
        <Link to="/login" className="text-safelight hover:underline">Go to login</Link>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-14">
      <p className="font-mono text-xs uppercase tracking-widest text-safelight mb-2">This event</p>
      <h1 className="font-display text-4xl mb-2">Upload your reference photo</h1>
      <p className="text-ash text-sm mb-8">
        One clear, front-facing photo is enough. We'll compare it against every face detected in this event's photos.
      </p>

      <form onSubmit={handleSearch} className="space-y-6">
        <label className="block border-2 border-dashed border-chrome rounded-lg p-8 text-center cursor-pointer hover:border-safelight transition-colors">
          <input type="file" accept="image/*" onChange={handleFile} className="hidden" />
          {preview ? (
            <img src={preview} alt="Reference preview" className="mx-auto max-h-48 rounded" />
          ) : (
            <span className="font-mono text-xs uppercase tracking-wide text-ash">Click to choose a photo</span>
          )}
        </label>
        {error && <p className="text-sm text-safelight">{error}</p>}
        <button
          type="submit"
          disabled={searching}
          className="w-full py-3 bg-safelight rounded font-mono text-sm uppercase tracking-wide hover:bg-safelight-dim transition-colors disabled:opacity-60"
        >
          {searching ? 'Scanning…' : 'Find my photos'}
        </button>
      </form>
    </div>
  )
}
