<template>
  <q-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="order-history-dialog">
      <!-- ====================================================== -->
      <!-- CABECERA -->
      <!-- ====================================================== -->

      <q-card-section class="row items-start q-pb-sm">
        <div class="col">
          <div class="text-h6 text-weight-bold">
            Historial detallado
          </div>

          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            OT {{ history?.order.so_number || orderNumber || orderId }}
          </div>

          <div
            v-if="history?.order.subject || orderSubject"
            class="text-caption text-grey-7 q-mt-xs"
          >
            {{ history?.order.subject || orderSubject }}
          </div>
        </div>

        <div class="row q-gutter-sm">
          <q-btn
            flat
            round
            dense
            icon="refresh"
            :loading="loading"
            @click="loadHistory"
          >
            <q-tooltip>Actualizar historial</q-tooltip>
          </q-btn>

          <q-btn
            flat
            round
            dense
            icon="close"
            v-close-popup
          />
        </div>
      </q-card-section>

      <q-separator />

      <!-- ====================================================== -->
      <!-- RESUMEN -->
      <!-- ====================================================== -->

      <q-card-section
        v-if="history"
        class="row items-center q-gutter-sm q-py-sm"
      >
        <q-chip
          dense
          outline
          icon="history"
        >
          {{ history.count }}
          {{ history.count === 1 ? 'evento' : 'eventos' }}
        </q-chip>

        <q-chip
          dense
          outline
          icon="tag"
        >
          OT ID: {{ history.order.id }}
        </q-chip>

        <q-space />

<q-btn
  outline
  dense
  no-caps
  color="primary"
  icon="description"
  label="Exportar "
  :loading="exportingWord"
  @click="exportHistoryWord"
