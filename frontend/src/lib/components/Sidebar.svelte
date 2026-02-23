<script lang="ts">
	import { chatSessions } from '$lib/stores/chat';

	let { onNewResearch, onSelectSession, activeSessionId } : {
		onNewResearch: () => void;
		onSelectSession: (id: string) => void;
		activeSessionId: string | null;
	} = $props();

	let sessions = $state<any[]>([]);
	let hoveredId = $state<string | null>(null);

	$effect(() => {
		const unsub = chatSessions.subscribe((s) => {
			sessions = s;
		});
		return unsub;
	});

	function formatDate(iso: string): string {
		const d = new Date(iso);
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
		if (diffDays === 0) return '今日';
		if (diffDays === 1) return '昨日';
		if (diffDays < 7) return `${diffDays}日前`;
		return d.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
	}

	function handleDelete(e: Event, id: string) {
		e.stopPropagation();
		chatSessions.deleteSession(id);
	}
</script>

<aside class="sidebar">
	<button class="new-research-btn" onclick={onNewResearch}>
		<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
			<path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
		</svg>
		新しい調査
	</button>

	<nav class="sessions-list">
		{#each sessions as session (session.id)}
			<div
				class="session-item"
				class:active={session.id === activeSessionId}
				role="button"
				tabindex="0"
				onclick={() => onSelectSession(session.id)}
				onkeydown={(e) => { if (e.key === 'Enter') onSelectSession(session.id); }}
				onmouseenter={() => hoveredId = session.id}
				onmouseleave={() => hoveredId = null}
			>
				<div class="session-info">
					<span class="session-title">{session.title}</span>
					<span class="session-date">{formatDate(session.created_at)}</span>
				</div>
				{#if hoveredId === session.id}
					<button class="delete-btn" onclick={(e) => handleDelete(e, session.id)} title="削除">
						<svg width="14" height="14" viewBox="0 0 14 14" fill="none">
							<path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
						</svg>
					</button>
				{/if}
			</div>
		{/each}
	</nav>
</aside>

<style>
	.sidebar {
		width: 260px;
		min-width: 260px;
		height: 100%;
		background: var(--bg-secondary);
		display: flex;
		flex-direction: column;
		padding: 12px;
		overflow-y: auto;
	}

	.new-research-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 10px 12px;
		border-radius: 8px;
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
		border: 1px solid var(--border);
		transition: background 0.15s;
		margin-bottom: 16px;
	}

	.new-research-btn:hover {
		background: var(--bg-tertiary);
	}

	.sessions-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
		overflow-y: auto;
	}

	.session-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px;
		border-radius: 8px;
		text-align: left;
		transition: background 0.15s;
		width: 100%;
	}

	.session-item:hover {
		background: var(--bg-tertiary);
	}

	.session-item.active {
		background: var(--bg-tertiary);
	}

	.session-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
		flex: 1;
	}

	.session-title {
		font-size: 13px;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.session-date {
		font-size: 11px;
		color: var(--text-muted);
	}

	.delete-btn {
		flex-shrink: 0;
		padding: 4px;
		border-radius: 4px;
		color: var(--text-muted);
		transition: color 0.15s, background 0.15s;
	}

	.delete-btn:hover {
		color: var(--error);
		background: rgba(239, 68, 68, 0.1);
	}
</style>
