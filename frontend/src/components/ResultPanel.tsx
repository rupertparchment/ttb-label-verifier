import { useState } from 'react'
import type { VerificationResult } from '../types'

interface Props {
  results: VerificationResult[]
  batchSummary: {
    total: number
    passed: number
    failed: number
    warnings: number
    total_processing_time_ms: number
  } | null
}

function statusIcon(status: string) {
  switch (status) {
    case 'pass': return '✓'
    case 'fail': return '✗'
    case 'warning': return '⚠'
    default: return '—'
  }
}

function ResultCard({ result }: { result: VerificationResult }) {
  const [open, setOpen] = useState(result.overall_status !== 'pass')

  return (
    <div className={`result-card ${result.overall_status}`}>
      <div
        className="result-header"
        onClick={() => setOpen(!open)}
        role="button"
        aria-expanded={open}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {result.image_preview && (
            <img
              src={`data:image/jpeg;base64,${result.image_preview}`}
              alt=""
              className="thumbnail"
            />
          )}
          <div>
            <strong>{result.filename}</strong>
            <div className="help-text">{result.processing_time_ms} ms</div>
          </div>
        </div>
        <span className={`status-badge ${result.overall_status}`}>
          {statusIcon(result.overall_status)} {result.overall_status}
        </span>
      </div>
      {open && (
        <div className="result-body">
          <table className="check-table">
            <thead>
              <tr>
                <th>Field</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {result.checks.map((check, i) => (
                <tr key={i}>
                  <td><strong>{check.field_name}</strong></td>
                  <td>
                    <span className={`check-icon ${check.status}`}>
                      {statusIcon(check.status)}
                    </span>
                  </td>
                  <td>{check.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.extracted_text && (
            <details style={{ marginTop: '1rem' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                Extracted label text (OCR)
              </summary>
              <pre style={{
                whiteSpace: 'pre-wrap',
                fontSize: '0.85rem',
                background: '#f4f6f8',
                padding: '0.75rem',
                borderRadius: '4px',
                marginTop: '0.5rem',
              }}>
                {result.extracted_text}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

export function ResultPanel({ results, batchSummary }: Props) {
  return (
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <h2 className="card-title">Verification Results</h2>

      {batchSummary && (
        <div className="summary-bar">
          <span>{batchSummary.total} labels processed in {(batchSummary.total_processing_time_ms / 1000).toFixed(1)}s</span>
          <span className="pass">{batchSummary.passed} passed</span>
          <span className="fail">{batchSummary.failed} failed</span>
          {batchSummary.warnings > 0 && (
            <span className="warning">{batchSummary.warnings} need review</span>
          )}
        </div>
      )}

      {!batchSummary && results.length === 1 && (
        <div className="summary-bar">
          <span>Processed in {results[0].processing_time_ms} ms</span>
          <span className={results[0].overall_status}>
            Overall: {results[0].overall_status.toUpperCase()}
          </span>
        </div>
      )}

      {results.map((r, i) => (
        <ResultCard key={i} result={r} />
      ))}
    </div>
  )
}
