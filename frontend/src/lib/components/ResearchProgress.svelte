<script lang="ts">
	import { researchState, type ResearchStep } from '$lib/stores/research';

	let { oncancel }: { oncancel: () => void } = $props();

	let state = $state({ activeTaskId: null as string | null, progress: 0, currentStep: '', steps: [] as ResearchStep[] });

	$effect(() => {
		const unsub = researchState.subscribe((s) => {
			state = s;
		});
		return unsub;
	});
</script>

<div class="progress-container">
	<div class="progress-header">
		<span class="progress-label">調査中...</span>
		<span class="progress-percent">{Math.round(state.progress)}%</span>
	</div>

	<div class="progress-bar-track">
		<div class="progress-bar-fill" style="width: {state.progress}%"></div>
	</div>

	<div class="steps">
		{#each state.steps as step, i}
			<div class="step" class:completed={step.completed} class:active={!step.completed && i === state.steps.findIndex(s => !s.completed)}>
				<div class="step-indicator">
					{#if step.completed}
						<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
							<path d="M3 8l3 3 7-7" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					{:else if !step.completed && i === state.steps.findIndex(s => !s.completed)}
						<div class="spinner"></div>
					{:else}
						<div class="dot"></div>
					{/if}
				</div>
				<span class="step-text">{step.message}</span>
			</div>
		{/each}
	</div>

	{#if state.currentStep}
		<div class="current-step">
			<span class="pulse-dot"></span>
			{state.currentStep}
		</div>
	{/if}

	<button class="cancel-btn" onclick={oncancel}>
		キャンセル
	</button>
</div>

<style>
	.progress-container {
		max-width: 560px;
		margin: 24px auto;
		padding: 24px;
		background: var(--bg-tertiary);
		border-radius: 16px;
		border: 1px solid var(--border);
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.progress-label {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-primary);
	}

	.progress-percent {
		font-size: 14px;
		font-weight: 600;
		color: var(--accent);
	}

	.progress-bar-track {
		height: 4px;
		background: var(--bg-secondary);
		border-radius: 2px;
		overflow: hidden;
		margin-bottom: 20px;
	}

	.progress-bar-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.4s ease;
	}

	.steps {
		display: flex;
		flex-direction: column;
		gap: 12px;
		margin-bottom: 16px;
	}

	.step {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.step-indicator {
		flex-shrink: 0;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.step-text {
		font-size: 14px;
		color: var(--text-secondary);
		transition: color 0.2s;
	}

	.step.completed .step-text {
		color: var(--text-primary);
	}

	.step.active .step-text {
		color: var(--text-primary);
		font-weight: 500;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text-muted);
	}

	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid var(--bg-secondary);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.current-step {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		color: var(--text-secondary);
		padding: 8px 0;
	}

	.pulse-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--accent);
		animation: pulse 1.5s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.5; transform: scale(0.8); }
	}

	.cancel-btn {
		display: block;
		margin: 12px auto 0;
		padding: 8px 20px;
		font-size: 13px;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: 8px;
		transition: color 0.15s, border-color 0.15s;
	}

	.cancel-btn:hover {
		color: var(--error);
		border-color: var(--error);
	}
</style>
