import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { API_BASE } from '../config'
import { saveAuth } from '../auth'

export default function AuthForm({ role, mode }) {
  const navigate = useNavigate()
  const isRegister = mode === 'register'
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.email || !form.password || (isRegister && !form.name)) {
      setError('Fill in every field first.')
      return
    }
    setError('')
    setSubmitting(true)

    const path = `/api/${role}/${isRegister ? 'register' : 'login'}`
    const body = isRegister
      ? { name: form.name, email: form.email, password: form.password }
      : { email: form.email, password: form.password }

    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.error || 'Something went wrong.')
        setSubmitting(false)
        return
      }

      saveAuth(data)

      navigate(role === 'manager' ? '/manager/dashboard' : '/events')
    } catch {
      setError('Could not reach the server. Is the backend running on port 5000?')
      setSubmitting(false)
    }
  }

  const roleLabel = role === 'manager' ? 'Event manager' : 'Attendee'

  return (
    <div className="max-w-md mx-auto px-6 py-20">
      <p className="font-mono text-xs uppercase tracking-widest text-safelight mb-2">{roleLabel} account</p>
      <h1 className="font-display text-4xl mb-8">{isRegister ? 'Create account' : 'Log in'}</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        {isRegister && (
          <div>
            <label className="block font-mono text-xs uppercase text-ash mb-1">Full name</label>
            <input value={form.name} onChange={update('name')} className="w-full bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" type="text" />
          </div>
        )}
        <div>
          <label className="block font-mono text-xs uppercase text-ash mb-1">Email</label>
          <input value={form.email} onChange={update('email')} className="w-full bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" type="email" />
        </div>
        <div>
          <label className="block font-mono text-xs uppercase text-ash mb-1">Password</label>
          <input value={form.password} onChange={update('password')} className="w-full bg-ink-soft border border-chrome rounded px-3 py-2 text-paper focus:outline-none focus:border-safelight" type="password" />
        </div>
        {error && <p className="text-sm text-safelight">{error}</p>}
        <button type="submit" disabled={submitting} className="w-full py-3 bg-safelight rounded font-mono text-sm uppercase tracking-wide hover:bg-safelight-dim transition-colors disabled:opacity-60">
          {submitting ? 'Please wait…' : isRegister ? 'Create account' : 'Log in'}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-ash">
        {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
        <Link
          to={
            role === 'manager'
              ? isRegister ? '/manager/login' : '/manager/register'
              : isRegister ? '/login' : '/register'
          }
          className="text-safelight hover:underline"
        >
          {isRegister ? 'Log in' : 'Register'}
        </Link>
      </p>
    </div>
  )
}
