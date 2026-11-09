export type ActionHistoryItem = {
  id: number;
  title: string;
  description: string;
  dateTime: string;
  icon: string;
  color: string;
};

const STORAGE_KEY = 'bolpar-action-history';

export const getActionHistory = (): ActionHistoryItem[] => {
  return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as ActionHistoryItem[];
};

export const addActionHistory = (
  title: string,
  description: string,
  icon = 'history',
  color = 'primary',
) => {
  const actions = getActionHistory();

  actions.unshift({
    id: Date.now(),
    title,
    description,
    dateTime: new Date().toLocaleString('es-PY', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    icon,
    color,
  });

  localStorage.setItem(STORAGE_KEY, JSON.stringify(actions));
};

export const clearActionHistory = (): void => {
  localStorage.removeItem(STORAGE_KEY);
};