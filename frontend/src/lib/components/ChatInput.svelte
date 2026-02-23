<script lang="ts">
	let { onsubmit, disabled = false }: { onsubmit: (query: string) => void; disabled?: boolean } = $props();

	let text = $state('');
	let textareaEl: HTMLTextAreaElement | undefined = $state();

	function autoResize() {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = Math.min(textareaEl.scrollHeight, 200) + 'px';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submit();
		}
	}

	function submit() {
		const query = text.trim();
		if (!query || disabled) return;
		onsubmit(query);
		text = '';
		if (textareaEl) {
			textareaEl.style.height = 'auto';
		}
	}
</script>

<div class="input-container">
	<div class="input-wrapper">
		<textarea
			bind:this={textareaEl}
			bind:value={text}
			oninput={autoResize}
			onkeydown={handleKeydown}
			placeholder="調査したいことを入力してください..."
			rows="1"
			{disabled}
		></textarea>
		<button class="send-btn" onclick={submit} disabled={disabled || !text.trim()} title="送信">
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
				<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</button>
	</div>
</div>

<style>
	.input-container {
		padding: 16px 24px 24px;
		max-width: 768px;
		margin: 0 auto;
		width: 100%;
	}

	.input-wrapper {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		background: var(--bg-tertiary);
		border-radius: 16px;
		padding: 12px 16px;
		border: 1px solid var(--border);
		transition: border-color 0.15s;
	}

	.input-wrapper:focus-within {
		border-color: var(--accent);
	}

	textarea {
		flex: 1;
		resize: none;
		font-size: 15px;
		line-height: 1.5;
		color: var(--text-primary);
		min-height: 24px;
		max-height: 200px;
	}

	textarea::placeholder {
		color: var(--text-muted);
	}

	textarea:disabled {
		opacity: 0.5;
	}

	.send-btn {
		flex-shrink: 0;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--accent);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background 0.15s, opacity 0.15s;
	}

	.send-btn:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.send-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
