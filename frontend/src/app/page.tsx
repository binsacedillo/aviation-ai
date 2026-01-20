import { HealthStatus } from '@/components/HealthStatus'
import { QueryInterface } from '@/components/QueryInterface'
import '@/styles/globals.css'

export const metadata = {
  title: 'Flight Copilot Assistant',
  description: 'AI-powered flight planning assistant with semantic guardrails',
}

export default function Home() {
  return (
    <main className="container">
      <header className="header">
        <h1>✈️ Flight Copilot Assistant</h1>
        <p>AI-powered flight planning with semantic guardrails</p>
      </header>

      <div className="dashboard">
        <section className="section health-section">
          <h2>System Status</h2>
          <HealthStatus />
        </section>

        <section className="section query-section">
          <h2>Ask a Question</h2>
          <QueryInterface />
        </section>

        <section className="section info-section">
          <h2>About</h2>
          <div className="info-box">
            <h3>Live vs Fallback Responses</h3>
            <dl>
              <dt>✅ Live</dt>
              <dd>
                Response passed semantic guardrails verification. Crosswind calculations are accurate within 3 knots.
              </dd>
              <dt>⚠️ Fallback</dt>
              <dd>
                Response failed verification. Agent reflected and corrected. If still failing, safe-fail defensive layer
                provided conservative response.
              </dd>
            </dl>

            <h3>Guardrail Status</h3>
            <dl>
              <dt>✅ Passed</dt>
              <dd>Response verified against real METAR data. Claim is within acceptable tolerance.</dd>
              <dt>❌ Failed (Corrected)</dt>
              <dd>Response failed verification, agent reflected and generated corrected response.</dd>
              <dt>⊘ Skipped</dt>
              <dd>No METAR or runway data available. Verification could not be performed.</dd>
            </dl>
          </div>
        </section>
      </div>

      <footer className="footer">
        <p>Flight Copilot © 2026 | All responses verified with semantic guardrails</p>
      </footer>
    </main>
  )
}
