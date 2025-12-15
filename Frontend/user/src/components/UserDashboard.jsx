import { useState } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

 function setCookie(name, value, maxAgeSeconds = 60 * 60 * 24 * 7) {
   try {
     document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`
   } catch {
     // ignore cookie errors
   }
 }

 function getCookie(name) {
   try {
     const key = `${encodeURIComponent(name)}=`
     const parts = document.cookie.split(';').map((p) => p.trim())
     for (const p of parts) {
       if (p.startsWith(key)) return decodeURIComponent(p.slice(key.length))
     }
   } catch {
     // ignore cookie errors
   }
   return null
 }

 function deleteCookie(name) {
   try {
     document.cookie = `${encodeURIComponent(name)}=; Max-Age=0; Path=/; SameSite=Lax`
   } catch {
     // ignore cookie errors
   }
 }

function renderHighlightedSummary(text) {
  const safeText = String(text || '')
  const parts = safeText.split(/(\*\*[^*]+\*\*)/g)

  return parts.map((part, index) => {
    const match = part.match(/^\*\*(.+)\*\*$/)
    if (match) {
      return (
        <strong key={index} className="font-semibold text-indigo-700">
          {match[1]}
        </strong>
      )
    }
    return <span key={index}>{part}</span>
  })
}

function getRatingDiffInfo(resp) {
  if (!resp) return null

  const actual = Number(resp.rating)
  const hasPredicted =
    resp.predicted_stars !== null &&
    resp.predicted_stars !== undefined &&
    resp.predicted_stars !== ''
  if (!hasPredicted) return null

  const predicted = Number(resp.predicted_stars)
  if (!Number.isFinite(actual) || !Number.isFinite(predicted)) return null

  const diff = predicted - actual
  if (diff > 0) {
    return {
      diff,
      label: `+${diff} (AI higher)`,
      description: 'AI predicted a higher rating than you selected.',
    }
  }
  if (diff < 0) {
    return {
      diff,
      label: `${diff} (AI lower)`,
      description: 'AI predicted a lower rating than you selected.',
    }
  }
  return {
    diff: 0,
    label: '0 (Match)',
    description: 'AI prediction matches your rating.',
  }
}

function UserDashboard() {
  const [rating, setRating] = useState(0)
  const [reviewText, setReviewText] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(() => {
    const savedResponse = localStorage.getItem('lastAiResponse')
    if (savedResponse) return JSON.parse(savedResponse)

    const cookieResponse = getCookie('lastAiResponse')
    if (cookieResponse) {
      try {
        const parsed = JSON.parse(cookieResponse)
        localStorage.setItem('lastAiResponse', JSON.stringify(parsed))
        return parsed
      } catch {
        return null
      }
    }

    return null
  })
  const [error, setError] = useState(null)
  const [isPolling, setIsPolling] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  const isBusy = loading || isPolling || isGenerating
  const hasCompletedResponse = !!(
    response &&
    !(response.status === 'processing') &&
    !(typeof response.ai_response === 'string' && response.ai_response.toLowerCase().includes('processing'))
  )

  const ratingDiffInfo = getRatingDiffInfo(response)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (rating === 0) {
      setError('Please select a rating')
      return
    }

    if (!reviewText.trim()) {
      setError('Please write a review')
      return
    }

    setLoading(true)
    setIsGenerating(true)
    setError(null)

    const tempResponse = {
      id: `temp_${Date.now()}`,
      rating,
      review_text: reviewText,
      ai_response: 'Generating your personalized response...',
      ai_summary: 'Analyzing your feedback...',
      status: 'processing',
      timestamp: new Date().toISOString(),
    }
    setResponse(tempResponse)
    try {
      localStorage.setItem('lastAiResponse', JSON.stringify(tempResponse))
      setCookie('lastAiResponse', JSON.stringify(tempResponse))
    } catch {
      // ignore storage errors
    }

    try {
      const res = await axios.post(
        `${API_BASE_URL}/api/submit-review`,
        {
          rating,
          review_text: reviewText,
        },
        {
          timeout: 60000,
        },
      )

      const updatedResponse = {
        ...res.data,
        ai_response:
          res.data.status === 'processing' ? 'Generating your personalized response...' : res.data.ai_response,
        ai_summary: res.data.status === 'processing' ? 'Analyzing your feedback...' : res.data.ai_summary,
      }

      setResponse(updatedResponse)
      setError(null)

      if (updatedResponse.status && updatedResponse.status !== 'processing') {
        setIsGenerating(false)
        setIsPolling(false)
        setReviewText('')
        setRating(0)
      }

      localStorage.setItem('lastAiResponse', JSON.stringify(updatedResponse))
      setCookie('lastAiResponse', JSON.stringify(updatedResponse))

      // Previously we started a long polling loop here to wait for a slower
      // AI completion. The backend now returns a complete AI pack instantly
      // (and refines it in the background), so we no longer need to poll.
    } catch (err) {
      setIsGenerating(false)
      setIsPolling(false)

      let errorMsg = 'Failed to submit review. Please try again.'
      if (err.response) {
        if (err.response.status === 404) {
          errorMsg = 'Endpoint not found (404). Please ensure the backend server is running.'
        } else if (err.response.status === 500) {
          errorMsg = 'Server error. Please check backend logs and try again later.'
        } else if (err.response.status === 400) {
          errorMsg = err.response.data?.detail || 'Invalid request. Please check your input and try again.'
        } else {
          errorMsg = err.response.data?.detail || `Error ${err.response.status}: ${err.response.statusText}`
        }
      } else if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
        errorMsg = 'Request timed out: backend did not respond within 60s. Please try again later.'
      } else if (err.request) {
        errorMsg = `Network error: Cannot connect to backend at ${API_BASE_URL}. Please ensure the backend server is running.`
      } else {
        errorMsg = err.message || 'Failed to submit review. Please try again.'
      }
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleWriteAnother = () => {
    setResponse(null)
    setError(null)
    setIsGenerating(false)
    setIsPolling(false)
    setLoading(false)
    setRating(0)
    setReviewText('')
    localStorage.removeItem('lastAiResponse')
    deleteCookie('lastAiResponse')
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {isBusy && (
        <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" />
          <div className="relative bg-white rounded-xl shadow-2xl p-8 w-[min(420px,90vw)] pointer-events-auto">
            <div className="flex flex-col items-center">
              <div className="w-14 h-14 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="mt-4 text-gray-800 font-semibold text-center">AI is generating your personalized response...</p>
              <p className="mt-1 text-sm text-gray-500 text-center">
                Please wait a moment while we analyze your review.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className={`bg-white rounded-lg shadow-xl p-8 transition ${isBusy ? 'blur-sm' : ''}`}>
        <div className="flex justify-between items-start mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Submit Your Review</h1>
            <p className="text-gray-600">Share your experience and get an AI-powered response</p>
          </div>
          <div className="flex items-center gap-4">
            {response && !isPolling && (
              <div className="text-sm text-gray-500">
                Last updated: {new Date(response.submitted_at || new Date()).toLocaleString()}
              </div>
            )}
          </div>
        </div>

        {!hasCompletedResponse && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">Rating *</label>
              <div className="flex space-x-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    className={`w-12 h-12 rounded-full text-2xl transition-all transform hover:scale-110 ${
                      rating >= star ? 'bg-yellow-400 text-yellow-900' : 'bg-gray-200 text-gray-400 hover:bg-gray-300'
                    }`}
                  >
                    ⭐
                  </button>
                ))}
              </div>
              {rating > 0 && (
                <p className="mt-2 text-sm text-gray-600">
                  Selected: {rating} {rating === 1 ? 'star' : 'stars'}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="review" className="block text-sm font-medium text-gray-700 mb-2">
                Your Review *
              </label>
              <textarea
                id="review"
                rows="6"
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Share your thoughts about your experience..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              />
              <p className="mt-1 text-sm text-gray-500">{reviewText.length} characters</p>
            </div>

            {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>}

            <button
              type="submit"
              disabled={isBusy}
              className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition ${
                isBusy ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 transform hover:scale-105'
              }`}
            >
              {isBusy ? 'Generating...' : 'Submit Review'}
            </button>

            {(isPolling || isGenerating) && <p className="text-center text-sm text-gray-500">AI Response generating... please wait.</p>}
          </form>
        )}

        {response && (
          <div className="mt-8 p-6 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-800 flex items-center">
                <span className="mr-2">🤖</span> AI Response
              </h2>
              {hasCompletedResponse && (
                <button type="button" onClick={handleWriteAnother} className="text-sm text-indigo-600 hover:text-indigo-800">
                  Add New Review
                </button>
              )}
            </div>

            <div className="space-y-5">
              {ratingDiffInfo && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="bg-white/60 rounded-lg border border-gray-200 p-3">
                    <div className="text-xs text-gray-500">Your Rating</div>
                    <div className="text-lg font-semibold text-gray-800">{response.rating} ⭐</div>
                  </div>
                  <div className="bg-white/60 rounded-lg border border-blue-200 p-3">
                    <div className="text-xs text-gray-500">AI Predicted</div>
                    <div className="text-lg font-semibold text-blue-700">{response.predicted_stars} ⭐</div>
                  </div>
                  <div className="bg-white/60 rounded-lg border border-indigo-200 p-3">
                    <div className="text-xs text-gray-500">Difference</div>
                    <div className="text-lg font-semibold text-indigo-700">{ratingDiffInfo.label}</div>
                    <div className="text-xs text-gray-500">{ratingDiffInfo.description}</div>
                  </div>
                </div>
              )}

              <div className="bg-white/60 rounded-lg border border-indigo-100 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">AI Summary</h3>
                {(isPolling || isGenerating || response.status === 'processing') ? (
                  <div className="text-gray-700">
                    <div className="flex items-center space-x-3">
                      <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <p className="line-clamp-3 sm:line-clamp-none max-h-24 sm:max-h-40 overflow-y-auto">
                        {response.ai_summary || 'Analyzing your feedback...'}
                      </p>
                    </div>
                  </div>
                ) : response.ai_summary ? (
                  <div className="text-gray-700 whitespace-pre-line max-h-40 overflow-y-auto">
                    {renderHighlightedSummary(response.ai_summary)}
                  </div>
                ) : (
                  <div className="text-gray-500 italic">No AI summary available.</div>
                )}
              </div>

              <div className="bg-white/60 rounded-lg border border-indigo-100 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">AI Response</h3>
                {(isPolling || isGenerating || response.status === 'processing') ? (
                  <div className="text-gray-700">
                    <div className="flex items-center space-x-3">
                      <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <p>AI Response generating...</p>
                    </div>
                  </div>
                ) : response.ai_response ? (
                  <div className="prose max-w-none text-gray-700">
                    {String(response.ai_response)
                      .split('\n')
                      .map((paragraph, i) => (
                        <p key={i} className="mb-4 last:mb-0">
                          {paragraph}
                        </p>
                      ))}
                  </div>
                ) : (
                  <div className="text-gray-500 italic">No AI response available yet. Please check back later.</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default UserDashboard
