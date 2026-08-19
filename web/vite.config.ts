import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Static build served by the device from LittleFS.
			adapter: adapter()
		})
	],
	server: {
		// During `pnpm dev`, proxy API calls to a real device.
		proxy: {
			'/api': `http://${process.env.INKBRIDGE_HOST ?? 'inkbridge.local'}`
		}
	}
});
