'use client'

import { useState } from 'react'
import { apiClient, QueryResponse } from '@/lib/api';
import MetarDisplay from './MetarDisplay'

export function QueryInterface() {
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [response, setResponse] = useState<QueryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const result = await apiClient.submitQuery({
        query: query.trim(),
        location: location || undefined,
      })

      setResponse(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get response')
      setResponse(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="query-interface">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="query">Your Question</label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., What's the crosswind for landing at Denver?"
            disabled={loading}
            rows={4}
          />
        </div>

        <div className="form-group">
          <label htmlFor="location">Location (Optional)</label>
          <input
            id="location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g., KDEN"
            disabled={loading}
          />
        </div>

        <button type="submit" disabled={loading} className="submit-btn">
          {loading ? 'Thinking...' : 'Get Answer'}
        </button>
      </form>

      {error && <div className="error-box">{error}</div>}

      {response && (
        <div className={`response-box ${response.is_fallback ? 'fallback' : 'live'}`}>
          <div className="response-header">
            <div className={`response-badge ${response.is_fallback ? 'fallback' : 'live'}`}>
              {response.is_fallback ? '⚠️ FALLBACK' : '✅ LIVE'}
            </div>
            <div className="verification-info">
              <p>
                <strong>Verification:</strong>{' '}
                {response.guardrail_status === 'passed'
                  ? '✅ Passed'
                  : response.guardrail_status === 'failed'
                    ? '❌ Failed (Corrected)'
                    : '⊘ Skipped'}
              </p>
            </div>
          </div>

          {/* Display structured METAR data or text response */}
          {response.response_type === 'metar' && response.metar ? (
            <MetarDisplay metar={response.metar} landing={response.landing} />
          ) : (
            <div className="response-text whitespace-pre-wrap">{response.text_response}</div>
          )}

          {response.details && (
            <details className="response-details">
              <summary>Technical Details</summary>
              <pre>{JSON.stringify(response.details, null, 2)}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
