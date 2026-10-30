// Сайт может жить в подпапке (GitHub Pages: /balance-fit). Все внутренние ссылки и картинки – через u().
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');

export function u(path: string): string {
  if (!path || /^(https?:|tel:|mailto:|#|data:)/.test(path)) return path;
  if (BASE && path.startsWith(BASE + '/')) return path;
  return BASE + (path.startsWith('/') ? path : '/' + path);
}
