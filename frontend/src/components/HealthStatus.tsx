'use client'

import { useEffect, useState } from 'react'
import { apiClient, type HealthStatus as HealthStatusType } from '@/lib/api'

export function HealthStatus() {
  const [health, setHealth] = useState<HealthStatusType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        setLoading(true)
        const data = await apiClient.getHealth()
        setHealth(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health status')
        setHealth(null)
      } finally {
        setLoading(false)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [])

  if (loading && !health) {
    return (
      <div className="health-status loading">
        <div className="spinner"></div>
        <p>Connecting to backend...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="health-status error">
        <div className="status-badge error">🔴 DISCONNECTED</div>
        <p className="error-text">{error}</p>
        <p className="hint">Make sure the backend is running on {process.env.NEXT_PUBLIC_API_URL}</p>
      </div>
    )
  }

  if (!health) return null

  return (
    <div className="health-status">
      <div className={`status-badge ${health.status}`}>
        {health.status === 'ok' ? '🟢 LIVE' : '🔴 ERROR'}
      </div>

      <div className="health-details">
        <p>
          <strong>Status:</strong> {health.status === 'ok' ? 'Online' : 'Error'}
        </p>
        <p>
          <strong>Version:</strong> {health.version}
        </p>
        <p>
          <strong>Guardrails:</strong> {health.guardrails_active ? '🛡️ Active' : '⚠️ Inactive'}
        </p>
        <p>
          <strong>Tests:</strong> {health.tests_passing}/{health.tests_total} passing
        </p>
      </div>
    </div>
  )
}
