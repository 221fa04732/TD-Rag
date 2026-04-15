import AnswerText from './AnswerText'

/** Renders long markdown-ish explanations: ## headings + AnswerText for body (bold, lists). */
export default function ExplanationText({ text }) {
  if (!text) return null
  const segments = text.split(/\n(?=## )/)
  return (
    <div className="image-explanation">
      {segments.map((seg, i) => {
        const t = seg.trim()
        if (t.startsWith('## ')) {
          const nl = t.indexOf('\n')
          const heading = nl === -1 ? t.slice(3).trim() : t.slice(3, nl).trim()
          const body = nl === -1 ? '' : t.slice(nl + 1).trim()
          return (
            <div key={i} className="explanation-section">
              {heading && <h4 className="explanation-heading">{heading}</h4>}
              {body ? <AnswerText text={body} /> : null}
            </div>
          )
        }
        return <AnswerText key={i} text={t} />
      })}
    </div>
  )
}