/>
        
      </q-card-section>

      <q-separator v-if="history" />

      <!-- ====================================================== -->
      <!-- ERROR -->
      <!-- ====================================================== -->

      <q-card-section v-if="errorMessage">
        <q-banner
          rounded
          class="bg-red-1 text-red-9"
        >
          <template #avatar>
            <q-icon name="error_outline" />
          </template>

          {{ errorMessage }}

          <template #action>
            <q-btn
              flat
              no-caps
              label="Reintentar"
              @click="loadHistory"
            />
          </template>
        </q-banner>
      </q-card-section>

      <!-- ====================================================== -->
      <!-- SIN REGISTROS -->
      <!-- ====================================================== -->

      <q-card-section
        v-else-if="
          !loading &&
          history &&
          history.results.length === 0
        "
        class="text-center q-py-xl"
      >
        <q-icon
          name="history"
          size="54px"
          color="grey-5"
        />

        <div class="text-h6 q-mt-md">
          Sin eventos registrados
        </div>

        <div class="text-body2 text-grey-7 q-mt-sm">
          Esta OT todavía no posee eventos en el nuevo historial de auditoría.
        </div>
      </q-card-section>

      <!-- ====================================================== -->
      <!-- TIMELINE -->
      <!-- ====================================================== -->

      <q-card-section
        v-else-if="history"
        class="history-scroll"
      >
        <q-timeline
          layout="comfortable"
          color="primary"
        >
          <q-timeline-entry
            v-for="event in history.results"
            :key="event.id"
            :title="event.event_label"
            :subtitle="formatDateTime(event.event_at)"
            :icon="getEventIcon(event.event_type)"
            :color="getEventColor(event.event_type)"
          >
            <q-card
              flat
              bordered
              class="history-event-card"
            >
              <q-card-section class="q-pb-sm">
                <!-- USUARIO / MAQUINA -->

                <div class="row q-col-gutter-md q-mb-sm">
                  <div class="col-12 col-sm-6">
                    <div class="history-field-label">
                      Usuario
                    </div>

                    <div class="history-field-value">
                      <q-icon
                        name="person"
                        size="18px"
                        class="q-mr-xs"
                      />

                      {{ event.performed_by || 'Sistema' }}
                    </div>
                  </div>

                  <div
                    v-if="event.machine"
                    class="col-12 col-sm-6"
                  >
                    <div class="history-field-label">
                      Máquina
                    </div>

                    <div class="history-field-value">
                      <q-icon
                        name="precision_manufacturing"
                        size="18px"
                        class="q-mr-xs"
                      />

                      {{ event.machine.nombre }}
                    </div>
                  </div>
                </div>

                <!-- DESCRIPCION -->

                <div
                  v-if="event.description"
                  class="q-mb-sm"
                >
                  <div class="history-field-label">
                    Detalle
                  </div>

                  <div class="history-description">
                    {{ event.description }}
                  </div>
                </div>

                <!-- ESTADOS -->

                <div
                  v-if="
                    event.previous_state ||
                    event.new_state
                  "
                  class="q-mb-sm"
                >
                  <div class="history-field-label">
                    Cambio de estado
                  </div>

                  <div class="row items-center q-gutter-sm">
                    <q-chip
                      v-if="event.previous_state"
                      dense
                      outline
                    >
                      {{ event.previous_state }}
                    </q-chip>

                    <q-icon
                      v-if="
                        event.previous_state &&
                        event.new_state
                      "
                      name="arrow_forward"
                    />

                    <q-chip
                      v-if="event.new_state"
                      dense
                      color="primary"
                      text-color="white"
                    >
                      {{ event.new_state }}
                    </q-chip>
                  </div>
                </div>

                <!-- MOTIVO -->

                <div
                  v-if="event.reason"
                  class="q-mb-sm"
                >
                  <div class="history-field-label">
                    Motivo / justificación
                  </div>

                  <q-banner
                    dense
                    rounded
                    class="bg-orange-1 text-orange-10"
                  >
                    {{ event.reason }}
                  </q-banner>
                </div>

                <!-- EMPLEADOS -->

                <div
                  v-if="event.employees?.length"
                  class="q-mb-sm"
                >
                  <div class="history-field-label">
                    Empleados asignados
                  </div>

                  <div class="row q-gutter-xs">
                    <q-chip
                      v-for="(employee, employeeIndex) in event.employees"
                      :key="employeeKey(employee, employeeIndex)"
                      dense
                      outline
                      icon="badge"
                    >
                      {{ employeeLabel(employee) }}
                    </q-chip>
                  </div>
                </div>

                <!-- METADATA -->

                <q-expansion-item
                  v-if="metadataEntries(event.metadata).length"
                  dense
                  dense-toggle
                  expand-separator
                  icon="data_object"
                  label="Datos del evento"
                  class="q-mt-sm"
                >
                  <q-card flat>
                    <q-card-section class="q-pa-sm">
                      <div
                        v-for="[key, value] in metadataEntries(event.metadata)"
                        :key="key"
                        class="metadata-row"
                      >
                        <div class="metadata-key">
                          {{ humanizeKey(key) }}
                        </div>

                        <div class="metadata-value">
                          {{ formatMetadataValue(value) }}
                        </div>
                      </div>
                    </q-card-section>
                  </q-card>
                </q-expansion-item>

                <!-- ID AUDITORIA -->

                <div class="history-audit-id">
                  Registro de auditoría #{{ event.id }}
                </div>
              </q-card-section>
            </q-card>
          </q-timeline-entry>
        </q-timeline>
      </q-card-section>

      <q-inner-loading :showing="loading">
        <q-spinner
          size="48px"
          color="primary"
        />

        <div class="q-mt-md text-weight-medium">
          Cargando historial...
        </div>
      </q-inner-loading>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { api } from 'src/boot/axios';

type HistoryMachine = {
  id: number;
  nombre: string;
  numero: number | null;
};

type HistoryEmployee =
  | string
  | number
  | {
      id?: number | string | null;
      zoho_id?: string | null;
      name?: string | null;
      assigned_by?: string | null;
      assigned_at?: string | null;
    };

type HistoryEvent = {
  id: number;
  event_type: string;
  event_label: string;
  event_at: string;
  performed_by: string | null;
  machine: HistoryMachine | null;
  description: string | null;
  previous_state: string | null;
  new_state: string | null;
  reason: string | null;
  employees: HistoryEmployee[];
  metadata: Record<string, unknown>;
  created_at: string;
};

type HistoryResponse = {
  order: {
    id: number;
    so_number: string;
    subject: string;
  };
  count: number;
  results: HistoryEvent[];
};

const props = defineProps<{
  modelValue: boolean;
  orderId: number | null;
  orderNumber?: string;
  orderSubject?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
}>();

const history = ref<HistoryResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const exportingWord = ref(false);

