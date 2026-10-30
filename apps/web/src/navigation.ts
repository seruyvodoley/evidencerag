export type View = 'home' | 'work' | 'compare' | 'research';
export const paths: Record<View, string> = {
  home: '/', work: '/documents', compare: '/compare', research: '/method'
};
export function routeFromPath(pathname: string): View {
  const path = pathname.replace(/\/+$/, '') || '/';
  return (Object.keys(paths) as View[]).find(view => paths[view] === path) || 'home';
}
