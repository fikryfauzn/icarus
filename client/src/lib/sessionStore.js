// client/src/lib/sessionStore.js
import { writable } from 'svelte/store';
import { get, post } from './api';

function createSessionStore() {
    // Initial state: loading is true so we don't flash the "Start" button unnecessarily
    const { subscribe, set, update } = writable({
        active: null,
        loading: true
    });

    return {
        subscribe,

        /**
         * Check if a session is currently running on the server.
         */
        checkActive: async () => {
            try {
                // endpoint: /api/sessions/active
                const session = await get('/sessions/active');
                update(s => ({ ...s, active: session, loading: false }));
            } catch (err) {
                console.error("Failed to check active session:", err);
                update(s => ({ ...s, loading: false }));
            }
        },

        /**
         * Start a new session.
         * @param {Object} payload - The snake_case data expected by Python
         */
        start: async (payload) => {
            // endpoint: /api/sessions
            const session = await post('/sessions', payload);
            update(s => ({ ...s, active: session }));
            return session;
        },

        /**
         * End the current session.
         * @param {number} sessionId
         * @param {Object} payload - The snake_case outcome data
         */
        stop: async (sessionId, payload) => {
            // endpoint: /api/sessions/<id>/end
            const session = await post(`/sessions/${sessionId}/end`, payload);
            // Clear active state immediately (Optimistic UI)
            update(s => ({ ...s, active: null }));
            return session;
        }
    };
}

export const sessionStore = createSessionStore();