import { useState, useEffect } from 'react'

const API = 'http://192.168.10.202:8000'

export default function UploadPage() {
  const [books, setBooks] = useState([])
  const [selectedBookId, setSelectedBookId] = useState('')
  const [error, setError] = useState('')

  const [pdfFile, setPdfFile] = useState(null)
  const [uploadingPdf, setUploadingPdf] = useState(false)
  const [uploadPdfMsg, setUploadPdfMsg] = useState('')

  const [bulkImgFiles, setBulkImgFiles] = useState(null)
  const [uploadingBulk, setUploadingBulk] = useState(false)
  const [bulkMsg, setBulkMsg] = useState('')

  const [imgFile, setImgFile] = useState(null)
  const [imgTitle, setImgTitle] = useState('')
  const [imgFigureRef, setImgFigureRef] = useState('')
  const [uploadingImg, setUploadingImg] = useState(false)
  const [uploadImgMsg, setUploadImgMsg] = useState('')

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

  const handlePdfUpload = async (e) => {
    e.preventDefault()
    if (!pdfFile) return
    setUploadingPdf(true)
    setUploadPdfMsg('')
    setError('')
    const form = new FormData()
    form.append('file', pdfFile)
    try {
      const res = await fetch(`${API}/api/books/upload`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setUploadPdfMsg(data.message || 'PDF uploaded. Add images below.')
      setPdfFile(null)
      await fetchBooks()
      if (data.book_id) setSelectedBookId(data.book_id)
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploadingPdf(false)
    }
  }

  const handleBulkImageUpload = async (e) => {
    e.preventDefault()
    if (!selectedBookId || !bulkImgFiles?.length) {
      setBulkMsg('Select a book and choose one or more image files.')
      return
    }
    setUploadingBulk(true)
    setBulkMsg('')
    const form = new FormData()
    for (let i = 0; i < bulkImgFiles.length; i++) {
      form.append('files', bulkImgFiles[i])
    }
    try {
      const res = await fetch(`${API}/api/books/${selectedBookId}/images/bulk`, {
        method: 'POST',
        body: form,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || 'Bulk upload failed')
      const { added = 0, failed = 0, errors = [] } = data
      let text = `Added ${added} image(s).`
      if (failed > 0) {
        text += ` ${failed} failed.`
        if (errors.length) {
          text += ' ' + errors.map((x) => `${x.filename}: ${x.reason}`).join(' · ')
        }
      } else {
        text += ' Go to Ask to query, or add more files.'
      }
      setBulkMsg(text)
      setBulkImgFiles(null)
      const bulkInput = document.getElementById('bulk-image-input')
      if (bulkInput) bulkInput.value = ''
    } catch (err) {
      setBulkMsg(err.message || 'Bulk upload failed')
    } finally {
      setUploadingBulk(false)
    }
  }

  const handleImageUpload = async (e) => {
    e.preventDefault()
    if (!selectedBookId || !imgFile || !imgTitle.trim() || !imgFigureRef.trim()) {
      setUploadImgMsg('Select a book, choose an image, enter a title, and the figure label as printed in the book (e.g. Fig. 2.1).')
      return
    }
    setUploadingImg(true)
    setUploadImgMsg('')
    const form = new FormData()
    form.append('file', imgFile)
    form.append('title', imgTitle.trim())
    form.append('figure_ref', imgFigureRef.trim())
    try {
      const res = await fetch(`${API}/api/books/${selectedBookId}/images`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : data.detail?.message || 'Upload failed')
      setUploadImgMsg('Image added. Add more or click "Done adding images", then go to Ask to query.')
      setImgFile(null)
      setImgTitle('')
      setImgFigureRef('')
    } catch (err) {
      setUploadImgMsg(err.message || 'Failed to add image')
    } finally {
      setUploadingImg(false)
    }
  }

  const handleDoneImages = async () => {
    if (!selectedBookId) return
    try {
      await fetch(`${API}/api/books/${selectedBookId}/images/done`, { method: 'POST' })
      setUploadImgMsg('Done. Go to Ask to ask questions.')
    } catch (_) {}
  }

  return (
    <div>
      <h1>Upload</h1>
      <p className="subtitle">Upload a PDF, then add figures: either many at once (filename encodes figure label and title) or one-by-one below. At query time we match images using your question plus retrieved text.</p>

      {error && <div className="error">{error}</div>}

      <section className="section">
        <h2>1. Upload PDF textbook</h2>
        <form onSubmit={handlePdfUpload} className="form-row">
          <div className="form-row">
            <label>PDF file</label>
            <input type="file" accept=".pdf" onChange={(e) => setPdfFile(e.target.files?.[0] || null)} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={!pdfFile || uploadingPdf}>
            {uploadingPdf ? 'Processing…' : 'Upload PDF'}
          </button>
        </form>
        {uploadPdfMsg && <div className="success">{uploadPdfMsg}</div>}
      </section>

      <section className="section">
        <h2>2. Add images</h2>
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

        <h3 style={{ marginTop: '1.25rem', fontSize: '1.05rem' }}>Bulk upload (recommended)</h3>
        <p style={{ fontSize: '0.9rem', color: '#a1a1aa', marginBottom: '0.75rem' }}>
          Name each file like: <code style={{ color: '#e4e4e7' }}>Figure 1.1 (Short title here).png</code> — text before the parentheses is the figure label (as in the book); text inside is the image title.
        </p>
        <form onSubmit={handleBulkImageUpload}>
          <div className="form-row">
            <label>Image files</label>
            <input
              id="bulk-image-input"
              type="file"
              accept=".jpg,.jpeg,.png,.gif,.webp"
              multiple
              onChange={(e) => setBulkImgFiles(e.target.files)}
            />
          </div>
          <div className="flex" style={{ marginTop: '0.75rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!selectedBookId || !bulkImgFiles?.length || uploadingBulk}
            >
              {uploadingBulk ? 'Uploading…' : 'Upload all'}
            </button>
            <button type="button" className="btn btn-success" onClick={handleDoneImages} disabled={!selectedBookId}>
              Done adding images
            </button>
          </div>
        </form>
        {bulkMsg && (
          <div
            className={bulkMsg.includes('failed') || bulkMsg.startsWith('Select') ? 'error' : 'success'}
            style={{ marginTop: '0.75rem' }}
          >
            {bulkMsg}
          </div>
        )}

        <h3 style={{ marginTop: '1.75rem', fontSize: '1.05rem' }}>Or one at a time</h3>
        <form onSubmit={handleImageUpload}>
          <div className="grid-2">
            <div className="form-row">
              <label>Image file</label>
              <input type="file" accept=".jpg,.jpeg,.png,.gif,.webp" onChange={(e) => setImgFile(e.target.files?.[0] || null)} />
            </div>
            <div className="form-row">
              <label>Title</label>
              <input type="text" placeholder="e.g. Neural network diagram" value={imgTitle} onChange={(e) => setImgTitle(e.target.value)} required />
            </div>
          </div>
          <div className="form-row">
            <label>Figure reference</label>
            <input
              type="text"
              placeholder="e.g. Fig. 2.1, Figure 3.2a, 3.1(b)"
              value={imgFigureRef}
              onChange={(e) => setImgFigureRef(e.target.value)}
              required
            />
            <p style={{ fontSize: '0.8rem', color: '#71717a', marginTop: '0.35rem' }}>
              Use the same label as in the textbook so retrieval can align with passages that mention this figure.
            </p>
          </div>
          <div className="flex" style={{ marginTop: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={!selectedBookId || !imgFile || !imgTitle.trim() || !imgFigureRef.trim() || uploadingImg}>
              {uploadingImg ? 'Adding…' : 'Add image'}
            </button>
          </div>
        </form>
        {uploadImgMsg && <div className={uploadImgMsg.startsWith('Image added') || uploadImgMsg.includes('Done') ? 'success' : 'error'}>{uploadImgMsg}</div>}
      </section>
    </div>
  )
}
