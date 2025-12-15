import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Bar, Line, Radar, Doughnut } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
)

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

function Analytics() {
  const navigate = useNavigate()
  const [analyticsData, setAnalyticsData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [dateRange, setDateRange] = useState('all')
  const [ratingFilter, setRatingFilter] = useState('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = {}
      if (dateRange && dateRange !== 'all') params.date_range = dateRange
      if (ratingFilter && ratingFilter !== 'all') params.rating = parseInt(ratingFilter)
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate

      const response = await axios.get(`${API_BASE_URL}/api/analytics`, {
        params,
        timeout: 60000,
      })

      if (!response.data) throw new Error('No data received from server')

      const processedData = {
        total_reviews: response.data.total_reviews || 0,
        average_rating: response.data.average_rating || 0,
        rating_distribution: response.data.rating_distribution || { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0 },
        trends_over_time: response.data.trends_over_time || { labels: [], data: [] },
        radar_analysis: response.data.radar_analysis || {
          service_quality: 0,
          food_quality: 0,
          value_for_money: 0,
          ambience: 0,
          overall_satisfaction: 0,
          response_time: 0,
        },
        prediction_comparison: response.data.prediction_comparison || { matches: 0, ai_higher: 0, ai_lower: 0 },
        positive_reviews: response.data.positive_reviews || 0,
        positive_percentage: response.data.positive_percentage || 0,
        ai_accuracy:
          response.data.ai_accuracy !== undefined && response.data.ai_accuracy !== null ? response.data.ai_accuracy : null,
        insights: response.data.insights || [],
      }

      setAnalyticsData(processedData)
    } catch (err) {
      let errorMsg = 'Failed to load analytics'
      if (err?.response) {
        if (err.response.status === 404) {
          errorMsg = 'Endpoint /api/analytics not found (404). Please ensure the backend server is running.'
        } else if (err.response.status === 500) {
          errorMsg = 'Server error. Please check backend logs and try again later.'
        } else if (err.response.status === 400) {
          errorMsg = err.response.data?.detail || 'Invalid request. Please check your filters and try again.'
        } else {
          errorMsg = err.response.data?.detail || `Error ${err.response.status}: ${err.response.statusText}`
        }
      } else if (err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'))) {
        errorMsg = 'Request timed out: backend did not respond within 60s. Please try again later.'
      } else if (err?.request) {
        errorMsg = `Network error: Cannot connect to backend at ${API_BASE_URL}. Please ensure the backend server is running.`
      } else {
        errorMsg = err?.message || 'Failed to load analytics'
      }

      setError(errorMsg)
      setAnalyticsData({
        total_reviews: 0,
        average_rating: 0,
        rating_distribution: { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0 },
        trends_over_time: { labels: [], data: [] },
        radar_analysis: {
          service_quality: 0,
          food_quality: 0,
          value_for_money: 0,
          ambience: 0,
          overall_satisfaction: 0,
          response_time: 0,
        },
        prediction_comparison: { matches: 0, ai_higher: 0, ai_lower: 0 },
        positive_reviews: 0,
        positive_percentage: 0,
        ai_accuracy: null,
        insights: ['Unable to load analytics data. Please check your connection and try again.'],
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [dateRange, ratingFilter, startDate, endDate])

  const data =
    analyticsData ||
    ({
      total_reviews: 0,
      average_rating: 0,
      rating_distribution: { '1': 0, '2': 0, '3': 0, '4': 0, '5': 0 },
      trends_over_time: { labels: [], data: [] },
      radar_analysis: {
        service_quality: 0,
        food_quality: 0,
        value_for_money: 0,
        ambience: 0,
        overall_satisfaction: 0,
        response_time: 0,
      },
      prediction_comparison: { matches: 0, ai_higher: 0, ai_lower: 0 },
      positive_reviews: 0,
      positive_percentage: 0,
      ai_accuracy: null,
      insights: [],
    })

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-600">Loading analytics...</div>
        </div>
      </div>
    )
  }

  const ratingBarData = {
    labels: ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars'],
    datasets: [
      {
        label: 'Number of Reviews',
        data: [
          data.rating_distribution?.['1'] || 0,
          data.rating_distribution?.['2'] || 0,
          data.rating_distribution?.['3'] || 0,
          data.rating_distribution?.['4'] || 0,
          data.rating_distribution?.['5'] || 0,
        ],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(251, 191, 36, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(16, 185, 129, 0.8)',
        ],
        borderColor: [
          'rgba(239, 68, 68, 1)',
          'rgba(245, 158, 11, 1)',
          'rgba(251, 191, 36, 1)',
          'rgba(34, 197, 94, 1)',
          'rgba(16, 185, 129, 1)',
        ],
        borderWidth: 2,
      },
    ],
  }

  const timeLineData = {
    labels: data.trends_over_time?.labels || [],
    datasets: [
      {
        label: 'Reviews Count',
        data: data.trends_over_time?.data || [],
        borderColor: 'rgba(99, 102, 241, 1)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        borderWidth: 3,
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointHoverRadius: 7,
      },
    ],
  }

  const radarData = {
    labels: ['Service Quality', 'Food Quality', 'Value for Money', 'Ambience', 'Overall Satisfaction', 'Response Time'],
    datasets: [
      {
        label: 'Average Score',
        data: [
          data.radar_analysis?.service_quality || 0,
          data.radar_analysis?.food_quality || 0,
          data.radar_analysis?.value_for_money || 0,
          data.radar_analysis?.ambience || 0,
          data.radar_analysis?.overall_satisfaction || 0,
          data.radar_analysis?.response_time || 0,
        ],
        backgroundColor: 'rgba(139, 92, 246, 0.2)',
        borderColor: 'rgba(139, 92, 246, 1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(139, 92, 246, 1)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(139, 92, 246, 1)',
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: false,
      },
    },
  }

  const matches = data.prediction_comparison?.matches || 0
  const aiHigher = data.prediction_comparison?.ai_higher || 0
  const aiLower = data.prediction_comparison?.ai_lower || 0
  const totalComparisons = matches + aiHigher + aiLower

  const comparisonData = {
    labels: ['Matches', 'AI Predicted Higher', 'AI Predicted Lower'],
    datasets: [
      {
        data: [matches, aiHigher, aiLower],
        backgroundColor: ['rgba(34, 197, 94, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(239, 68, 68, 0.8)'],
        borderColor: ['rgba(34, 197, 94, 1)', 'rgba(59, 130, 246, 1)', 'rgba(239, 68, 68, 1)'],
        borderWidth: 2,
      },
    ],
  }

  const doughnutOptions = {
    ...chartOptions,
    plugins: {
      ...chartOptions.plugins,
      tooltip: {
        callbacks: {
          label: function (context) {
            const label = context.label || ''
            const value = context.parsed || 0
            const total = context.dataset.data.reduce((a, b) => a + b, 0)
            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0
            return `${label}: ${value} (${percentage}%)`
          },
        },
      },
    },
  }

  const radarOptions = {
    ...chartOptions,
    scales: {
      r: {
        beginAtZero: true,
        max: 5,
        ticks: {
          stepSize: 1,
        },
      },
    },
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6 bg-white rounded-lg shadow-lg px-4 py-3 flex items-center justify-between">
        <div className="font-bold text-indigo-600">Admin Panel</div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate('/admin')}
            className="px-4 py-2 bg-white text-gray-700 rounded-md border border-gray-200 hover:bg-gray-50 transition"
          >
            All Reviews
          </button>
          <button
            type="button"
            onClick={() => navigate('/admin/analytics')}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition"
          >
            Analytics
          </button>
        </div>
      </div>

      <div className="mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Analytics Dashboard</h1>
          <p className="text-gray-600">Comprehensive insights and trends analysis</p>
        </div>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-6">
          <strong>Warning:</strong> {error} - Charts are showing with available data.
        </div>
      )}

      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="all">All Time</option>
              <option value="week">Last Week</option>
              <option value="month">Last Month</option>
              <option value="year">Last Year</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>

          {dateRange === 'custom' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Rating Filter</label>
            <select
              value={ratingFilter}
              onChange={(e) => setRatingFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="all">All Ratings</option>
              <option value="1">1 Star</option>
              <option value="2">2 Stars</option>
              <option value="3">3 Stars</option>
              <option value="4">4 Stars</option>
              <option value="5">5 Stars</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="text-sm text-gray-600 mb-1">Total Reviews</div>
          <div className="text-3xl font-bold text-indigo-600">{data.total_reviews || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="text-sm text-gray-600 mb-1">Average Rating</div>
          <div className="text-3xl font-bold text-yellow-600">{data.average_rating?.toFixed(2) || '0.00'} ⭐</div>
        </div>
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="text-sm text-gray-600 mb-1">Positive Reviews</div>
          <div className="text-3xl font-bold text-green-600">
            {data.positive_reviews || 0} ({data.positive_percentage?.toFixed(1) || 0}%)
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="text-sm text-gray-600 mb-1">AI Accuracy</div>
          <div className="text-3xl font-bold text-purple-600">
            {data.ai_accuracy && data.ai_accuracy > 0 ? data.ai_accuracy.toFixed(1) : 'N/A'}%
          </div>
          {(!data.ai_accuracy || data.ai_accuracy === 0) && <div className="text-xs text-gray-500 mt-1">No predictions yet</div>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Rating Distribution</h3>
          <div className="h-64">
            <Bar data={ratingBarData} options={chartOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Reviews Over Time</h3>
          <div className="h-64">
            <Line data={timeLineData} options={chartOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Multi-dimensional Analysis</h3>
          <div className="h-64">
            <Radar data={radarData} options={radarOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">AI Prediction vs Actual</h3>
          <div className="h-64">
            {totalComparisons > 0 ? (
              <Doughnut data={comparisonData} options={doughnutOptions} />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <p className="text-lg mb-2">📊</p>
                  <p>No prediction data available yet.</p>
                  <p className="text-sm mt-1">Submit reviews to see AI prediction comparisons.</p>
                </div>
              </div>
            )}
          </div>
          {totalComparisons > 0 && (
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-sm">
              <div className="p-2 bg-green-50 rounded">
                <div className="font-bold text-green-700">{matches}</div>
                <div className="text-gray-600">Matches</div>
              </div>
              <div className="p-2 bg-blue-50 rounded">
                <div className="font-bold text-blue-700">{aiHigher}</div>
                <div className="text-gray-600">AI Higher</div>
              </div>
              <div className="p-2 bg-red-50 rounded">
                <div className="font-bold text-red-700">{aiLower}</div>
                <div className="text-gray-600">AI Lower</div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Key Insights & Recommendations</h2>
        <div className="space-y-3">
          {data.insights && data.insights.length > 0 ? (
            data.insights.map((insight, index) => (
              <div key={index} className="flex items-start p-3 bg-blue-50 rounded-lg">
                <span className="mr-3 text-blue-600">💡</span>
                <p className="text-gray-700">{insight}</p>
              </div>
            ))
          ) : (
            <div className="flex items-start p-3 bg-gray-50 rounded-lg">
              <span className="mr-3 text-gray-600">ℹ️</span>
              <p className="text-gray-700">No insights available. Submit more reviews to see analytics insights.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Analytics
