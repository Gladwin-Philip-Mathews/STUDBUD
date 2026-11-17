import { routes } from './app.routes';

describe('feature routes', () => {
  it('loads every feature lazily behind the auth guard', async () => {
    const features = ['profiles', 'communities', 'connections', 'messaging', 'moderation', 'admin'];
    for (const path of features) {
      const route = routes.find((r) => r.path === path)!;
      expect(route.canActivate?.length).toBe(1);
      const children = await (route.loadChildren as () => Promise<any>)();
      expect(children.length).toBeGreaterThan(0);
    }
  });
});
