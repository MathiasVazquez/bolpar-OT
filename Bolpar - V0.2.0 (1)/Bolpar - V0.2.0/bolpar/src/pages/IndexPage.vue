<template>
  <LoginPage v-if="!userStore.isLoggedIn" />
  <OrderListPage v-else />
</template>

<script setup lang="ts">
import { useUserStore } from 'src/stores/user.store';
import LoginPage from './LoginPage.vue';
import OrderListPage from './OrderListPage.vue';

const userStore = useUserStore();
</script>

<style lang="scss" scoped>
.list-item {
  border: 1px solid $grey-4;
  border-radius: 4px;
}
</style>
