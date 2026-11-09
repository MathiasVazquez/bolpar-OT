import { defineBoot } from '#q-app/wrappers';
import axios, { type AxiosInstance } from 'axios';
import { VueQueryPlugin } from '@tanstack/vue-query';

declare module 'vue' {
  interface ComponentCustomProperties {
    $axios: AxiosInstance;
    $api: AxiosInstance;
  }
}

// Be careful when using SSR for cross-request state pollution
// due to creating a Singleton instance here;
// If any client changes this (global) instance, it might be a
// good idea to move this instance creation inside of the
// "export default () => {}" function below (which runs individually
// for each client)
const api = axios.create({ baseURL: 'https://bolpar-server.probusinesspy.xyz/api/' });

export default defineBoot(({ app }) => {
  app.use(VueQueryPlugin);

  // for use inside Vue files (Options API) through this.$axios and this.$api

  app.config.globalProperties.$axios = axios;
  // ^ ^ ^ this will allow you to use this.$axios (for Vue Options API form)
  //       so you won't necessarily have to import axios in each vue file

  app.config.globalProperties.$api = api;
  // ^ ^ ^ this will allow you to use this.$api (for Vue Options API form)
  //       so you can easily perform requests against your app's API

  // Set api auth header
  // api.defaults.headers.common.Authorization =
  //   'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUxOTEwNjQwLCJpYXQiOjE3NTE4NDIyNDAsImp0aSI6ImZiNDAzZGZmMTc1MTRlNjc4MDA5N2FkZmE2MDVhMGI0IiwidXNlcl9pZCI6MSwiZmF2X2NvbG9yIjoiIn0.mSVFNURvPvuihZaDTO6IW8pUe7IGtvwqhmTkVez-PMM';
});

export { api };
