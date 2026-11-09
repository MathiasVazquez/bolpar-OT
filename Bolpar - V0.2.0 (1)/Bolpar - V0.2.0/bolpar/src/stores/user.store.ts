import { defineStore, acceptHMRUpdate } from 'pinia';
import { computed, ref } from 'vue';

export const useUserStore = defineStore('user', () => {
  // state: () => ({
  //   accessToken: '',
  // }),
  // getters: {
  //   isLoggedIn: (state) => !!state.accessToken,
  // },
  // actions: {
  //   setAccessToken(token: string) {
  //     this.accessToken = token;
  //   },
  // },
  const accessToken = ref('');
  const username = ref('');
  const isLoggedIn = computed(() => !!accessToken.value);
  const userAuthorization = ref('');
  
  return {
  username,
  accessToken,
  isLoggedIn,
  userAuthorization,
  setUserAuthorization: (value: string) => (userAuthorization.value = value),
  setAccessToken: (token: string) => (accessToken.value = token),
  setUsername: (value: string) => (username.value = value),
  logout: () => {
    accessToken.value = '';
    username.value = '';
    userAuthorization.value = '';
  },
};
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useUserStore, import.meta.hot));
}

