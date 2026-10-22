/** Подписи ключей памяти для Mini App (синхрон с preference_extractor). */
export const FACT_LABELS_RU = {
  work: 'Работа',
  health: 'Здоровье',
  relationships: 'Отношения',
  hobby: 'Хобби',
  events: 'События',
  food: 'Еда',
  sleep: 'Сон',
  plans: 'Планы',
  pet: 'Питомцы',
  name: 'Имя',
  location: 'Место',
  mood: 'Настроение',
  preferences: 'Просьбы и предпочтения',
  requests: 'Просьбы',
  address: 'Как обращаться',
  communication: 'Как общаться',
  family: 'Семья',
  other: 'Другое',
}

export function labelForKey(key) {
  return FACT_LABELS_RU[key] || key
}
