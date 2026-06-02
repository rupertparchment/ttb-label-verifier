import { useCallback, useRef, useState } from 'react'
import type { ApplicationData, BatchVerificationResponse, VerificationResult } from './types'
import { EMPTY_APPLICATION, STANDARD_WARNING } from './types'
import { ResultPanel } from './components/ResultPanel'
import { SAMPLE_PRESETS } from './samples'

type Mode = 'single' | 'batch'

// In dev, call the backend directly (avoids Vite proxy localhost/IPv6 issues on Windows)
const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')

export default function App() {
  const [mode, setMode] = useState<Mode>('single')
  const [application, setApplication] = useState<ApplicationData>({ ...EMPTY_APPLICATION })
  const [files, setFiles] = useState<File[]>([])
  const [batchApps, setBatchApps] = useState<ApplicationData[]>([])
  const [results, setResults] = useState<VerificationResult[] | null>(null)
  const [batchSummary, setBatchSummary] = useState<Omit<BatchVerificationResponse, 'results'> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateField = (field: keyof ApplicationData, value: string) => {
    setApplication((prev) => ({ ...prev, [field]: value }))
  }

  const handleFiles = useCallback((incoming: FileList | File[]) => {
    const imageFiles = Array.from(incoming).filter((f) => f.type.startsWith('image/'))
    if (mode === 'single') {
      setFiles(imageFiles.slice(0, 1))
    } else {
      setFiles(imageFiles)
      // Default batch apps: same template for each file (user can edit via CSV import later)
      setBatchApps(
        imageFiles.map(() => ({ ...application, brand_name: application.brand_name || '' })),
      )
    }
    setResults(null)
    setBatchSummary(null)
    setError(null)
  }, [mode, application])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    handleFiles(e.dataTransfer.files)
  }

  const loadDemoData = () => {
    setApplication({ ...SAMPLE_PRESETS[0].application })
  }

  const loadSample = (id: string) => {
    const sample = SAMPLE_PRESETS.find((s) => s.id === id)
    if (sample) {
      setApplication({ ...sample.application })
    }
  }

  const verify = async () => {
    if (files.length === 0) {
      setError('Please upload at least one label image.')
      return
    }
    if (mode === 'single' && !application.brand_name.trim()) {
      setError('Brand name is required.')
      return
    }

    setLoading(true)
    setError(null)
    setResults(null)
    setBatchSummary(null)

    try {
      if (mode === 'single') {
        const form = new FormData()
        form.append('image', files[0])
        form.append('brand_name', application.brand_name)
        form.append('class_type', application.class_type)
        form.append('alcohol_content', application.alcohol_content)
        form.append('net_contents', application.net_contents)
        form.append('government_warning', application.government_warning)
        form.append('bottler_producer', application.bottler_producer)
        form.append('country_of_origin', application.country_of_origin)

        const res = await fetch(`${API_BASE}/api/verify`, { method: 'POST', body: form })
        if (!res.ok) {
          const detail = await res.text()
          if (res.status === 500 && !detail) {
            throw new Error(
              'Cannot reach the backend. Make sure uvicorn is running on port 8000, then try again.'
            )
          }
          throw new Error(detail || `Server error (${res.status})`)
        }
        const data: VerificationResult = await res.json()
        setResults([data])
      } else {
        const form = new FormData()
        files.forEach((f) => form.append('images', f))
        const apps = batchApps.length === files.length
          ? batchApps
          : files.map(() => application)
        form.append('applications_json', JSON.stringify(apps))

        const res = await fetch(`${API_BASE}/api/verify/batch`, { method: 'POST', body: form })
        if (!res.ok) {
          const detail = await res.text()
          if (res.status === 500 && !detail) {
            throw new Error(
              'Cannot reach the backend. Make sure uvicorn is running on port 8000, then try again.'
            )
          }
          throw new Error(detail || `Server error (${res.status})`)
        }
        const data: BatchVerificationResponse = await res.json()
        setResults(data.results)
        setBatchSummary({
          total: data.total,
          passed: data.passed,
          failed: data.failed,
          warnings: data.warnings,
          total_processing_time_ms: data.total_processing_time_ms,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header className="app-header">
        <h1>TTB Label Verifier</h1>
        <p>Compare label artwork against application data — results in seconds</p>
      </header>

      <main className="app-main">
        <div className="tabs" role="tablist">
          <button
            role="tab"
            aria-selected={mode === 'single'}
            className={`tab ${mode === 'single' ? 'active' : ''}`}
            onClick={() => { setMode('single'); setFiles([]); setResults(null) }}
          >
            Single Label
          </button>
          <button
            role="tab"
            aria-selected={mode === 'batch'}
            className={`tab ${mode === 'batch' ? 'active' : ''}`}
            onClick={() => { setMode('batch'); setFiles([]); setResults(null) }}
          >
            Batch Upload
          </button>
        </div>

        {error && <div className="error-banner" role="alert">{error}</div>}

        <div className="card">
          <h2 className="card-title">Step 1 — Upload Label {mode === 'batch' ? 'Images' : 'Image'}</h2>
          <div
            className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          >
            <div className="drop-zone-icon" aria-hidden="true">📄</div>
            <p><strong>Click or drag {mode === 'batch' ? 'images' : 'an image'} here</strong></p>
            <p>JPEG or PNG label artwork</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple={mode === 'batch'}
              className="sr-only"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
          </div>
          {files.length > 0 && (
            <ul className="file-list">
              {files.map((f, i) => (
                <li key={i}>
                  <span>{f.name}</span>
                  <span>{(f.size / 1024).toFixed(0)} KB</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {mode === 'single' ? (
          <div className="card">
            <h2 className="card-title">Step 2 — Application Data</h2>
            <p className="help-text" style={{ marginBottom: '1rem' }}>
              Enter the values from the COLA application to compare against the label.
              Each sample label in <code>sample_labels/</code> needs matching application data.
            </p>
            <div className="form-group">
              <label htmlFor="sample_preset">Load sample application data</label>
              <select
                id="sample_preset"
                defaultValue=""
                onChange={(e) => e.target.value && loadSample(e.target.value)}
              >
                <option value="" disabled>Select a test case…</option>
                {SAMPLE_PRESETS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label} — use {s.filename}
                  </option>
                ))}
              </select>
            </div>
            <button type="button" className="btn-secondary" onClick={loadDemoData} style={{ marginBottom: '1rem' }}>
              Load Demo Data (Old Tom)
            </button>
            <div className="form-group">
              <label htmlFor="brand_name">Brand Name *</label>
              <input
                id="brand_name"
                value={application.brand_name}
                onChange={(e) => updateField('brand_name', e.target.value)}
                placeholder="e.g. OLD TOM DISTILLERY"
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="class_type">Class / Type</label>
                <input
                  id="class_type"
                  value={application.class_type}
                  onChange={(e) => updateField('class_type', e.target.value)}
                  placeholder="Kentucky Straight Bourbon Whiskey"
                />
              </div>
              <div className="form-group">
                <label htmlFor="alcohol_content">Alcohol Content</label>
                <input
                  id="alcohol_content"
                  value={application.alcohol_content}
                  onChange={(e) => updateField('alcohol_content', e.target.value)}
                  placeholder="45% Alc./Vol. (90 Proof)"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="net_contents">Net Contents</label>
                <input
                  id="net_contents"
                  value={application.net_contents}
                  onChange={(e) => updateField('net_contents', e.target.value)}
                  placeholder="750 mL"
                />
              </div>
              <div className="form-group">
                <label htmlFor="bottler_producer">Bottler / Producer</label>
                <input
                  id="bottler_producer"
                  value={application.bottler_producer}
                  onChange={(e) => updateField('bottler_producer', e.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="government_warning">Government Warning (expected text)</label>
              <textarea
                id="government_warning"
                rows={4}
                value={application.government_warning}
                onChange={(e) => updateField('government_warning', e.target.value)}
              />
            </div>
          </div>
        ) : (
          <div className="card">
            <h2 className="card-title">Step 2 — Application Data (shared template)</h2>
            <p className="help-text" style={{ marginBottom: '1rem' }}>
              For batch uploads from the same importer, enter the common application fields below.
              Each uploaded image will be checked against this data. For mixed applications, run separate batches.
            </p>
            <div className="form-group">
              <label htmlFor="batch_brand">Brand Name *</label>
              <input
                id="batch_brand"
                value={application.brand_name}
                onChange={(e) => updateField('brand_name', e.target.value)}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="batch_class">Class / Type</label>
                <input id="batch_class" value={application.class_type} onChange={(e) => updateField('class_type', e.target.value)} />
              </div>
              <div className="form-group">
                <label htmlFor="batch_abv">Alcohol Content</label>
                <input id="batch_abv" value={application.alcohol_content} onChange={(e) => updateField('alcohol_content', e.target.value)} />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="batch_net">Net Contents</label>
              <input id="batch_net" value={application.net_contents} onChange={(e) => updateField('net_contents', e.target.value)} />
            </div>
          </div>
        )}

        <div className="actions">
          <button
            className="btn-primary"
            onClick={verify}
            disabled={loading || files.length === 0}
          >
            {loading ? 'Verifying…' : `Verify ${files.length > 1 ? `${files.length} Labels` : 'Label'}`}
          </button>
          {files.length > 0 && (
            <button
              className="btn-secondary"
              onClick={() => { setFiles([]); setResults(null); setError(null) }}
            >
              Clear
            </button>
          )}
        </div>

        {results && (
          <ResultPanel results={results} batchSummary={batchSummary} />
        )}
      </main>

      {loading && (
        <div className="loading-overlay" aria-live="polite">
          <div className="spinner" />
          <p>Reading label and checking fields…</p>
        </div>
      )}
    </>
  )
}
