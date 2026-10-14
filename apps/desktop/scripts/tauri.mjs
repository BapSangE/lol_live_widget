import { spawnSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { loadEnv } from 'vite';
const mode = process.argv[2] || 'dev';
const env = loadEnv(mode === 'dev' ? 'development' : 'production', process.cwd(), 'VITE_');
const server = process.env.VITE_SERVER_URL || env.VITE_SERVER_URL;
let origin = '';
if (server) {
  const url = new URL(server);
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/')
    throw new Error('VITE_SERVER_URL must be a server origin without credentials or path');
  if (
    url.protocol !== 'https:' &&
    !(
      mode === 'dev' &&
      url.protocol === 'http:' &&
      ['localhost', '127.0.0.1'].includes(url.hostname)
    )
  )
    throw new Error('Production server must use HTTPS');
  origin = url.origin;
}
const folder = resolve('src-tauri/.generated');
mkdirSync(folder, { recursive: true });
const config = resolve(folder, 'network.json');
writeFileSync(
  config,
  JSON.stringify({
    app: {
      security: {
        csp: `default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' ipc: http://ipc.localhost https://ipc.localhost ${origin}; object-src 'none'; frame-src 'none'`,
      },
    },
  }),
);
const result = spawnSync(
  process.execPath,
  [
    resolve('node_modules/@tauri-apps/cli/tauri.js'),
    mode,
    ...process.argv.slice(3),
    '--config',
    config,
  ],
  { stdio: 'inherit', env: { ...process.env, ...(server ? { VITE_SERVER_URL: server } : {}) } },
);
process.exit(result.status ?? 1);
