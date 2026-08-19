<script lang="ts">
	let {
		id,
		value = $bindable(''),
		placeholder = ''
	}: { id: string; value?: string; placeholder?: string } = $props();

	let visible = $state(false);
</script>

<div class="secret">
	<input {id} type={visible ? 'text' : 'password'} bind:value {placeholder} />
	<button
		type="button"
		class="toggle"
		onclick={() => (visible = !visible)}
		aria-label={visible ? 'Hide value' : 'Show value'}
		aria-pressed={visible}
		title={visible ? 'Hide' : 'Show'}
	>
		{#if visible}
			<!-- eye-off -->
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="18"
				height="18"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
				<path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
				<path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
				<line x1="2" y1="2" x2="22" y2="22" />
			</svg>
		{:else}
			<!-- eye -->
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="18"
				height="18"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
				<circle cx="12" cy="12" r="3" />
			</svg>
		{/if}
	</button>
</div>

<style>
	.secret {
		position: relative;
		display: flex;
		align-items: center;
	}

	.secret input {
		width: 100%;
		padding-right: 44px;
	}

	.toggle {
		position: absolute;
		right: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		padding: 0;
		border: none;
		background: transparent;
		color: var(--mid-gray);
		cursor: pointer;
	}

	.toggle:hover,
	.toggle:focus-visible {
		color: var(--ink);
	}
</style>
