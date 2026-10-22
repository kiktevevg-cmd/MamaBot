import { labelForKey } from '../memoryLabels'

export default function Memory({ facts, onDelete, onClear, onRefresh }) {
  const entries = Object.entries(facts || {})

  return (
    <>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>🧠 Память мамы</h3>
          {onRefresh && (
            <button type="button" className="btn btn-secondary" onClick={onRefresh}>
              Обновить
            </button>
          )}
        </div>
        {entries.length === 0 && (
          <p style={{ lineHeight: 1.5, marginTop: 8 }}>
            Пока пусто. Напиши маме в чат что-то вроде «запомни: …» или «не называй меня …» —
            просьбы и факты появятся здесь.
          </p>
        )}
        {entries.map(([key, value]) => (
          <div className="fact-item" key={key}>
            <span className="fact-key">{labelForKey(key)}</span>
            <span className="fact-value">{value}</span>
            <button className="delete-btn" onClick={() => onDelete(key)} type="button">
              🗑
            </button>
          </div>
        ))}
      </div>
      {entries.length > 0 && (
        <button className="btn btn-danger" onClick={() => onClear('all')} type="button">
          Очистить всю память
        </button>
      )}
    </>
  )
}