const loadHistory = async () => {
  if (!props.orderId) {
    return;
  }

  loading.value = true;
  errorMessage.value = '';

  try {
    const response = await api.get<HistoryResponse>(
      `inventario/orders/${props.orderId}/history/`,
    );

    history.value = response.data;
  } catch (error: unknown) {
    const status = (
      error as {
        response?: {
          status?: number;
        };
      }
    )?.response?.status;

    if (status === 401) {
      errorMessage.value =
        'La sesión no está autorizada o venció. Volvé a iniciar sesión.';
    } else if (status === 404) {
      errorMessage.value =
        'No se encontró la OT o el endpoint de historial.';
    } else {
      errorMessage.value =
        'No se pudo cargar el historial detallado de la OT.';
    }

    console.error(
      'Error cargando historial de OT:',
      error,
    );
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      void loadHistory();
    }
  },
);

watch(
  () => props.orderId,
  () => {
    if (props.modelValue) {
      void loadHistory();
    }
  },
);

const exportHistoryWord = async () => {
  if (!props.orderId) {
    return;
  }

  exportingWord.value = true;

  try {
    const response = await api.get(
      `inventario/orders/${props.orderId}/history/export-word/`,
      {
        responseType: 'blob',
      },
    );

    const blob = new Blob(
      [response.data],
      {
        type:
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      },
    );

    const url =
      window.URL.createObjectURL(blob);

    const link =
      document.createElement('a');

    const orderNumber =
      props.orderNumber ||
      String(props.orderId);

    link.href = url;

    link.download =
      `OT_${orderNumber}_historial_detallado.docx`;

    document.body.appendChild(link);

    link.click();
    link.remove();

    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error(
      'Error exportando historial:',
      error,
    );

    errorMessage.value =
      'No se pudo exportar el historial.';
  } finally {
    exportingWord.value = false;
  }
};

