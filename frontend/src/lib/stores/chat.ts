import { writable } from 'svelte/store';

export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
}

export interface ChatSession {
	id: string;
	title: string;
	task_id: string;
	query: string;
	messages: ChatMessage[];
	status: 'running' | 'completed' | 'failed';
	result_url: string | null;
	created_at: string;
}

function loadSessions(): ChatSession[] {
	if (typeof localStorage === 'undefined') return [];
	try {
		const data = localStorage.getItem('chat_sessions');
		return data ? JSON.parse(data) : [];
	} catch {
		return [];
	}
}

function saveSessions(sessions: ChatSession[]) {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem('chat_sessions', JSON.stringify(sessions));
}

const { subscribe, set, update } = writable<ChatSession[]>(loadSessions());

subscribe((sessions) => {
	saveSessions(sessions);
});

export const chatSessions = {
	subscribe,
	createSession(query: string, taskId: string): ChatSession {
		const session: ChatSession = {
			id: crypto.randomUUID(),
			title: query.slice(0, 50),
			task_id: taskId,
			query,
			messages: [{ role: 'user', content: query }],
			status: 'running',
			result_url: null,
			created_at: new Date().toISOString()
		};
		update((sessions) => [session, ...sessions]);
		return session;
	},
	updateSession(id: string, updates: Partial<ChatSession>) {
		update((sessions) =>
			sessions.map((s) => (s.id === id ? { ...s, ...updates } : s))
		);
	},
	deleteSession(id: string) {
		update((sessions) => sessions.filter((s) => s.id !== id));
	},
	getSession(id: string): ChatSession | undefined {
		let result: ChatSession | undefined;
		subscribe((sessions) => {
			result = sessions.find((s) => s.id === id);
		})();
		return result;
	}
};
