import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getAuth, clearAuth } from '../auth'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const [, refresh] = useState(0)
  const { token, role, name } = getAuth()
  const loggedIn = Boolean(token)

  function logout() {
    clearAuth()
    refresh((n) => n + 1) // re-read login state even if the route doesn't change
    navigate('/')
  }

  // Attendees (and guests) browse events; managers get their own dashboard.
  const links =
    role === 'manager'
      ? [{ to: '/manager/dashboard', label: 'My events' }]
      : [{ to: '/events', label: 'Events' }]

  return (
    <header className="bg-ink-soft border-b border-chrome">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-safelight inline-block" />
          <span className="font-mono text-sm tracking-widest text-paper uppercase">Smart Photo Drive</span>
        </Link>
        <nav className="flex items-center gap-6 font-mono text-xs uppercase tracking-wider">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className={location.pathname === l.to ? 'text-safelight' : 'text-ash hover:text-paper transition-colors'}
            >
              {l.label}
            </Link>
          ))}
          {loggedIn ? (
            <>
              <span className="text-ash normal-case tracking-normal hidden sm:inline">
                {name} ({role === 'manager' ? 'manager' : 'attendee'})
              </span>
              <button
                onClick={logout}
                className="px-3 py-1.5 border border-chrome rounded text-paper hover:border-safelight transition-colors uppercase"
              >
                Log out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="px-3 py-1.5 border border-chrome rounded text-paper hover:border-safelight transition-colors"
            >
              Log in
            </Link>
          )}
        </nav>
      </div>
    </header>
  )
}
