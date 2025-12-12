import { type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router';

interface RouteMetaImpl {
  NeedLogined: boolean;
}

declare module 'vue-router' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface RouteMeta extends RouteMetaImpl {}
}

const loginInterceptor = (
  signInPath: string,
  to: RouteLocationNormalized,
  next: NavigationGuardNext,
) => {
  next();
};

export { loginInterceptor };
