import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import UserDashboard from './components/UserDashboard'
import AdminDashboard from './components/AdminDashboard'
import Analytics from './components/Analytics'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <nav className="bg-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link to="/user" className="text-2xl font-bold text-indigo-600">
                  AI Feedback System
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link
                  to="/user"
                  className="px-4 py-2 text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition"
                >
                  User
                </Link>
                <Link
                  to="/admin"
                  className="px-4 py-2 text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition"
                >
                  Admin
                </Link>
                <Link
                  to="/user/analytics"
                  className="px-4 py-2 text-gray-700 hover:text-indigo-600 hover:bg-indigo-50 rounded-md transition"
                >
                  Analytics
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Navigate to="/user" replace />} />
          <Route path="/user" element={<UserDashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/analytics" element={<Analytics />} />
          <Route path="/user/analytics" element={<Analytics />} />
        </Routes>

        <footer className="mt-12 py-6 text-center text-sm text-gray-600">All Rights Reserved © 2025</footer>
      </div>
    </Router>
  )
}

export default App