const formatDateTime = (value: string) => {
  if (!value) {
    return '-';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString('es-PY', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const getEventIcon = (eventType: string) => {
  const icons: Record<string, string> = {
    OT_RECEIVED: 'cloud_download',
    OT_OPENED: 'visibility',
    EMPLOYEES_ASSIGNED: 'groups',
    MACHINE_STARTED: 'play_circle',
    MACHINE_PRODUCTION_STARTED: 'precision_manufacturing',
    MACHINE_PAUSED: 'pause_circle',
    MACHINE_RESUMED: 'play_arrow',
    SHIFT_CHANGED: 'swap_horiz',
    MACHINE_FINISHED: 'flag',
    CONSUMPTION_REGISTERED: 'inventory_2',
    WASTE_REGISTERED: 'delete_sweep',
    FINAL_CONSUMPTION_REGISTERED: 'assignment',
    PREVIOUS_MACHINE_QUANTITY_RECEIVED: 'move_to_inbox',
    QUANTITY_PRODUCED: 'output',
    JUSTIFICATION_REGISTERED: 'description',
    OT_COMPLETED: 'task_alt',
  };

  return icons[eventType] || 'history';
};

const getEventColor = (eventType: string) => {
  const colors: Record<string, string> = {
    OT_RECEIVED: 'blue',
    OT_OPENED: 'blue-grey',
    EMPLOYEES_ASSIGNED: 'indigo',
    MACHINE_STARTED: 'cyan',
    MACHINE_PRODUCTION_STARTED: 'primary',
    MACHINE_PAUSED: 'orange',
    MACHINE_RESUMED: 'teal',
    SHIFT_CHANGED: 'deep-orange',
    MACHINE_FINISHED: 'green',
    CONSUMPTION_REGISTERED: 'purple',
    WASTE_REGISTERED: 'red',
    FINAL_CONSUMPTION_REGISTERED: 'deep-purple',
    PREVIOUS_MACHINE_QUANTITY_RECEIVED: 'blue-grey',
    QUANTITY_PRODUCED: 'green',
    JUSTIFICATION_REGISTERED: 'amber',
    OT_COMPLETED: 'positive',
  };

  return colors[eventType] || 'grey';
};

const employeeLabel = (
  employee: HistoryEmployee,
) => {
  if (
    typeof employee === 'string' ||
    typeof employee === 'number'
  ) {
    return String(employee);
  }

  if (employee.name) {
    return employee.name;
  }

  if (employee.zoho_id) {
    return `Zoho ${employee.zoho_id}`;
  }

  if (employee.id !== undefined && employee.id !== null) {
    return `Empleado ${employee.id}`;
  }

  return 'Empleado';
};

const employeeKey = (
  employee: HistoryEmployee,
  index: number,
) => {
  if (
    typeof employee === 'string' ||
    typeof employee === 'number'
  ) {
    return `${employee}-${index}`;
  }

  return `${
    employee.id ??
    employee.zoho_id ??
    employee.name ??
    'employee'
  }-${index}`;
};

const metadataEntries = (
  metadata: Record<string, unknown> | null | undefined,
): [string, unknown][] => {
  if (!metadata) {
    return [];
  }

  return Object.entries(metadata);
};

const humanizeKey = (key: string) => {
  const aliases: Record<string, string> = {
    insumo: 'Producto / insumo',
    cantidad: 'Cantidad',
    unidad: 'Unidad',
    linea: 'Máquina / línea',
    lote: 'Lote',
    previous_value: 'Valor anterior',
    value: 'Valor nuevo',
    label: 'Concepto',
    field: 'Campo',
    mode: 'Modo de asignación',
    employees_before: 'Empleados anteriores',
    employees_after: 'Empleados posteriores',
    created: 'Asignaciones creadas',
    deactivated: 'Asignaciones desactivadas',
    action_type: 'Acción',
    snapshot_id: 'Snapshot ID',
    machine_status_log_id: 'Registro de estado ID',
    so_number: 'Número OT',
    subject: 'Asunto / producto',
    source: 'Origen',
    plan_count: 'Máquinas planificadas',
    machines_count: 'Máquinas registradas',
    machine_ids: 'IDs de máquinas',
    replace: 'Reemplazo de consumos',
    item_index: 'Ítem',
  };

  if (aliases[key]) {
    return aliases[key];
  }

  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/^./, (value) => value.toUpperCase());
};

const formatMetadataValue = (
  value: unknown,
): string => {
  if (value === null || value === undefined) {
    return '-';
  }

  if (typeof value === 'string') {
    return value;
  }

  if (
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value);
  }

  if (typeof value === 'bigint') {
    return value.toString();
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '-';
    }

    return value
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }

        if (
          typeof item === 'number' ||
          typeof item === 'boolean'
        ) {
          return String(item);
        }

        if (item === null || item === undefined) {
          return '-';
        }

        if (
          typeof item === 'object' &&
          !Array.isArray(item)
        ) {
          const objectItem = item as Record<
            string,
            unknown
          >;

          const name = objectItem.name;

          if (
            typeof name === 'string' ||
            typeof name === 'number'
          ) {
            return String(name);
          }

          const id = objectItem.id;

          if (
            typeof id === 'string' ||
            typeof id === 'number'
          ) {
            return `ID ${String(id)}`;
          }

          return Object.entries(objectItem)
            .map(([key, innerValue]) => {
              return (
                `${humanizeKey(key)}: ` +
                formatMetadataValue(innerValue)
              );
            })
            .join(' | ');
        }

        return formatMetadataValue(item);
      })
      .join(', ');
  }

  if (typeof value === 'object') {
    return Object.entries(
      value as Record<string, unknown>,
    )
      .map(([key, innerValue]) => {
        return (
          `${humanizeKey(key)}: ` +
          formatMetadataValue(innerValue)
        );
      })
      .join(' | ');
  }

  if (typeof value === 'symbol') {
    return value.description ?? 'Símbolo';
  }

  if (typeof value === 'function') {
    return '[función]';
  }

  return '-';
};
</script>

<style scoped>
.order-history-dialog {
  width: 1100px;
  max-width: 96vw;
  min-height: 500px;
  max-height: 92vh;
  position: relative;
}

.history-scroll {
  max-height: 72vh;
  overflow-y: auto;
  padding: 24px;
}

.history-event-card {
  border-radius: 10px;
}

.history-field-label {
  font-size: 11px;
  font-weight: 700;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.history-field-value {
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.history-description {
  font-size: 14px;
  line-height: 1.5;
}

.metadata-row {
  display: grid;
  grid-template-columns: minmax(150px, 220px) 1fr;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid #eeeeee;
}

.metadata-row:last-child {
  border-bottom: none;
}

.metadata-key {
  font-size: 12px;
  font-weight: 700;
  color: #616161;
}

.metadata-value {
  font-size: 13px;
  word-break: break-word;
}

.history-audit-id {
  margin-top: 12px;
  font-size: 10px;
  color: #9e9e9e;
  text-align: right;
}

@media (max-width: 700px) {
  .order-history-dialog {
    width: 98vw;
    max-width: 98vw;
  }

  .history-scroll {
    padding: 12px;
  }

  .metadata-row {
    grid-template-columns: 1fr;
    gap: 3px;
  }
}
</style>