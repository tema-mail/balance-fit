import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

/* GitHub Pages отдаёт сайт из подпапки /balance-fit/ – её задаёт PUBLIC_BASE
   при сборке в CI; локально сайт живёт в корне. */
export default defineConfig({
  site: 'https://tema-mail.github.io',
  base: process.env.PUBLIC_BASE || '/',
  trailingSlash: 'ignore',
  build: { format: 'directory', inlineStylesheets: 'never' },
  devToolbar: { enabled: false },
  // острова админки (Preact) – правило стека владельца 11.10.2026
  integrations: [preact()],
});
