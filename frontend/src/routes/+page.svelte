<script lang="ts">
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatMessage from '$lib/components/ChatMessage.svelte';
	import ChatInput from '$lib/components/ChatInput.svelte';
	import ResearchProgress from '$lib/components/ResearchProgress.svelte';
	import { chatSessions, type ChatSession } from '$lib/stores/chat';
	import { researchState, resetResearch } from '$lib/stores/research';
	import { startResearch, subscribeToTask, cancelResearch, getTaskStatus } from '$lib/api';

	let sidebarOpen = $state(true);
	let activeSessionId = $state<string | null>(null);
	let currentMessages = $state<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
	let isRunning = $state(false);
	let errorMsg = $state<string | null>(null);
	let messagesEndEl: HTMLDivElement | undefined = $state();
	let currentEventSource: EventSource | null = $state(null);
	let sessions = $state<ChatSession[]>([]);
	let reconnectedTaskIds = new Set<string>();

	$effect(() => {
		const unsub = chatSessions.subscribe((s) => {
			sessions = s;
		});
		return unsub;
	});

	// Sync messages from store to UI when selecting a session
	$effect(() => {
		if (activeSessionId) {
			const session = sessions.find((s) => s.id === activeSessionId);
			if (session) {
				currentMessages = [...session.messages];
				if (session.status !== 'running') {
					isRunning = false;
				}
			}
		}
	});

	$effect(() => {
		if (messagesEndEl) {
			messagesEndEl.scrollIntoView({ behavior: 'smooth' });
		}
	});

	// Reconnect to active tasks on mount (run once)
	$effect(() => {
		const running = sessions.find((s) => s.status === 'running');
		if (running && !reconnectedTaskIds.has(running.task_id)) {
			reconnectedTaskIds.add(running.task_id);
			activeSessionId = running.id;
			reconnectToTask(running);
		}
	});

	function reconnectToTask(session: ChatSession) {
		isRunning = true;
		researchState.set({
			activeTaskId: session.task_id,
			progress: 0,
			currentStep: '再接続中...',
			steps: [
				{ message: 'クエリを解析中...', completed: true },
				{ message: '検索中...', completed: false },
				{ message: '分析中...', completed: false },
				{ message: 'レポート生成中...', completed: false }
			]
		});

		getTaskStatus(session.task_id)
			.then((status) => {
				if (status.status === 'completed' || status.status === 'failed') {
					finishTask(session.id, status.status, status.result_url ?? null, status.error ?? null);
					return;
				}
				subscribeToEvents(session.id, session.task_id);
			})
			.catch(() => {
				finishTask(session.id, 'failed', null, '再接続に失敗しました');
			});
	}

	/** Single place to mark a task as done and update the store once */
	function finishTask(sessionId: string, status: string, resultUrl: string | null, error: string | null) {
		if (status === 'completed' && resultUrl) {
			// Fetch report content from backend task info
			const session = sessions.find((s) => s.id === sessionId);
			if (session) {
				getTaskStatus(session.task_id).then((info) => {
					// Find the last substantive assistant message (the report)
					const reportMsg = info.messages?.filter((m: any) => m.role === 'assistant' && m.content.length > 200).pop();
					if (reportMsg && !session.messages.some((m) => m.content === reportMsg.content)) {
						chatSessions.updateSession(sessionId, {
							messages: [...session.messages, { role: 'assistant', content: reportMsg.content }],
							status: 'completed',
							result_url: resultUrl
						});
					} else {
						chatSessions.updateSession(sessionId, { status: 'completed', result_url: resultUrl });
					}
					isRunning = false;
					resetResearch();
				}).catch(() => {
					chatSessions.updateSession(sessionId, { status: 'completed', result_url: resultUrl });
					isRunning = false;
					resetResearch();
				});
			}
		} else if (status === 'failed') {
			chatSessions.updateSession(sessionId, { status: 'failed' });
			errorMsg = error || '調査に失敗しました';
			isRunning = false;
			resetResearch();
		} else {
			chatSessions.updateSession(sessionId, { status: status as any });
			isRunning = false;
			resetResearch();
		}
	}

	function handleNewResearch() {
		activeSessionId = null;
		currentMessages = [];
		isRunning = false;
		errorMsg = null;
		resetResearch();
		if (currentEventSource) {
			currentEventSource.close();
			currentEventSource = null;
		}
	}

	function handleSelectSession(id: string) {
		if (currentEventSource && !isRunning) {
			currentEventSource.close();
			currentEventSource = null;
		}
		activeSessionId = id;
		errorMsg = null;
	}

	async function handleSubmit(query: string) {
		errorMsg = null;
		currentMessages = [{ role: 'user', content: query }];

		try {
			const { task_id } = await startResearch(query);
			const session = chatSessions.createSession(query, task_id);
			activeSessionId = session.id;
			isRunning = true;

			researchState.set({
				activeTaskId: task_id,
				progress: 0,
				currentStep: 'クエリを解析中...',
				steps: [
					{ message: 'クエリを解析中...', completed: false },
					{ message: '検索中...', completed: false },
					{ message: '分析中...', completed: false },
					{ message: 'レポート生成中...', completed: false }
				]
			});

			subscribeToEvents(session.id, task_id);
		} catch (err) {
			errorMsg = err instanceof Error ? err.message : '調査の開始に失敗しました';
			isRunning = false;
		}
	}

	function subscribeToEvents(sessionId: string, taskId: string) {
		// Close any existing connection first
		if (currentEventSource) {
			currentEventSource.close();
		}

		let completed = false;

		currentEventSource = subscribeToTask(
			taskId,
			(event) => {
				researchState.update((s) => {
					const newState = { ...s, progress: event.progress };

					if (event.message) {
						newState.currentStep = event.message;
					}

					// Update step indicators based on progress
					if (event.progress >= 5) {
						newState.steps = s.steps.map((step, i) => ({ ...step, completed: i === 0 }));
					}
					if (event.progress >= 10) {
						newState.steps = s.steps.map((step, i) => ({ ...step, completed: i <= 1 }));
					}
					if (event.progress >= 50) {
						newState.steps = s.steps.map((step, i) => ({ ...step, completed: i <= 2 }));
					}
					if (event.progress >= 80) {
						newState.steps = s.steps.map((step, i) => ({ ...step, completed: i <= 3 }));
					}

					if (event.event_type === 'completed') {
						newState.steps = s.steps.map((step) => ({ ...step, completed: true }));
						newState.progress = 100;
					}

					return newState;
				});

				if (event.event_type === 'completed' && event.data?.report && !completed) {
					completed = true;
					// Snapshot the user message before updating
					const userMsg = currentMessages.find((m) => m.role === 'user');
					const msgs = userMsg
						? [userMsg, { role: 'assistant' as const, content: event.data.report }]
						: [{ role: 'assistant' as const, content: event.data.report }];
					chatSessions.updateSession(sessionId, {
						messages: msgs,
						status: 'completed',
						result_url: event.data?.result_url || null
					});
					isRunning = false;
					resetResearch();
				} else if (event.event_type === 'failed' && !completed) {
					completed = true;
					chatSessions.updateSession(sessionId, { status: 'failed' });
					errorMsg = event.message || '調査に失敗しました';
					isRunning = false;
					resetResearch();
				}
			},
			() => {
				// onDone - only fetch if we haven't already handled completion
				if (!completed && isRunning) {
					getTaskStatus(taskId).then((status) => {
						if (completed) return; // double-check
						completed = true;
						finishTask(sessionId, status.status, status.result_url, status.error);
					}).catch(() => {
						if (!completed) {
							completed = true;
							isRunning = false;
							resetResearch();
						}
					});
				}
			}
		);
	}

	async function handleCancel() {
		if (!activeSessionId) return;
		const session = sessions.find((s) => s.id === activeSessionId);
		if (!session) return;

		try {
			await cancelResearch(session.task_id);
		} catch {
			// ignore cancel errors
		}

		if (currentEventSource) {
			currentEventSource.close();
			currentEventSource = null;
		}

		chatSessions.updateSession(activeSessionId, { status: 'failed' });
		isRunning = false;
		resetResearch();
		errorMsg = '調査がキャンセルされました';
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

<div class="page-layout">
	{#if sidebarOpen}
		<Sidebar
			onNewResearch={handleNewResearch}
			onSelectSession={handleSelectSession}
			{activeSessionId}
		/>
	{/if}

	<main class="main-content">
		<header class="top-bar">
			<button class="sidebar-toggle" onclick={toggleSidebar} title={sidebarOpen ? 'サイドバーを閉じる' : 'サイドバーを開く'}>
				<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
					<path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
				</svg>
			</button>
			<h1 class="app-title">Deep Research</h1>
		</header>

		<div class="messages-area">
			{#if currentMessages.length === 0 && !isRunning}
				<div class="empty-state">
					<div class="empty-icon">
						<svg width="48" height="48" viewBox="0 0 24 24" fill="none">
							<path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="var(--text-muted)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					</div>
					<h2>Deep Research</h2>
					<p>調査したいトピックを入力してください。<br />AIが詳細なリサーチレポートを作成します。</p>
				</div>
			{:else}
				<div class="messages-list">
					{#each currentMessages as msg}
						<ChatMessage role={msg.role} content={msg.content} />
					{/each}

					{#if isRunning}
						<ResearchProgress oncancel={handleCancel} />
					{/if}

					{#if errorMsg}
						<div class="error-message">
							<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
								<circle cx="8" cy="8" r="7" stroke="var(--error)" stroke-width="1.5"/>
								<path d="M8 5v3M8 10v1" stroke="var(--error)" stroke-width="1.5" stroke-linecap="round"/>
							</svg>
							{errorMsg}
						</div>
					{/if}

					<div bind:this={messagesEndEl}></div>
				</div>
			{/if}
		</div>

		<ChatInput onsubmit={handleSubmit} disabled={isRunning} />
	</main>
</div>

<style>
	.page-layout {
		display: flex;
		height: 100vh;
		overflow: hidden;
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
		height: 100vh;
	}

	.top-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.sidebar-toggle {
		padding: 6px;
		border-radius: 6px;
		color: var(--text-secondary);
		transition: color 0.15s, background 0.15s;
	}

	.sidebar-toggle:hover {
		color: var(--text-primary);
		background: var(--bg-tertiary);
	}

	.app-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.messages-area {
		flex: 1;
		overflow-y: auto;
		padding: 0 24px;
	}

	.messages-list {
		padding-bottom: 24px;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		text-align: center;
		gap: 16px;
		color: var(--text-muted);
	}

	.empty-icon {
		margin-bottom: 8px;
	}

	.empty-state h2 {
		font-size: 24px;
		font-weight: 700;
		color: var(--text-primary);
	}

	.empty-state p {
		font-size: 15px;
		line-height: 1.6;
		max-width: 400px;
	}

	.error-message {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		border-radius: 12px;
		color: var(--error);
		font-size: 14px;
		max-width: 768px;
		margin: 12px auto;
	}

	@media (max-width: 768px) {
		.messages-area {
			padding: 0 12px;
		}
	}
</style>
