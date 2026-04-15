import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AnswerText from '../components/AnswerText'
import ExplanationText from '../components/ExplanationText'

const API = ''

export default function QueryPage() {
  const [books, setBooks] = useState([])
  const [selectedBookId, setSelectedBookId] = useState('')
  const [query, setQuery] = useState('')
  const [submittedQuestion, setSubmittedQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  /** index -> { loading, text, error } */
  const [imageExplainByIndex, setImageExplainByIndex] = useState({})

  const fetchBooks = async () => {
    try {
      const r = await fetch(`${API}/api/books`)
      const data = await r.json()
      setBooks(data.books || [])
      if (data.books?.length && !selectedBookId) setSelectedBookId(data.books[0].id)
    } catch (e) {
      setError('Failed to load books')
    }
  }

  useEffect(() => { fetchBooks() }, [])

  useEffect(() => {
    if (!result?.images?.length || !selectedBookId || !submittedQuestion) {
      setImageExplainByIndex({})
      return
    }

    const ac = new AbortController()
    const images = result.images
    const q = submittedQuestion
    const bookId = selectedBookId

    setImageExplainByIndex(
      Object.fromEntries(images.map((_, i) => [i, { loading: true, text: null, error: null }])),
    )

    ;(async () => {
      await Promise.all(
        images.map(async (img, i) => {
          try {
            const res = await fetch(`${API}/api/image-explanation`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                book_id: bookId,
                question: q,
                image_path: img.image_path,
                title: img.title || undefined,
              }),
              signal: ac.signal,
            })
            let data = {}
            try {
              data = await res.json()
            } catch (_) {
              data = {}
            }
            if (!res.ok) {
              const d = data.detail
              const msg =
                typeof d === 'string'
                  ? d
                  : Array.isArray(d)
                    ? d.map((x) => x.msg || x).join(' ')
                    : 'Explanation failed'
              throw new Error(msg || 'Explanation failed')
            }
            if (ac.signal.aborted) return
            setImageExplainByIndex((prev) => ({
              ...prev,
              [i]: { loading: false, text: data.explanation || null, error: null },
            }))
          } catch (err) {
            if (err.name === 'AbortError' || ac.signal.aborted) return
            setImageExplainByIndex((prev) => ({
              ...prev,
              [i]: { loading: false, text: null, error: err.message || 'Failed to load explanation' },
            }))
          }
        }),
      )
    })()

    return () => ac.abort()
  }, [result, selectedBookId, submittedQuestion])

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!selectedBookId || !query.trim()) return
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const res = await fetch(`${API}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ book_id: selectedBookId, question: query.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Query failed')
      setSubmittedQuestion(query.trim())
      setResult(data)
    } catch (err) {
      setError(err.message || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Ask</h1>
      <p className="subtitle">Choose a book and ask a question. You get an answer from the book and relevant images.</p>

      {error && <div className="error">{error}</div>}

      {books.length === 0 && (
        <div className="section">
          <p>No books yet. <Link to="/upload">Upload a PDF</Link> first, then add images.</p>
        </div>
      )}

      {books.length > 0 && (
        <section className="section">
          <h2>Ask a question</h2>
          <form onSubmit={handleQuery}>
            <div className="form-row">
              <label>Book</label>
              <select
                value={selectedBookId}
                onChange={(e) => setSelectedBookId(e.target.value)}
                style={{ padding: '0.6rem', borderRadius: 8, background: '#27272a', color: '#e4e4e7', border: '1px solid #3f3f46', minWidth: 200 }}
              >
                <option value="">Select a book</option>
                {books.map((b) => (
                  <option key={b.id} value={b.id}>{b.title || b.id}</option>
                ))}
              </select>
            </div>
            <div className="form-row">
              <label>Question</label>
              <input type="text" placeholder="e.g. Explain the architecture of a neural network" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={!selectedBookId || !query.trim() || loading}>
              {loading ? 'Searching…' : 'Search'}
            </button>
          </form>

          {result && (
            <div style={{ marginTop: '1.5rem' }}>
              <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>Results</h3>
              {result.answer && (
                <div className="result-text" style={{ marginBottom: '1rem' }}>
                  <div style={{ marginBottom: '0.5rem', color: '#a1a1aa', fontSize: '0.85rem' }}>Answer (from the book):</div>
                  <AnswerText text={result.answer} />
                </div>
              )}
              {!result.answer && result.text_sections?.length > 0 && (
                <>
                  <div style={{ marginBottom: '0.5rem', color: '#a1a1aa', fontSize: '0.85rem' }}>From the book (no synthesized answer — add GEMINI_API_KEY in backend/.env and restart):</div>
                  {result.text_sections.map((s, i) => (
                    <div key={i} className="result-text">
                      {s.page_number != null && <div className="page">Page {s.page_number}</div>}
                      {s.text}
                    </div>
                  ))}
                </>
              )}
              {result.images?.length > 0 && (
                <>
                  <div style={{ marginBottom: '0.5rem', color: '#a1a1aa', fontSize: '0.85rem' }}>Relevant images (from your uploads):</div>
                  <div className="result-images">
                    {result.images.map((img, i) => {
                      const ex = imageExplainByIndex[i]
                      return (
                        <div key={`${img.image_path}-${i}`} className="result-img-card">
                          <img src={img.image_path.startsWith('http') ? img.image_path : `${API || ''}${img.image_path}`} alt={img.title} />
                          <div className="caption">
                            <strong>{img.title}</strong>
                            {img.figure_ref && <div className="figure-ref">{img.figure_ref}</div>}
                            {img.page_ref && <div className="page-ref">{img.page_ref}</div>}
                          </div>
                          {(ex?.loading || ex?.error || ex?.text) && (
                            <div className="image-explanation-wrap">
                              <details className="image-explanation-details">
                                <summary className="image-explanation-summary">
                                  {ex.loading
                                    ? 'Image explanation — generating…'
                                    : ex.error
                                      ? 'Image explanation — error (expand for details)'
                                      : 'Image explanation — show'}
                                </summary>
                                <div className="image-explanation-panel">
                                  {ex.loading && (
                                    <div className="image-explanation-status">Generating explanation…</div>
                                  )}
                                  {ex.error && (
                                    <div className="image-explanation-status error">{ex.error}</div>
                                  )}
                                  {ex.text && (
                                    <>
                                      <div className="image-explanation-label">For your question</div>
                                      <ExplanationText text={ex.text} />
                                    </>
                                  )}
                                </div>
                              </details>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </>
              )}
              {(!result.answer && !result.text_sections?.length && !result.images?.length) && (
                <div className="result-text">No matching text or images found. Try rephrasing or add images with title and figure labels on the Upload page.</div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
