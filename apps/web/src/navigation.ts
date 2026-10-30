export type View = 'home' | 'work' | 'compare' | 'research' | 'cookies';

const basePath = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
const localPaths: Record<View, string> = {
  home: '/', work: '/documents', compare: '/compare', research: '/method', cookies: '/cookies'
};

export const paths: Record<View, string> = Object.fromEntries(
  Object.entries(localPaths).map(([view, path]) => [view, `${basePath.replace(/\/$/, '')}${path}` || '/'])
) as Record<View, string>;

export function routeFromPath(pathname: string): View {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  const basePrefix = basePath.replace(/\/$/, '');
  const localPath = basePrefix && (normalized === basePrefix || normalized.startsWith(`${basePrefix}/`))
    ? normalized.slice(basePrefix.length) || '/'
    : normalized;
  return (Object.keys(localPaths) as View[]).find(view => localPaths[view] === localPath) || 'home';
}
