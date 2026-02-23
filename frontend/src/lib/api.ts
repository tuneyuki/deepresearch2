const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface TaskInfo {
	id: string;
	status: 'pending' | 'running' | 'completed' | 'failed';
	progress: number;
	messages: Array<{ role: string; content: string; timestamp?: string }>;
	result_url: string | null;
	error: string | null;
}

export interface ProgressEvent {
	event_type: string;
	message: string;
	progress: number;
	data?: any;
}

export async function startResearch(query: string): Promise<{ task_id: string }> {
	const res = await fetch(`${API_BASE}/research`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ query })
	});
	if (!res.ok) {
		throw new Error(`Failed to start research: ${res.statusText}`);
	}
	return res.json();
}

export async function getTaskStatus(taskId: string): Promise<TaskInfo> {
	const res = await fetch(`${API_BASE}/research/${taskId}`);
	if (!res.ok) {
		throw new Error(`Failed to get task status: ${res.statusText}`);
	}
	return res.json();
}

export function subscribeToTask(
	taskId: string,
	onEvent: (event: ProgressEvent) => void,
	onDone?: () => void
): EventSource {
	const es = new EventSource(`${API_BASE}/research/${taskId}/stream`);
	es.onmessage = (e) => {
		const data = JSON.parse(e.data);
		onEvent(data);
		if (data.event_type === 'completed' || data.event_type === 'failed') {
			es.close();
			onDone?.();
		}
	};
	es.onerror = () => {
		es.close();
		onDone?.();
	};
	return es;
}

export async function cancelResearch(taskId: string): Promise<void> {
	await fetch(`${API_BASE}/research/${taskId}/cancel`, { method: 'POST' });
}
