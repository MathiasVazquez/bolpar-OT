<template>
  <div class="column gap-md flex-center full-height bg-grey-2" :style="{ minHeight: '100vh' }">
    <q-spinner-box color="primary" size="4rem" :thickness="5" />
    <div>{{ message }}</div>
  </div>
</template>

<script setup lang="ts">
type LoadingBoxProps = {
  message?: string;
};

defineProps<LoadingBoxProps>();
</script>
