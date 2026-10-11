import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
const codespaceHost = process.env.CODESPACE_NAME && process.env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN
  ? `${process.env.CODESPACE_NAME}-5173.${process.env.GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}` : null;
export default defineConfig({
  plugins: [tailwindcss()],
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true,
    allowedHosts: codespaceHost ? [codespaceHost] : [],
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false, timeout: 75000 } },
  },
});
