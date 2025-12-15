import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

function AdminDashboard() {
  const navigate = useNavigate()
  const [submissions, setSubmissions] = useState([])
  const [filteredSubmissions, setFilteredSubmissions] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const isFetchingRef = useRef(false)

  const [ratingFilter, setRatingFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('')

  const [expandedSections, setExpandedSections] = useState({})

  const toggleSection = (submissionId, section) => {
    const key = `${submissionId}-${section}`
    setExpandedSections((prev) => ({
      ...prev,
      [key]: !prev[key],
    }))
  }

  const fetchData = async () => {
    if (isFetchingRef.current) return
    isFetchingRef.current = true
    try {
      setError(null)
      const params = {}
      if (ratingFilter !== 'all') params.rating = parseInt(ratingFilter)
      if (dateFilter) params.date = dateFilter

      const [submissionsRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/submissions`, { params, timeout: 15000 }),
        axios.get(`${API_BASE_URL}/api/stats`, { timeout: 15000 }),
      ])

      const list = submissionsRes.data || []
      setSubmissions(list)
      setFilteredSubmissions(list)
      setStats(statsRes.data)
    } catch (err) {
      let errorMsg = 'Failed to load data'
      if (err?.response) {
        if (err.response.status === 404) {
          errorMsg = 'Endpoint not found (404). Please ensure the backend server is running and the API endpoints are available.'
        } else if (err.response.status === 500) {
          errorMsg = 'Server error. Please check backend logs.'
        } else {
          errorMsg = err.response.data?.detail || `Error ${err.response.status}: ${err.response.statusText}`
        }
      } else if (err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'))) {
        errorMsg = 'Request timed out: backend did not respond within 15s. Please try again later.'
      } else if (err?.request) {
        errorMsg = `Network error: Cannot connect to backend at ${API_BASE_URL}. Please ensure the backend server is running.`
      } else {
        errorMsg = err?.message || 'Failed to load data'
      }
      setError(errorMsg)
    } finally {
      setLoading(false)
      isFetchingRef.current = false
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [ratingFilter, dateFilter])

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getRatingColor = (rating) => {
    if (rating >= 4) return 'text-green-600 bg-green-100'
    if (rating === 3) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getPredictionStatus = (actual, predicted) => {
    if (predicted === null || predicted === undefined || predicted === '') {
      return { status: 'neutral', text: 'No prediction', color: 'gray', icon: '➖', message: 'No AI prediction available' }
    }

    const p = Number(predicted)
    const a = Number(actual)
    if (!Number.isFinite(p) || !Number.isFinite(a)) {
      return { status: 'neutral', text: 'No prediction', color: 'gray', icon: '➖', message: 'No AI prediction available' }
    }

    const diff = p - a
    if (diff > 0) {
      return { status: 'improvement', text: `+${diff} (AI higher)`, color: 'green', icon: '📈', message: 'AI predicted higher than user rating' }
    }
    if (diff < 0) {
      return { status: 'concern', text: `${diff} (AI lower)`, color: 'red', icon: '📉', message: 'AI predicted lower than user rating' }
    }
    return { status: 'match', text: '0 (Match)', color: 'blue', icon: '✅', message: 'AI prediction matches user rating' }
  }

  const getScoreDifference = (actual, predicted) => {
    if (predicted === null || predicted === undefined || predicted === '') return null
    const p = Number(predicted)
    const a = Number(actual)
    if (!Number.isFinite(p) || !Number.isFinite(a)) return null

    const diff = p - a
    if (diff > 0) return { label: `+${diff} (AI higher)`, tone: 'positive' }
    if (diff < 0) return { label: `${diff} (AI lower)`, tone: 'negative' }
    return { label: '0 (Match)', tone: 'match' }
  }

  const getFilterMessage = () => {
    if (ratingFilter !== 'all' && filteredSubmissions.length === 0) {
      const starText = ratingFilter === '1' ? 'star' : 'stars'
      return {
        message: `😔 Sorry, no ${ratingFilter}-${starText} review${ratingFilter !== '1' ? 's' : ''} ${dateFilter ? `submitted on ${dateFilter}` : 'submitted in the system'}. Please try selecting a different rating or clear the filter to see all reviews.`,
        emoji: '⭐',
      }
    }
    if (dateFilter && filteredSubmissions.length === 0 && ratingFilter === 'all') {
      return {
        message: `📅 Sorry, no reviews submitted on ${dateFilter}. Please try selecting a different date or clear the filter to see all reviews.`,
        emoji: '📅',
      }
    }
    if (dateFilter && ratingFilter !== 'all' && filteredSubmissions.length === 0) {
      const starText = ratingFilter === '1' ? 'star' : 'stars'
      return {
        message: `😔 Sorry, no ${ratingFilter}-${starText} review${ratingFilter !== '1' ? 's' : ''} submitted on ${dateFilter}. Please try adjusting your filters.`,
        emoji: '🔍',
      }
    }
    return null
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-600">Loading...</div>
        </div>
      </div>
    )
  }

  if (error && !submissions.length) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
          <strong>Error:</strong> {error}
        </div>
        <button onClick={fetchData} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6 bg-white rounded-lg shadow-lg px-4 py-3 flex items-center justify-between">
        <div className="font-bold text-indigo-600">Admin Panel</div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition"
          >
            All Reviews
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin/analytics')}
            className="px-4 py-2 bg-white text-gray-700 rounded-md border border-gray-200 hover:bg-gray-50 transition"
          >
            Analytics
          </button>
        </div>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Admin Dashboard</h1>
        <p className="text-gray-600">Default: show all reviews with filters and AI insights</p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="text-sm text-gray-600 mb-1">Total Reviews</div>
            <div className="text-3xl font-bold text-indigo-600">{stats.total_reviews}</div>
          </div>
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="text-sm text-gray-600 mb-1">Average Rating</div>
            <div className="text-3xl font-bold text-yellow-600">{stats.average_rating.toFixed(2)} ⭐</div>
          </div>
          <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="text-sm text-gray-600 mb-1">Latest Update</div>
            <div className="text-sm font-semibold text-gray-800">
              {submissions.length > 0 ? formatDate(submissions[0].timestamp) : 'No submissions'}
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Rating</label>
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="all">All Ratings</option>
              <option value="1">1 Star</option>
              <option value="2">2 Stars</option>
              <option value="3">3 Stars</option>
              <option value="4">4 Stars</option>
              <option value="5">5 Stars</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Date</label>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        {(ratingFilter !== 'all' || dateFilter) && (
          <button
            onClick={() => {
              setRatingFilter('all')
              setDateFilter('')
            }}
            className="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            Clear Filters
          </button>
        )}
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">{error}</div>}

      <div className="mb-6 flex justify-end">
        <button
          onClick={fetchData}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition flex items-center space-x-2"
        >
          <span>🔄</span>
          <span>Refresh Data</span>
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="px-6 py-4 bg-indigo-600 text-white">
          <h2 className="text-xl font-bold">All Reviews {filteredSubmissions.length > 0 && `(${filteredSubmissions.length})`}</h2>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: '600px' }}>
          {getFilterMessage() && (
            <div className="p-8 text-center">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl px-8 py-6 inline-block shadow-lg max-w-2xl">
                <div className="text-5xl mb-3">{getFilterMessage().emoji}</div>
                <p className="text-lg font-semibold text-gray-800 leading-relaxed">{getFilterMessage().message}</p>
                <button
                  onClick={() => {
                    setRatingFilter('all')
                    setDateFilter('')
                  }}
                  className="mt-4 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                >
                  Clear Filters & View All Reviews
                </button>
              </div>
            </div>
          )}

          {filteredSubmissions.length === 0 && !getFilterMessage() ? (
            <div className="p-8 text-center text-gray-500">No submissions yet. Reviews will appear here once users submit them.</div>
          ) : filteredSubmissions.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {filteredSubmissions.map((submission) => {
                const predictionStatus = getPredictionStatus(submission.rating, submission.predicted_stars)
                const diffBadge = getScoreDifference(submission.rating, submission.predicted_stars)

                const summaryKey = `${submission.id}-summary`
                const actionsKey = `${submission.id}-actions`
                const isSummaryExpanded = expandedSections[summaryKey]
                const isActionsExpanded = expandedSections[actionsKey]

                return (
                  <div key={submission.id} className="p-6 hover:bg-gray-50 transition">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center space-x-4 flex-wrap gap-2">
                        <div className="flex items-center space-x-2 bg-gray-50 px-3 py-2 rounded-lg border border-gray-200">
                          <span className="text-sm font-semibold text-gray-700">User Rating:</span>
                          <div className={`px-3 py-1 rounded-full font-bold ${getRatingColor(submission.rating)}`}>{submission.rating} ⭐</div>
                        </div>

                        <div className="flex items-center space-x-2 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200">
                          <span className="text-sm font-semibold text-gray-700">AI Predicted:</span>
                          {submission.predicted_stars !== null && submission.predicted_stars !== undefined && submission.predicted_stars !== '' ? (
                            <div
                              className={`px-3 py-1 rounded-full font-bold ${
                                predictionStatus.color === 'green'
                                  ? 'bg-green-100 text-green-700'
                                  : predictionStatus.color === 'red'
                                    ? 'bg-red-100 text-red-700'
                                    : predictionStatus.color === 'gray'
                                      ? 'bg-gray-100 text-gray-600'
                                      : 'bg-blue-100 text-blue-700'
                              }`}
                            >
                              {submission.predicted_stars} ⭐
                            </div>
                          ) : (
                            <div className="px-3 py-1 rounded-full font-bold bg-gray-100 text-gray-500">N/A</div>
                          )}
                        </div>

                        {diffBadge && (
                          <div
                            className={`px-3 py-1 rounded-lg font-semibold text-sm border ${
                              diffBadge.tone === 'positive'
                                ? 'bg-green-50 text-green-700 border-green-200'
                                : diffBadge.tone === 'negative'
                                  ? 'bg-red-50 text-red-700 border-red-200'
                                  : 'bg-blue-50 text-blue-700 border-blue-200'
                            }`}
                          >
                            {diffBadge.label}
                          </div>
                        )}

                        <div>
                          <div className="text-sm text-gray-500">{formatDate(submission.timestamp)}</div>
                          <div className="text-xs text-gray-400">ID: {submission.id}</div>
                        </div>
                      </div>

                      <div
                        className={`px-3 py-1 rounded-lg text-sm font-semibold ${
                          predictionStatus.color === 'green'
                            ? 'bg-green-50 text-green-700 border border-green-200'
                            : predictionStatus.color === 'red'
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : predictionStatus.color === 'gray'
                                ? 'bg-gray-50 text-gray-700 border border-gray-200'
                                : 'bg-blue-50 text-blue-700 border border-blue-200'
                        }`}
                      >
                        <span className="mr-1">{predictionStatus.icon}</span>
                        {predictionStatus.text}
                      </div>
                    </div>

                    <div className="mb-4">
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">User Review</h3>
                      <div className="bg-gray-50 p-3 rounded-lg max-h-32 overflow-y-auto">
                        <p className="text-gray-800">{submission.review_text}</p>
                      </div>
                    </div>

                    <div className="mb-4">
                      <button
                        onClick={() => toggleSection(submission.id, 'summary')}
                        className="w-full flex items-center justify-between text-sm font-semibold text-gray-700 mb-2 p-2 hover:bg-gray-100 rounded-lg transition"
                      >
                        <span className="flex items-center">
                          <span className="mr-2">🤖</span> AI Summary
                        </span>
                        <span className="text-gray-500">{isSummaryExpanded ? '▼' : '▶'}</span>
                      </button>
                      {isSummaryExpanded && (
                        <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 max-h-40 overflow-y-auto">
                          <p className="text-gray-700 whitespace-pre-line">{submission.ai_summary}</p>
                        </div>
                      )}
                    </div>

                    <div>
                      <button
                        onClick={() => toggleSection(submission.id, 'actions')}
                        className="w-full flex items-center justify-between text-sm font-semibold text-gray-700 mb-2 p-2 hover:bg-gray-100 rounded-lg transition"
                      >
                        <span className="flex items-center">
                          <span className="mr-2">💡</span> AI Recommendations
                        </span>
                        <span className="text-gray-500">{isActionsExpanded ? '▼' : '▶'}</span>
                      </button>
                      {isActionsExpanded && (
                        <div className="bg-yellow-50 p-3 rounded-lg border border-yellow-200 max-h-60 overflow-y-auto">
                          <p className="text-gray-700 whitespace-pre-line">{submission.ai_recommended_actions}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard
