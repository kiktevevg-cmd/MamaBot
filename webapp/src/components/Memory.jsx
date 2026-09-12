export default function Memory({ facts, onDelete, onClear }) {
  const entries = Object.entries(facts)

  return (
    <>
      <div className="card">
        <h3>🧠 Память мамы</h3>
        {entries.length === 0 && <p>Пока ничего не запомнила</p>}
        {entries.map(([key, value]) => (
          <div className="fact-item" key={key}>
            <span className="fact-key">{key}</span>
            <span className="fact-value">{value}</span>
            <button className="delete-btn" onClick={() => onDelete(key)}>
              🗑
            </button>
          </div>
        ))}
      </div>
      {entries.length > 0 && (
        <button className="btn btn-danger" onClick={() => onClear('all')}>
          Очистить всю память
        </button>
      )}
    </>
  )
}
