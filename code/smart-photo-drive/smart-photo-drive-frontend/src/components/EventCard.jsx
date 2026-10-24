import { Link } from 'react-router-dom'
import SprocketStrip from './SprocketStrip'

export default function EventCard({ event }) {
  return (
    <Link to={`/events/${event.id}`} className="block bg-paper text-ink rounded-lg overflow-hidden group">
      <SprocketStrip />
      <div className="aspect-[4/3] overflow-hidden bg-paper-dim flex items-center justify-center">
        {event.cover ? (
          <img
            src={event.cover}
            alt=""
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <span className="font-mono text-xs uppercase tracking-widest text-ink/40">No photos yet</span>
        )}
      </div>
      <SprocketStrip />
      <div className="p-4">
        <h3 className="font-display text-xl leading-none mb-1">{event.name}</h3>
        <p className="font-mono text-xs text-ink/60 mb-2">{event.date || 'Date TBD'} &middot; {event.location || 'Location TBD'}</p>
        <p className="font-mono text-xs text-safelight-dim">{event.photoCount.toLocaleString()} photos uploaded</p>
      </div>
    </Link>
  )
}
