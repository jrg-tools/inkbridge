<script lang="ts">
	import { browser } from '$app/environment';
	import SecretInput from '$lib/SecretInput.svelte';
	import Lightbulb from '@lucide/svelte/icons/lightbulb';
	import ToggleRight from '@lucide/svelte/icons/toggle-right';
	import Moon from '@lucide/svelte/icons/moon';
	import Lock from '@lucide/svelte/icons/lock';
	import Fan from '@lucide/svelte/icons/fan';
	import Thermometer from '@lucide/svelte/icons/thermometer';
	import Tv from '@lucide/svelte/icons/tv';
	import Zap from '@lucide/svelte/icons/zap';
	import type { Component } from 'svelte';

	interface Status {
		version: string;
		ip: string;
		mode: 'AP' | 'STA';
		rssi: number;
		freeHeap: number;
		uptime: number;
	}

	interface ScriptButtonSetting {
		label: string;
		id: string;
		icon: string;
	}

	interface WifiNetworkSetting {
		ssid: string;
		password: string;
	}

	interface TransferSettings {
		wifiNetworks: WifiNetworkSetting[];
		haHost: string;
		haPort: number;
		haEntities: string;
		haScripts: ScriptButtonSetting[];
	}

	interface DeviceSettings {
		language: string;
		fontFamily: string;
		apSsid: string;
		apPassword: string;
	}

	type Section = 'wifi' | 'ha' | 'device';
	type ConnectionState = 'unknown' | 'checking' | 'connected' | 'disconnected';

	// Keys must match what the device's Icons::byKey() understands — it falls
	// back to the generic bolt/zap icon for anything else.
	const ICON_OPTIONS: { value: string; label: string; Icon: Component }[] = [
		{ value: 'bulb', label: 'Light', Icon: Lightbulb },
		{ value: 'toggle', label: 'Switch', Icon: ToggleRight },
		{ value: 'lock', label: 'Lock', Icon: Lock },
		{ value: 'fan', label: 'Fan', Icon: Fan },
		{ value: 'thermometer', label: 'Climate', Icon: Thermometer },
		{ value: 'tv', label: 'Media', Icon: Tv },
		{ value: 'moon', label: 'Sleep', Icon: Moon },
		{ value: 'bolt', label: 'Other', Icon: Zap }
	];

	// Keys must match what UITheme::applyFontFamily() on the device understands.
	const FONT_OPTIONS: { value: string; label: string }[] = [
		{ value: 'notosans', label: 'Noto Sans (default)' },
		{ value: 'helvetica', label: 'Helvetica' },
		{ value: 'lucida', label: 'Lucida Sans' },
		{ value: 'schoolbook', label: 'New Century Schoolbook' }
	];

	const sections: { id: Section; label: string }[] = [
		{ id: 'wifi', label: 'Wi-Fi' },
		{ id: 'ha', label: 'Home Assistant' },
		{ id: 'device', label: 'Device' }
	];

	const POLL_MS = 5000;

	let connection: ConnectionState = $state('unknown');
	let status = $state<Status | null>(null);
	let transfer = $state<TransferSettings>({
		wifiNetworks: [],
		haHost: '',
		haPort: 8123,
		haEntities: '',
		haScripts: []
	});
	let deviceSettings = $state<DeviceSettings>({
		language: 'en',
		fontFamily: 'notosans',
		apSsid: '',
		apPassword: ''
	});
	// Secrets are never returned by the API; only sent when the user types one.
	let haToken = $state('');
	let message = $state('');
	let error = $state(false);
	let saving = $state(false);
	let section = $state<Section>('wifi');
	let testingHa = $state(false);
	let haTestResult = $state<{ ok: boolean; message: string } | null>(null);

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
			if (data.transfer) {
				transfer = {
					...data.transfer,
					haScripts: data.transfer.haScripts ?? [],
					// The device never returns passwords; start each row blank so
					// saving without touching it keeps the stored one (matched by SSID).
					wifiNetworks: (data.transfer.wifiNetworks ?? []).map((n: { ssid: string }) => ({
						ssid: n.ssid,
						password: ''
					}))
				};
			}
			if (data.settings) deviceSettings = data.settings;
		} catch {
			message = 'Could not load settings.';
			error = true;
		}
	}

	// Hits Home Assistant's REST API directly from the browser — no round
	// trip through the device — using whatever is currently in the form
	// (host/port/token), whether or not it's been saved yet.
	async function testHaConnection() {
		haTestResult = null;

		const host = transfer.haHost.trim();
		if (!host) {
			haTestResult = { ok: false, message: 'Enter a host first.' };
			return;
		}
		if (!haToken) {
			haTestResult = { ok: false, message: 'Enter an access token first.' };
			return;
		}

		let scheme = 'http://';
		let bareHost = host;
		if (bareHost.startsWith('https://')) {
			scheme = 'https://';
			bareHost = bareHost.slice(8);
		} else if (bareHost.startsWith('http://')) {
			bareHost = bareHost.slice(7);
		}
		const port = transfer.haPort > 0 ? `:${transfer.haPort}` : '';
		const url = `${scheme}${bareHost}${port}/api/`;

		testingHa = true;
		try {
			const res = await fetch(url, { headers: { Authorization: `Bearer ${haToken}` } });
			if (res.ok) {
				haTestResult = { ok: true, message: 'Connected.' };
			} else if (res.status === 401) {
				haTestResult = { ok: false, message: 'Reached the server, but the token was rejected.' };
			} else {
				haTestResult = { ok: false, message: `Unexpected response: HTTP ${res.status}` };
			}
		} catch {
			haTestResult = {
				ok: false,
				message:
					'Could not reach it from this browser. Check the host/port, or enable CORS for this origin in Home Assistant (http.cors_allowed_origins).'
			};
		} finally {
			testingHa = false;
		}
	}

	function addScript() {
		transfer.haScripts.push({ label: '', id: '', icon: 'bolt' });
	}

	function removeScript(index: number) {
		transfer.haScripts.splice(index, 1);
	}

	function addWifiNetwork() {
		transfer.wifiNetworks.push({ ssid: '', password: '' });
	}

	function removeWifiNetwork(index: number) {
		transfer.wifiNetworks.splice(index, 1);
	}

	// Generic reorder-by-drag for both lists below — order matters for each:
	// scripts is the device's main-menu order, wifiNetworks is the connect
	// priority (first that connects wins).
	type ListKey = 'scripts' | 'wifi';
	let dragList = $state<ListKey | null>(null);
	let dragIndex = $state<number | null>(null);
	let dragOverIndex = $state<number | null>(null);

	// Kept generic (rather than looking the array up by key) so TypeScript
	// doesn't collapse it to the union of both item types.
	function reorder<T>(arr: T[], from: number, to: number) {
		if (to < 0 || to >= arr.length) return;
		const [item] = arr.splice(from, 1);
		arr.splice(to, 0, item);
	}

	function moveItem(key: ListKey, index: number, delta: number) {
		if (key === 'scripts') {
			reorder(transfer.haScripts, index, index + delta);
		} else {
			reorder(transfer.wifiNetworks, index, index + delta);
		}
	}

	function onDragStart(event: DragEvent, key: ListKey, index: number) {
		dragList = key;
		dragIndex = index;
		event.dataTransfer?.setData('text/plain', String(index));
		if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
	}

	function onDragOver(event: DragEvent, key: ListKey, index: number) {
		if (dragIndex === null || dragList !== key) return;
		event.preventDefault();
		if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
		dragOverIndex = index;
	}

	function onDrop(event: DragEvent, key: ListKey, index: number) {
		event.preventDefault();
		if (dragList === key && dragIndex !== null && dragIndex !== index) {
			if (key === 'scripts') {
				reorder(transfer.haScripts, dragIndex, index);
			} else {
				reorder(transfer.wifiNetworks, dragIndex, index);
			}
		}
		dragList = null;
		dragIndex = null;
		dragOverIndex = null;
	}

	function onDragEnd() {
		dragList = null;
		dragIndex = null;
		dragOverIndex = null;
	}

	async function save(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		message = '';
		error = false;

		const transferBody: Record<
			string,
			string | number | ScriptButtonSetting[] | WifiNetworkSetting[]
		> = { ...transfer };
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
				<p class="hint-small">
					The device tries these networks top to bottom and connects to the first one it
					reaches. Drag the handle (or use the arrows) to reorder.
				</p>
				{#each transfer.wifiNetworks as net, i (i)}
					<div
						class="list-row"
						class:drag-over={dragList === 'wifi' && dragOverIndex === i && dragIndex !== i}
						ondragover={(e) => onDragOver(e, 'wifi', i)}
						ondrop={(e) => onDrop(e, 'wifi', i)}
						ondragend={onDragEnd}
						role="group"
						aria-label="Network {i + 1}"
					>
						<div class="list-row-head">
							<span
								class="drag-handle"
								draggable="true"
								ondragstart={(e) => onDragStart(e, 'wifi', i)}
								ondragend={onDragEnd}
								title="Drag to reorder"
								aria-hidden="true"
							>
								&#10021;
							</span>
							<span class="list-row-index">#{i + 1}</span>
							<div class="move-buttons">
								<button
									type="button"
									class="btn btn--move"
									onclick={() => moveItem('wifi', i, -1)}
									disabled={i === 0}
									aria-label="Move up"
								>
									&#9650;
								</button>
								<button
									type="button"
									class="btn btn--move"
									onclick={() => moveItem('wifi', i, 1)}
									disabled={i === transfer.wifiNetworks.length - 1}
									aria-label="Move down"
								>
									&#9660;
								</button>
							</div>
							<button
								type="button"
								class="btn btn--remove"
								onclick={() => removeWifiNetwork(i)}
								aria-label="Remove network"
							>
								&times;
							</button>
						</div>
						<div class="field">
							<label for="wifi-ssid-{i}">Network name (SSID)</label>
							<input id="wifi-ssid-{i}" type="text" bind:value={net.ssid} />
						</div>
						<div class="field">
							<label for="wifi-password-{i}">Password</label>
							<SecretInput
								id="wifi-password-{i}"
								bind:value={net.password}
								placeholder="(unchanged)"
							/>
						</div>
					</div>
				{/each}
				<button type="button" class="btn btn--secondary" onclick={addWifiNetwork}>
					+ Add network
				</button>
				<p class="hint-small">The stored password is never shown. Leave blank to keep it.</p>
			</section>
		{:else if section === 'ha'}
			<section class="panel" aria-label="Home Assistant">
				<h2 class="section-title">Home Assistant</h2>
				<div class="field">
					<label for="ha-host">Host</label>
					<input
						id="ha-host"
						type="text"
						bind:value={transfer.haHost}
						placeholder="homeassistant.local or https://assistant.example.com"
					/>
				</div>
				<div class="field">
					<label for="ha-port">Port</label>
					<input id="ha-port" type="number" bind:value={transfer.haPort} min="0" max="65535" />
				</div>
				<p class="hint-small">
					Port 0 uses the scheme's default (443 for https, 80 for http) — set this to 0 if Host
					is a reverse-proxied https:// address with no separate port.
				</p>
				<div class="field">
					<label for="ha-token">Access token</label>
					<SecretInput id="ha-token" bind:value={haToken} placeholder="(unchanged)" />
				</div>
				<p class="hint-small">The stored token is never shown. Leave blank to keep it.</p>
				<div class="field">
					<button
						type="button"
						class="btn btn--secondary"
						disabled={testingHa}
						onclick={testHaConnection}
					>
						{testingHa ? 'Testing…' : 'Test connection'}
					</button>
					{#if haTestResult}
						<p class="hint-small test-result" class:error={!haTestResult.ok}>
							{haTestResult.ok ? '✓' : '✗'}
							{haTestResult.message}
						</p>
					{/if}
					<p class="hint-small">
						Tested directly from this browser, not through the device — the device's own
						connection may still differ.
					</p>
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

				<h3 class="subsection-title">Scripts</h3>
				<p class="hint-small">
					Each entry becomes a button in the device's main menu, in this order. Script ID is
					the part after "script." — the button calls script.turn_on for that entity. Drag the
					handle (or use the arrows) to reorder.
				</p>
				{#each transfer.haScripts as scriptBtn, i (i)}
					<div
						class="list-row"
						class:drag-over={dragList === 'scripts' && dragOverIndex === i && dragIndex !== i}
						ondragover={(e) => onDragOver(e, 'scripts', i)}
						ondrop={(e) => onDrop(e, 'scripts', i)}
						ondragend={onDragEnd}
						role="group"
						aria-label="Script {i + 1}"
					>
						<div class="list-row-head">
							<span
								class="drag-handle"
								draggable="true"
								ondragstart={(e) => onDragStart(e, 'scripts', i)}
								ondragend={onDragEnd}
								title="Drag to reorder"
								aria-hidden="true"
							>
								&#10021;
							</span>
							<span class="list-row-index">#{i + 1}</span>
							<div class="move-buttons">
								<button
									type="button"
									class="btn btn--move"
									onclick={() => moveItem('scripts', i, -1)}
									disabled={i === 0}
									aria-label="Move up"
								>
									&#9650;
								</button>
								<button
									type="button"
									class="btn btn--move"
									onclick={() => moveItem('scripts', i, 1)}
									disabled={i === transfer.haScripts.length - 1}
									aria-label="Move down"
								>
									&#9660;
								</button>
							</div>
							<button
								type="button"
								class="btn btn--remove"
								onclick={() => removeScript(i)}
								aria-label="Remove script"
							>
								&times;
							</button>
						</div>
						<div class="field">
							<label for="script-label-{i}">Name</label>
							<input
								id="script-label-{i}"
								type="text"
								bind:value={scriptBtn.label}
								placeholder="Sleep"
							/>
						</div>
						<div class="field">
							<label for="script-id-{i}">Script ID</label>
							<input
								id="script-id-{i}"
								type="text"
								bind:value={scriptBtn.id}
								placeholder="sleep_time"
							/>
						</div>
						<div class="field">
							<span class="field-label" id="script-icon-label-{i}">Icon</span>
							<div class="icon-picker" role="radiogroup" aria-labelledby="script-icon-label-{i}">
								{#each ICON_OPTIONS as opt (opt.value)}
									<button
										type="button"
										class="icon-option"
										class:active={scriptBtn.icon === opt.value}
										onclick={() => (scriptBtn.icon = opt.value)}
										role="radio"
										aria-checked={scriptBtn.icon === opt.value}
										title={opt.label}
									>
										<opt.Icon size={18} strokeWidth={2} />
									</button>
								{/each}
							</div>
						</div>
					</div>
				{/each}
				<button type="button" class="btn btn--secondary" onclick={addScript}>
					+ Add script
				</button>
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
					<label for="font-family">Font family</label>
					<select id="font-family" bind:value={deviceSettings.fontFamily}>
						{#each FONT_OPTIONS as opt (opt.value)}
							<option value={opt.value}>{opt.label}</option>
						{/each}
					</select>
				</div>
				<p class="hint-small">Applies device-wide — menus, headers, and every screen.</p>
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

	.subsection-title {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--dark-gray);
		border-top: 1px solid var(--light-gray);
		margin: 20px 0 4px;
		padding-top: 16px;
	}

	.list-row {
		padding: 12px;
		margin: 12px 0;
		border: 1px solid var(--light-gray);
		border-radius: 4px;
		transition: border-color 100ms ease;
	}

	.list-row.drag-over {
		border: 1.5px dashed var(--ink);
	}

	.list-row .field {
		margin: 8px 0;
	}

	.list-row-head {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.drag-handle {
		cursor: grab;
		font-size: 16px;
		color: var(--mid-gray);
		user-select: none;
		line-height: 1;
	}

	.drag-handle:active {
		cursor: grabbing;
	}

	.list-row-index {
		flex: 1;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--mid-gray);
	}

	.move-buttons {
		display: flex;
		gap: 4px;
	}

	.btn--secondary {
		margin-top: 4px;
	}

	.btn--move,
	.btn--remove {
		width: 28px;
		min-height: 28px;
		padding: 0;
		font-size: 14px;
		line-height: 1;
		box-shadow: none;
	}

	.field-label {
		display: block;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--dark-gray);
		margin-bottom: 6px;
	}

	.icon-picker {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.icon-option {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 38px;
		height: 38px;
		border: 1.5px solid var(--dark-gray);
		border-radius: 4px;
		background: var(--white);
		color: var(--ink);
		cursor: pointer;
		transition:
			background 100ms ease,
			color 100ms ease,
			border-color 100ms ease;
	}

	.icon-option:hover {
		border-color: var(--ink);
	}

	.icon-option.active {
		background: var(--ink);
		border-color: var(--ink);
		color: var(--paper);
	}

	.hint-small {
		font-size: 12px;
		color: var(--mid-gray);
		margin: 4px 0 0;
	}

	.test-result {
		font-weight: 700;
		color: var(--ink);
	}

	.test-result.error {
		color: var(--dark-gray);
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
