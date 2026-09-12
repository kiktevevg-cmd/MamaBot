export default function Settings({ settings, onUpdate }) {
  return (
    <div className="card">
      <h3>💬 Общение</h3>

      <div className="field">
        <label>Инициативность: {settings.initiative_level}</label>
        <input
          type="range"
          min="1"
          max="5"
          value={settings.initiative_level}
          onChange={(e) =>
            onUpdate({ initiative_level: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>Мин. пауза (минуты)</label>
        <input
          type="number"
          min="15"
          max="120"
          value={settings.min_cooldown_minutes}
          onChange={(e) =>
            onUpdate({ min_cooldown_minutes: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>Макс. пауза (часы)</label>
        <input
          type="number"
          min="1"
          max="12"
          value={settings.max_cooldown_hours}
          onChange={(e) =>
            onUpdate({ max_cooldown_hours: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>Начало активности (час)</label>
        <input
          type="number"
          min="0"
          max="23"
          value={settings.initiative_start_hour}
          onChange={(e) =>
            onUpdate({ initiative_start_hour: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>Конец активности (час)</label>
        <input
          type="number"
          min="0"
          max="23"
          value={settings.initiative_end_hour}
          onChange={(e) =>
            onUpdate({ initiative_end_hour: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>Длина ответов: {settings.response_length}</label>
        <input
          type="range"
          min="1"
          max="5"
          value={settings.response_length}
          onChange={(e) =>
            onUpdate({ response_length: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={settings.enable_emojis}
            onChange={(e) => onUpdate({ enable_emojis: e.target.checked })}
          />{' '}
          Эмодзи в сообщениях
        </label>
      </div>

      <h3 style={{ marginTop: 20 }}>😊 Эмоциональные реакции</h3>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={settings.enable_reactions ?? true}
            onChange={(e) => onUpdate({ enable_reactions: e.target.checked })}
          />{' '}
          Ставить реакции на значимые сообщения
        </label>
      </div>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={settings.allow_multiple_reactions ?? true}
            onChange={(e) =>
              onUpdate({ allow_multiple_reactions: e.target.checked })
            }
          />{' '}
          Несколько реакций одновременно
        </label>
      </div>

      <div className="field">
        <label>Стиль реакций</label>
        <select
          value={settings.reaction_style || 'живой'}
          onChange={(e) => onUpdate({ reaction_style: e.target.value })}
        >
          <option value="сдержанный">Сдержанный (только ❤️)</option>
          <option value="живой">Живой (разные эмоции)</option>
          <option value="эмоциональный">Эмоциональный (всегда несколько)</option>
        </select>
      </div>

      <div className="field">
        <label>
          Чувствительность к эмоциям: {settings.reaction_sensitivity ?? 3}
        </label>
        <input
          type="range"
          min="1"
          max="5"
          value={settings.reaction_sensitivity ?? 3}
          onChange={(e) =>
            onUpdate({ reaction_sensitivity: parseInt(e.target.value, 10) })
          }
        />
        <p style={{ fontSize: '0.75rem', color: '#888', marginTop: 4 }}>
          1 — только явные эмоции · 3 — умеренно · 5 — на любые значимые
        </p>
      </div>

      <div
        style={{
          fontSize: '0.85rem',
          lineHeight: 1.6,
          color: '#666',
          marginTop: 8,
        }}
      >
        <strong>Примеры:</strong>
        <br />
        Достижение → 🔥 🎉 👏
        <br />
        Грусть → 💔 😢
        <br />
        Любовь → ❤️ 🥰
      </div>
    </div>
  )
}
