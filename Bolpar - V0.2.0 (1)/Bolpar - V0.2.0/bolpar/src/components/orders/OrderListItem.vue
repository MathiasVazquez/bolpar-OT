<template>
  <q-item clickable class="order-item" :class="{ compact: compact }" @click="$emit('click')">
    <q-item-section avatar class="avatar-section">
      <q-avatar color="primary" text-color="white" size="34px" class="order-avatar">
        {{ number }}
      </q-avatar>
    </q-item-section>

    <q-item-section>
      <q-item-label class="order-title" :lines="compact ? 1 : 2">
        {{ order.subject }}
      </q-item-label>

      <q-item-label caption class="customer-name" lines="1">
        {{ order.account_name }}
      </q-item-label>
    </q-item-section>

    <q-item-section side class="date-section">
      <q-badge
        v-if="compact"
        rounded
        :color="statusColor"
        text-color="white"
        :label="statusLabel"
        class="status-badge"
      />

      <q-item-label caption>Vencimiento</q-item-label>
      <q-item-label caption>{{ order.due_date }}</q-item-label>
    </q-item-section>
  </q-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Order } from 'src/queries/models/order.model';

type Props = {
  order: Order;
  number: number | string;
  compact?: boolean;
};

const props = defineProps<Props>();

defineEmits<{
  (e: 'click'): void;
}>();

const statusLabel = computed(() =>
  props.order.status === 'completado' ? 'Completado' : 'Pendiente',
);

const statusColor = computed(() =>
  props.order.status === 'completado' ? 'green-4' : 'orange-4',
);
</script>

<style scoped lang="scss">
.order-item {
  min-height: 78px;
  border-bottom: 1px solid #dde2ea;
  background: #fff;
  transition: background 0.15s ease;
}

.order-item:hover {
  background: #f5f8ff;
}

.order-item:last-child {
  border-bottom: none;
}

.order-title {
  font-weight: 700;
  font-size: 14px;
  color: #111827;
}

.customer-name {
  font-weight: 600;
  color: #7b8494;
  letter-spacing: 0.4px;
}

.order-avatar {
  font-weight: 700;
  background: #0b2857 !important;
}

.date-section {
  min-width: 94px;
  text-align: right;
}

.status-badge {
  margin-bottom: 6px;
  font-size: 10px;
}

.compact {
  min-height: 66px;
}

.compact .order-title {
  font-size: 13px;
}

.compact .date-section {
  min-width: 88px;
}

@media (max-width: 700px) {
  .date-section {
    display: none;
  }

  .order-item {
    min-height: 72px;
  }
}
</style>