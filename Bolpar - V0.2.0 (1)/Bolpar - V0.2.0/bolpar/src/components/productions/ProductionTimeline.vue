<template>
  <q-card flat bordered class="production-timeline-card">
    <q-expansion-item
      v-model="expanded"
      header-class="q-pa-md"
      expand-icon="keyboard_arrow_down"
    >
      <template #header>
        <q-item-section>
          <div class="text-h6">Historial de producción</div>
          <div class="text-caption text-grey-7">
            Movimientos actuales de la OT seleccionada
          </div>
        </q-item-section>
      </template>

      <q-separator />

      <q-card-section>
        <div v-if="timelineItems.length > 0" class="timeline">
          <div v-for="(item, index) in timelineItems" :key="index" class="timeline-item">
            <div class="timeline-dot" :class="item.color" />

            <div class="timeline-content">
              <div class="text-weight-bold">
                {{ item.title }}
              </div>

              <div v-if="item.dateTime" class="text-caption text-grey-7">
                {{ item.dateTime }}
              </div>

              <div v-if="item.description" class="text-body2 text-grey-8 timeline-description q-mt-xs">
                {{ item.description }}
              </div>

              <div v-if="item.detail" class="text-caption text-grey-7 q-mt-xs timeline-description">
                {{ item.detail }}
              </div>
            </div>
          </div>
        </div>

        <div v-else class="text-grey-7">
          Todavía no hay movimientos registrados para esta producción.
        </div>
      </q-card-section>
    </q-expansion-item>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useProcessStore } from 'src/stores/process.store';
import { useUserStore } from 'src/stores/user.store';
import { MACHINE_STATE } from 'src/queries/models/machines.model';
import { useGetEmployees } from 'src/queries/get-employees-query';
import { useListSnapshots } from 'src/queries/list-snapshots-query';

const expanded = ref(false);

const processStore = useProcessStore();
const userStore = useUserStore();
const { employees } = useGetEmployees();

const selectedMachineId = computed(() => processStore.selectedMachine?.id);
const { snapshots } = useListSnapshots(selectedMachineId);

type TimelineItem = {
  title: string;
  timestamp: number;
  dateTime?: string;
  description?: string;
  detail?: string;
  color: string;
};

type InputRow = {
  consumed?: number | string | null;
};

type StatusLog = {
  estado: string;
  motivo?: string | null;
  fecha_hora?: string | null;
};

const getEmployeeName = (employeeId: string | number) => {
  const employee = employees.value.find((e) => e.id.toString() === employeeId.toString());
  return employee?.name ?? `Empleado ID: ${employeeId}`;
};

const timelineItems = computed<TimelineItem[]>(() => {
  const items: TimelineItem[] = [];
  const statusLogs = [...(processStore.selectedMachine?.status_logs ?? [])] as StatusLog[];

  statusLogs.forEach((log) => {
    const timestamp = new Date(log.fecha_hora ?? '').getTime();

    items.push({
      title: getStatusTitle(log.estado),
      timestamp: Number.isNaN(timestamp) ? 0 : timestamp,
      dateTime: formatDateTime(log.fecha_hora),
      description: `Usuario: ${userStore.username || 'Usuario no identificado'}`,
      detail: getStatusDetail(log.estado, log.motivo),
      color: getStatusColor(log.estado),
    });
  });

  snapshots.value
    .filter((snapshot) => snapshot.actionType === 'employees-assigned')
    .forEach((snapshot) => {
      const assignedEmployees = snapshot.data.assignedEmployees ?? [];

      items.push({
        title: 'Empleados designados',
        timestamp: snapshot.datetime,
        dateTime: formatDateTime(snapshot.datetime),
        description: `Usuario: ${userStore.username || 'Usuario no identificado'}`,
        detail:
          assignedEmployees.length > 0
            ? assignedEmployees.map((employeeId) => getEmployeeName(employeeId)).join('\n')
            : 'Sin empleados registrados',
        color: 'blue',
      });
    });

  const inputRows = (processStore.selectedMachineInputRows ?? []) as InputRow[];

  if (inputRows.length > 0) {
    const totalConsumed = inputRows.reduce((total, row) => total + Number(row.consumed ?? 0), 0);

    items.push({
      title: 'Registro de consumo',
      timestamp: Date.now(),
      dateTime: 'Fecha y hora: según registro guardado',
      description: `Usuario: ${userStore.username || 'Usuario no identificado'}`,
      detail: `Total consumido: ${Math.round(totalConsumed * 1000) / 1000} Kg\n${
        inputRows.length
      } registro(s) cargado(s)`,
      color: 'purple',
    });
  }

  return items.sort((a, b) => b.timestamp - a.timestamp);
});

const getStatusTitle = (status: string) => {
  if (status === MACHINE_STATE.Started) return 'Inicio de producción cambio';
  if (status === MACHINE_STATE.Produccion) return 'Producción en curso';
  if (status === MACHINE_STATE.Paused) return 'Pausa';
  if (status === MACHINE_STATE.Finished) return 'Finalización';
  return 'Estado de producción';
};

const getStatusDetail = (status: string, motivo?: string | null) => {
  if (status === MACHINE_STATE.Paused) {
    return `Estado: Pausa\nMotivo: ${motivo || 'Sin motivo registrado'}`;
  }

  return `Estado: ${status}`;
};

const getStatusColor = (status: string) => {
  if (status === MACHINE_STATE.Started) return 'grey';
  if (status === MACHINE_STATE.Produccion) return 'green';
  if (status === MACHINE_STATE.Paused) return 'orange';
  if (status === MACHINE_STATE.Finished) return 'green';
  return 'grey';
};

const formatDateTime = (value?: string | number | null) => {
  if (!value) return 'Fecha y hora: sin registrar';

  return `Fecha y hora: ${new Date(value).toLocaleString('es-PY', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })}`;
};
</script>

<style scoped lang="scss">
.production-timeline-card {
  width: 100%;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.timeline-item {
  position: relative;
  display: flex;
  gap: 12px;
}

.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 18px;
  width: 2px;
  height: calc(100% + 8px);
  background: #dcdcdc;
}

.timeline-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-top: 3px;
  z-index: 1;
  background: #9e9e9e;
}

.timeline-dot.green {
  background: #2e7d32;
}

.timeline-dot.orange {
  background: #ef6c00;
}

.timeline-dot.blue {
  background: #1565c0;
}

.timeline-dot.purple {
  background: #6a1b9a;
}

.timeline-content {
  flex: 1;
  min-width: 0;
}

.timeline-description {
  white-space: pre-line;
}
</style>