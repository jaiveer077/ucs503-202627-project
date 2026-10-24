import { Link } from 'react-router-dom'
import SprocketStrip from '../components/SprocketStrip'

export default function Home() {
  return (
    <div>
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-safelight mb-4">Face-based photo retrieval</p>
        <h1 className="font-display text-5xl md:text-7xl leading-[0.95] mb-6">FIND YOURSELF<br />IN THE CROWD</h1>
        <p className="text-ash max-w-xl mx-auto mb-10">Upload one photo of your face. We search the event collection and show photos likely to include you, so you can find your pictures faster.</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/events" className="px-6 py-3 bg-safelight text-paper rounded font-mono text-sm uppercase tracking-wide hover:bg-safelight-dim transition-colors">I'm attending an event</Link>
          <Link to="/manager/login" className="px-6 py-3 border border-chrome text-paper rounded font-mono text-sm uppercase tracking-wide hover:border-paper transition-colors">I'm an event manager</Link>
        </div>
      </section>
      <SprocketStrip />
      <section className="max-w-6xl mx-auto px-6 py-14 grid sm:grid-cols-3 gap-8">
        {[
          ['01', 'Upload the roll', "An event manager uploads the full photo collection after the event."],
          ['02', 'Give us your face', "You provide one clear reference photo — that's the only input we need."],
          ['03', 'Get your frames', 'Dlib-based face matching returns likely photos, ranked by a display match score.'],
        ].map(([n, title, body]) => (
          <div key={n}>
            <p className="font-mono text-safelight text-sm mb-2">{n}</p>
            <h3 className="font-display text-2xl mb-2">{title}</h3>
            <p className="text-ash text-sm">{body}</p>
          </div>
        ))}
      </section>
      <SprocketStrip />
    </div>
  )
}
