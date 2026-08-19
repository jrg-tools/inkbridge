<script lang="ts">
	import { browser } from '$app/environment';
	import SecretInput from '$lib/SecretInput.svelte';

	interface Status {
		version: string;
		ip: string;
		mode: 'AP' | 'STA';
		rssi: number;
		freeHeap: number;
		uptime: number;
	}

	interface TransferSettings {
		wifiSsid: string;
		haHost: string;
		haPort: number;
		haEntities: string;
	}

	interface DeviceSettings {
		language: string;
		apSsid: string;
		apPassword: string;
	}

	type Section = 'wifi' | 'ha' | 'device';
	type ConnectionState = 'unknown' | 'checking' | 'connected' | 'disconnected';

	const sections: { id: Section; label: string }[] = [
		{ id: 'wifi', label: 'Wi-Fi' },
		{ id: 'ha', label: 'Home Assistant' },
		{ id: 'device', label: 'Device' }
	];

	const POLL_MS = 5000;

	let connection: ConnectionState = $state('unknown');
	let status = $state<Status | null>(null);
	let transfer = $state<TransferSettings>({
		wifiSsid: '',
		haHost: '',
		haPort: 8123,
		haEntities: ''
	});
	let deviceSettings = $state<DeviceSettings>({ language: 'en', apSsid: '', apPassword: '' });
	// Secrets are never returned by the API; only sent when the user types one.
	let wifiPassword = $state('');
	let haToken = $state('');
	let message = $state('');
	let error = $state(false);
	let saving = $state(false);
	let section = $state<Section>('wifi');

	const statusLabel = $derived.by(() => {
		switch (connection) {
			case 'connected':
				return `\u25CF INKBRIDGE ${status?.mode === 'AP' ? 'HOTSPOT' : 'CONNECTED'}`;
			case 'checking':
				return '\u25CC SEARCHING FOR DEVICE';
			case 'disconnected':
				return '\u25CB DEVICE OFFLINE';
			default:
				return '\u25CB DEVICE';
		}
	});

	// Device detection polling.
	async function checkDevice() {
		if (!browser || document.visibilityState === 'hidden') return;
		if (connection === 'unknown') connection = 'checking';
		try {
			const res = await fetch('/api/status');
			if (!res.ok) throw new Error();
			status = await res.json();
			connection = 'connected';
		} catch {
			status = null;
			connection = 'disconnected';
		}
	}

	$effect(() => {
		if (!browser) return;
		checkDevice();
		loadSettings();
		const timer = setInterval(checkDevice, POLL_MS);
		return () => clearInterval(timer);
	});

	async function loadSettings() {
		try {
			const res = await fetch('/api/settings');
			const data = await res.json();
			if (data.transfer) transfer = data.transfer;
			if (data.settings) deviceSettings = data.settings;
		} catch {
			message = 'Could not load settings.';
			error = true;
		}
	}

	async function save(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		message = '';
		error = false;

		const transferBody: Record<string, string | number> = { ...transfer };
		if (wifiPassword) transferBody.wifiPassword = wifiPassword;
		if (haToken) transferBody.haToken = haToken;
		const body = { transfer: transferBody, settings: { ...deviceSettings } };

		try {
			const res = await fetch('/api/settings', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (!res.ok) throw new Error(await res.text());
			message = 'Saved. Restarting device\u2026';
			await fetch('/api/restart', { method: 'POST' });
		} catch (e) {
			message = `Save failed: ${e instanceof Error ? e.message : e}`;
			error = true;
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>InkBridge Setup</title>
	<meta name="description" content="Configure your InkBridge device." />
</svelte:head>

<div class="app">
	<header class="header">
		<h1>InkBridge</h1>
		<span class="status status--{connection}" role="status" aria-live="polite">{statusLabel}</span>
	</header>

	<nav class="menu" aria-label="Sections">
		{#each sections as s (s.id)}
			<button type="button" class:active={section === s.id} onclick={() => (section = s.id)}>
				{s.label}
			</button>
		{/each}
	</nav>

	<form onsubmit={save}>
		{#if section === 'wifi'}
			<section class="panel" aria-label="Wi-Fi">
				<h2 class="section-title">Wi-Fi</h2>
				<div class="field">
					<label for="wifi-ssid">Network name (SSID)</label>
					<input id="wifi-ssid" type="text" bind:value={transfer.wifiSsid} />
				</div>
				<div class="field">
					<label for="wifi-password">Password</label>
					<SecretInput id="wifi-password" bind:value={wifiPassword} placeholder="(unchanged)" />
				</div>
				<p class="hint-small">The stored password is never shown. Leave blank to keep it.</p>
			</section>
		{:else if section === 'ha'}
			<section class="panel" aria-label="Home Assistant">
				<h2 class="section-title">Home Assistant</h2>
				<div class="field">
					<label for="ha-host">Host</label>
					<input id="ha-host" type="text" bind:value={transfer.haHost} placeholder="homeassistant.local" />
				</div>
				<div class="field">
					<label for="ha-port">Port</label>
					<input id="ha-port" type="number" bind:value={transfer.haPort} min="1" max="65535" />
				</div>
				<div class="field">
					<label for="ha-token">Access token</label>
					<SecretInput id="ha-token" bind:value={haToken} placeholder="(unchanged)" />
				</div>
				<div class="field">
					<label for="ha-entities">Entities (comma-separated)</label>
					<input
						id="ha-entities"
						type="text"
						bind:value={transfer.haEntities}
						placeholder="sensor.temp, light.desk"
					/>
				</div>
				<p class="hint-small">The stored token is never shown. Leave blank to keep it.</p>
			</section>
		{:else}
			<section class="panel" aria-label="Device">
				<h2 class="section-title">Device</h2>
				<div class="field">
					<label for="language">Language</label>
					<select id="language" bind:value={deviceSettings.language}>
						<option value="en">English</option>
						<option value="es">Espa&ntilde;ol</option>
					</select>
				</div>
				<div class="field">
					<label for="ap-ssid">Hotspot name</label>
					<input id="ap-ssid" type="text" bind:value={deviceSettings.apSsid} />
				</div>
				<div class="field">
					<label for="ap-password">Hotspot password</label>
					<SecretInput
						id="ap-password"
						bind:value={deviceSettings.apPassword}
						placeholder="(empty = regenerate)"
					/>
				</div>
				<p class="hint-small">Hotspot credentials are shown on the device screen.</p>
			</section>
		{/if}

		<div class="actions">
			<button type="submit" class="btn btn--primary" disabled={saving}>
				{saving ? 'Saving\u2026' : 'Save & Restart'}
			</button>
			{#if message}
				<p class="message" class:error role="status" aria-live="polite">{message}</p>
			{/if}
		</div>
	</form>

	<footer class="footer">
		{#if status}
			v{status.version} &middot; {status.ip}
		{/if}
	</footer>
</div>

<style>
	.app {
		max-width: 560px;
		margin: 0 auto;
		padding: 0 16px 40px;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 0;
		border-bottom: 2px solid var(--ink);
		margin-bottom: 20px;
	}

	.header h1 {
		font-size: 18px;
		margin: 0;
	}

	.status {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.1em;
		white-space: nowrap;
		color: var(--mid-gray);
	}

	.status--connected {
		color: var(--ink);
	}

	.menu {
		display: flex;
		gap: 10px;
		margin-bottom: 16px;
	}

	.menu button {
		flex: 1;
		min-height: 44px;
		padding: 0 8px;
		border: 1.5px solid var(--ink);
		border-radius: 4px;
		background: var(--paper);
		color: var(--ink);
		font-family: var(--font);
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		cursor: pointer;
		box-shadow: 2px 2px 0 var(--light-gray);
		transition:
			transform 60ms ease,
			box-shadow 60ms ease;
		user-select: none;
	}

	.menu button:active {
		transform: translate(2px, 2px);
		box-shadow: none;
	}

	.menu button.active {
		background: var(--ink);
		color: var(--paper);
		box-shadow: none;
	}

	.field {
		margin: 12px 0;
	}

	.hint-small {
		font-size: 12px;
		color: var(--mid-gray);
		margin: 4px 0 0;
	}

	.actions {
		margin-top: 16px;
		display: grid;
		gap: 10px;
	}

	.message {
		margin: 0;
		font-size: 13px;
		color: var(--dark-gray);
		text-align: center;
	}

	.message.error {
		color: var(--ink);
		font-weight: 700;
	}

	.footer {
		margin-top: 24px;
		padding-top: 8px;
		border-top: 1px solid var(--light-gray);
		text-align: center;
		font-size: 12px;
		letter-spacing: 0.08em;
		color: var(--mid-gray);
	}
</style>
