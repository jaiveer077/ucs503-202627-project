import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './pages/Home'
import AuthForm from './pages/AuthForm'
import BrowseEvents from './pages/BrowseEvents'
import EventDetail from './pages/EventDetail'
import MatchedPhotos from './pages/MatchedPhotos'
import ManagerDashboard from './pages/ManagerDashboard'

export default function App() {
  return (
    <div className="min-h-screen bg-ink text-paper font-body">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<AuthForm role="user" mode="login" />} />
        <Route path="/register" element={<AuthForm role="user" mode="register" />} />
        <Route path="/manager/login" element={<AuthForm role="manager" mode="login" />} />
        <Route path="/manager/register" element={<AuthForm role="manager" mode="register" />} />
        <Route path="/events" element={<BrowseEvents />} />
        <Route path="/events/:eventId" element={<EventDetail />} />
        <Route path="/events/:eventId/results" element={<MatchedPhotos />} />
        <Route path="/manager/dashboard" element={<ManagerDashboard />} />
      </Routes>
    </div>
  )
}
