<template>
  <LoadingBox v-if="isGettingSnapshots" message="Cargando información de la orden de trabajo..." />

  <q-page v-if="processStore.selectedOrder" v-show="!isGettingSnapshots" class="order-details-page">
    <div class="info-panel">
      <div class="info-card">
        <q-tabs v-model="tab" no-caps dense active-color="primary">
          <q-tab name="product" label="Producto" />
          <q-tab name="ot" label="OT" />
        </q-tabs>

        <q-separator />

        <q-tab-panels v-model="tab" animated>
          <q-tab-panel name="product">
            <div class="text-h6 panel-title">
              {{ orderProduct?.product_name }}
            </div>

            <q-separator spaced />

            <div class="info-grid">
              <div v-for="(info, index) of productInfo" :key="index" class="column">
                <div class="text-grey-9">
                  {{ info.label }}
                </div>
                <div class="text-weight-medium text-subtitle1">
                  {{ formatMoney(info.value).toFormatedString() }}
                </div>
              </div>
            </div>
          </q-tab-panel>

          <q-tab-panel name="ot">
            <div class="text-h6 panel-title">
              {{ order?.subject }}
            </div>

            <q-separator spaced />

            <div class="info-grid">
              <div v-for="(info, index) of otInfo" :key="index" class="column">
                <div class="text-grey-9">
                  {{ info.label }}
                </div>
                <div class="text-weight-medium text-subtitle1">
                  {{ info.value }}
                </div>
              </div>
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </div>

      <div class="info-card q-pa-md">
        <div class="text-h6 panel-title">Consumo total</div>

        <q-separator spaced />

        <div class="info-grid">
          <div
            v-for="field of currentMachineFinishInfoOptions?.fields"
            :key="field.value"
            class="column"
          >
            <div class="text-grey-9">
              {{ field.label }}
            </div>
            <div class="text-weight-medium text-subtitle1">
              {{ getSumOfFinalComsumption(field.value) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="main-panel">
      <OrderDetailsHeader @status-change="handleStatusChange" />

      <div class="tables-panel">
        <PlanificationTable />

        <RealTable
          v-if="
            processStore.selectedMachineStatusIsOneOf([
              MACHINE_STATE.Finished,
              MACHINE_STATE.Produccion,
              MACHINE_STATE.Paused,
            ])
          "
        />
      </div>
    </div>

    <div class="process-panel">
      <q-item-label caption class="q-pa-md">Estado de procesos</q-item-label>

      <q-list class="process-list">
        <q-item
          v-for="(step, index) of order?.planificacion_produccion"
          :key="index"
          :class="{ 'bg-primary text-white': index === processStore.selectedMachineIndex }"
          class="process-item"
          clickable
          @click="processStore.selectMachine(index)"
        >
          <q-item-section avatar :style="{ minWidth: '0px' }">
            <q-avatar
              v-if="processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Finished"
              color="green-9"
              icon="check"
              text-color="white"
              size="sm"
            />

            <q-avatar
              v-else-if="
                processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Produccion
              "
              color="orange-9"
              icon="arrow_right"
              text-color="white"
              size="sm"
              font-size="20px"
            />

            <q-avatar
              v-else-if="processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Paused"
              color="orange-9"
              icon="pause"
              text-color="white"
              size="sm"
              font-size="20px"
            />

            <q-avatar v-else color="grey" icon="timer" text-color="white" size="sm" />
          </q-item-section>

          <q-item-section>
            <q-item-label>{{ step.linea_new }}</q-item-label>
            <q-item-label class="text-caption" style="opacity: 0.8" lines="2">
              {{
                processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Finished
                  ? 'Completado'
                  : processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Produccion
                    ? 'En producción'
                    : processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Paused
                      ? 'Pausado'
                      : processStore.getMachineStatusByIndex(index)?.estado === MACHINE_STATE.Started
                        ? 'Preparado'
                        : 'Pendiente'
              }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>

      <div class="q-mt-md">
        <ProductionTimeline />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import PlanificationTable from 'src/components/productions/PlanificationTable.vue';
import RealTable from 'src/components/productions/RealTable.vue';
import OrderDetailsHeader from 'src/components/productions/OrderDetailsHeader.vue';
import { computed, onMounted, ref, watch } from 'vue';
import { useGetMachinesQuery } from 'src/queries/get-ot-machines.query';
import type { Register } from 'src/components/productions/models';
import type { MachineProcess } from 'src/queries/models/machines.model';
import { MACHINE_STATE } from 'src/queries/models/machines.model';
import { useProcessStore } from 'src/stores/process.store';
import { formatMoney } from 'src/utils/money.utils';
import { useListSnapshots } from 'src/queries/list-snapshots-query';
import LoadingBox from 'src/components/LoadingBox.vue';
import { finishMachineInfoOptions } from 'src/utils/machine-options';
import ProductionTimeline from 'src/components/productions/ProductionTimeline.vue';

import { api } from 'src/boot/axios';
import { useUserStore } from 'src/stores/user.store';

const processStore = useProcessStore();

const userStore = useUserStore();

const selectedMachineId = computed(() => processStore.selectedMachine?.id);

const { refetchSnapshots, getSumOfFinalComsumption, lastSnapshot, isGettingSnapshots } =
  useListSnapshots(selectedMachineId);

onMounted(async () => {
  const orderId = processStore.selectedOrder?.id;

  if (orderId) {
    try {
      await api.post(
        `inventario/orders/${orderId}/history/opened/`,
        {
          performed_by:
            userStore.username || 'unknown',
        },
      );
    } catch (error) {
      console.error(
        'No se pudo registrar la apertura de la OT:',
        error,
      );
    }
  }

  await refetchSnapshots();
  updateProcessStoreFromSnapshot();
});

const currentMachineFinishInfoOptions = computed(() =>
  finishMachineInfoOptions.find((option) =>
    option.isName(processStore.selectedMachine?.nombre ?? ''),
  ),
);

const registers = ref<Register[]>([]);
const order = computed(() => processStore.selectedOrder);
const orderProduct = computed(() => processStore.selectedOrder?.items[0]);
const { getMachines } = useGetMachinesQuery();

const normalizeMachineText = (value: string | number | null | undefined) =>
  String(value ?? '').trim().toLowerCase();

const getMachineCode = (value: string | number | null | undefined) => {
  const match = String(value ?? '').trim().match(/^(\d+)/);
  return match?.[1] ?? '';
};

const findMachineForCurrentPlan = (machines: MachineProcess[]) => {
  const plan = order.value?.planificacion_produccion?.[0];
  const planCode = getMachineCode(plan?.linea_new || plan?.linea);

  const candidates = machines.filter((machine) => {
    const machineCode = getMachineCode(machine.nombre);
    if (planCode && machineCode) return planCode === machineCode;

    return normalizeMachineText(machine.nombre) ===
      normalizeMachineText(plan?.linea_new || plan?.linea);
  });

  const currentId = processStore.selectedMachine?.id;
  return (
    candidates.find((machine) => machine.id === currentId) ??
    [...candidates].sort((a, b) => Number(b.id) - Number(a.id))[0]
  );
};

const handleStatusChange = async () => {
  if (!order.value || !processStore.selectedOrder?.id) return;

  registers.value = [];

  const allMachines = await getMachines(processStore.selectedOrder.id);
  const currentMachine = findMachineForCurrentPlan(allMachines);

  processStore.selectOrder(order.value, currentMachine ? [currentMachine] : []);
  processStore.selectMachine(0);

  await refetchSnapshots();
updateProcessStoreFromSnapshot();
await syncAssignedEmployeesFromBackend();
};

const updateProcessStoreFromSnapshot = () => {
  processStore.setSelectedMachineInputRows(
    lastSnapshot.value?.data.consumptionInputRows ?? [],
  );

  processStore.setSelectedMachineOverpassReasons(
    lastSnapshot.value?.data.overpassJustifications ?? {},
  );
};

const syncAssignedEmployeesFromBackend = async () => {
  const machineId = processStore.selectedMachine?.id;

  if (!machineId) return;

  try {
    const { data } = await api.get<{
      results?: Array<{ id: number | string }>;
    }>(`inventario/machines/${machineId}/employees/`);

    const employeeIds = (data.results ?? []).map((employee) =>
      String(employee.id),
    );

    processStore.setSelectedMachineEmployees(employeeIds);
  } catch (error) {
    console.error(
      'No se pudieron recuperar los empleados asignados:',
      error,
    );
  }
};

watch(lastSnapshot, updateProcessStoreFromSnapshot);

watch(selectedMachineId, async () => {
  await refetchSnapshots();
  updateProcessStoreFromSnapshot();
  await syncAssignedEmployeesFromBackend();
});

const tab = ref('product');

const productInfo = computed(() => [
  {
    label: 'Ancho útil',
    value: order.value?.ancho_util,
  },
  {
    label: 'Cantidad de Kilogramos',
    value: order.value?.cantidad_kilogramos,
  },
  {
    label: 'Cantidad de Metros',
    value: order.value?.cantidad_metros,
  },
  {
    label: 'Cilindro',
    value: order.value?.cilindro,
  },
  {
    label: 'Fondo útil',
    value: order.value?.fondo_util,
  },
  {
    label: 'Fuerte útil',
    value: order.value?.fuerte_util,
  },
]);

const otInfo = computed(() => [
  {
    label: 'Nombre del cliente',
    value: order.value?.account_name,
  },
]);
</script>

<style scoped lang="scss">
.order-details-page {
  min-height: 100vh;
  padding: 16px;
  display: flex;
  gap: 16px;
  overflow: auto;
}

.info-panel {
  width: 260px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}

.info-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: white;
}

.panel-title {
  line-height: 1.2em;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.main-panel {
  flex: 1;
  min-width: 0;
}

.tables-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 8px;
}

.process-panel {
  width: 240px;
  flex-shrink: 0;
}

.process-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.process-item {
  border-radius: 8px;
}

@media (max-width: 900px) {
  .order-details-page {
    flex-direction: column;
    padding: 10px;
    padding-bottom: 110px;
  }

  .info-panel {
    width: 100%;
  }

  .info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .process-panel {
    width: 100%;
    order: -1;
  }

  .process-list {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .main-panel {
    width: 100%;
  }
}

@media (max-width: 600px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .process-list {
    grid-template-columns: 1fr;
  }
}
</style>