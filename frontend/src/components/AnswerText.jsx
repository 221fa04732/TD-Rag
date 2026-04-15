// Simple renderer so the LLM answer (paragraphs, bullets, **bold**) displays nicely
export default function AnswerText({ text }) {
  if (!text) return null
  const blocks = text.split(/\n\n+/)
  return (
    <div className="answer-body">
      {blocks.map((block, i) => {
        const trimmed = block.trim()
        if (!trimmed) return null
        const lines = trimmed.split('\n')
        const isList = lines.every(l => /^\s*[-*]\s+/.test(l) || l.trim() === '')
        if (isList && lines.some(l => l.trim())) {
          return (
            <ul key={i} style={{ margin: '0.5rem 0', paddingLeft: '1.25rem' }}>
              {lines.filter(l => l.trim()).map((line, j) => {
                const content = line.replace(/^\s*[-*]\s+/, '')
                return <li key={j} dangerouslySetInnerHTML={{ __html: content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>') }} />
              })}
            </ul>
          )
        }
        return (
          <p key={i} style={{ margin: '0.5rem 0', lineHeight: 1.6 }} dangerouslySetInnerHTML={{ __html: trimmed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>') }} />
        )
      })}
    </div>
  )
}
