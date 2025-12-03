// client/src/lib/stores.js
import { writable } from 'svelte/store';
import { get } from './api';

function createDayStore() {
  const { subscribe, set, update } = writable(null);

  return {
    subscribe,
    // Fetch data for a specific date (YYYY-MM-DD)
    load: async (dateStr) => {
      try {
        const data = await get('/day-summary', { date: dateStr });
        set(data);
      } catch (err) {
        console.error("Failed to load day summary:", err);
        set(null);
      }
    },
    // Optimistic update (optional, for later)
    refresh: () => update(n => n) 
  };
}

export const daySummary = createDayStore();