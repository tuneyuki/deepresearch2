<script lang="ts">
	import { marked } from 'marked';

	let { role, content }: { role: 'user' | 'assistant'; content: string } = $props();

	let renderedHtml = $derived(
		role === 'assistant' ? marked.parse(content, { async: false }) as string : content
	);
</script>

<div class="message" class:user={role === 'user'} class:assistant={role === 'assistant'}>
	{#if role === 'assistant'}
		<div class="avatar">
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
				<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
			</svg>
		</div>
	{/if}
	<div class="content">
		{#if role === 'assistant'}
			<div class="markdown-body">{@html renderedHtml}</div>
		{:else}
			<div class="user-text">{content}</div>
		{/if}
	</div>
</div>

<style>
	.message {
		display: flex;
		gap: 16px;
		padding: 24px 0;
		max-width: 768px;
		margin: 0 auto;
		width: 100%;
	}

	.message.user {
		justify-content: flex-end;
	}

	.avatar {
		flex-shrink: 0;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: var(--accent);
		display: flex;
		align-items: center;
		justify-content: center;
		color: white;
	}

	.content {
		min-width: 0;
		flex: 1;
		max-width: 100%;
	}

	.user-text {
		background: var(--bg-tertiary);
		padding: 12px 16px;
		border-radius: 18px;
		display: inline-block;
		max-width: 80%;
		float: right;
		font-size: 15px;
		line-height: 1.5;
	}

	.message.user .content {
		display: flex;
		justify-content: flex-end;
	}

	/* Markdown styles */
	.markdown-body {
		font-size: 15px;
		line-height: 1.7;
		color: var(--text-primary);
	}

	.markdown-body :global(h1) {
		font-size: 1.6em;
		font-weight: 700;
		margin: 24px 0 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.markdown-body :global(h2) {
		font-size: 1.35em;
		font-weight: 600;
		margin: 20px 0 10px;
	}

	.markdown-body :global(h3) {
		font-size: 1.15em;
		font-weight: 600;
		margin: 16px 0 8px;
	}

	.markdown-body :global(p) {
		margin: 10px 0;
	}

	.markdown-body :global(ul),
	.markdown-body :global(ol) {
		margin: 10px 0;
		padding-left: 24px;
	}

	.markdown-body :global(li) {
		margin: 4px 0;
	}

	.markdown-body :global(code) {
		background: var(--bg-secondary);
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 0.9em;
		font-family: 'Consolas', 'Monaco', monospace;
	}

	.markdown-body :global(pre) {
		background: var(--bg-secondary);
		padding: 16px;
		border-radius: 8px;
		overflow-x: auto;
		margin: 12px 0;
	}

	.markdown-body :global(pre code) {
		background: none;
		padding: 0;
		font-size: 0.85em;
	}

	.markdown-body :global(blockquote) {
		border-left: 3px solid var(--accent);
		padding-left: 16px;
		margin: 12px 0;
		color: var(--text-secondary);
	}

	.markdown-body :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: 12px 0;
	}

	.markdown-body :global(th),
	.markdown-body :global(td) {
		border: 1px solid var(--border);
		padding: 8px 12px;
		text-align: left;
	}

	.markdown-body :global(th) {
		background: var(--bg-secondary);
		font-weight: 600;
	}

	.markdown-body :global(hr) {
		border: none;
		border-top: 1px solid var(--border);
		margin: 20px 0;
	}

	.markdown-body :global(a) {
		color: var(--accent);
	}

	.markdown-body :global(strong) {
		font-weight: 600;
	}
</style>
