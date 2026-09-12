const PERSONALITIES = ['заботливая', 'строгая', 'веселая', 'ностальгическая']

export default function Profile({ settings, onUpdate }) {
  return (
    <div className="card">
      <h3>👤 Личное</h3>

      <div className="field">
        <label>Твоё имя</label>
        <input
          value={settings.user_name || ''}
          onChange={(e) => onUpdate({ user_name: e.target.value })}
          placeholder="Как к тебе обращаться"
        />
      </div>

      <div className="field">
        <label>Пол</label>
        <select
          value={settings.user_gender}
          onChange={(e) => onUpdate({ user_gender: e.target.value })}
        >
          <option value="не указано">Не указано</option>
          <option value="мужской">Мужской</option>
          <option value="женский">Женский</option>
        </select>
      </div>

      <div className="field">
        <label>Имя мамы</label>
        <input
          value={settings.mama_name}
          onChange={(e) => onUpdate({ mama_name: e.target.value })}
        />
      </div>

      <div className="field">
        <label>Характер мамы</label>
        <select
          value={settings.mama_personality}
          onChange={(e) => onUpdate({ mama_personality: e.target.value })}
        >
          {PERSONALITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
