<template>
  <q-table
    flat
    bordered
    title="Consumo real"
    :rows="processStore.selectedMachineInputRows ?? []"
    :columns="columns"
    :pagination="{ page: 1, rowsPerPage: 0 }"
    :rows-per-page-options="[0]"
    :row-key="getRealConsumptionRowKey"
    class="full-width"
    hide-bottom
  >
    <template #top>
      <div class="column full-width">
        <div class="row justify-between full-width">
          <div class="q-table__title">Consumo real</div>

          <q-btn
            v-if="processStore.selectedMachineStatus?.estado === MACHINE_STATE.Produccion"
            flat
            dense
            rounded
            no-caps
            icon="add"
            label="Agregar registro"
            class="bg-grey-3 q-pr-md q-pl-sm"
            @click="showAddRowDialog = true"
          />
        </div>

        <q-banner
          v-if="missingProductLines.length > 0"
          dense
          rounded
          class="bg-orange-2 text-orange-10 q-mt-md full-width"
        >
          <template #avatar>
            <q-icon name="warning" />
          </template>

          Debe cargar un registro de consumo real para todos los artículos planificados antes de
          hacer Cambio Turno o Finalizar Producción.
          Faltan: {{ missingProductLines.map((item) => item.insumo).join(', ') }}
        </q-banner>
      </div>
    </template>

    <template #body-cell="props">
      <q-td :props="props" :style="{ whiteSpace: 'normal' }">
        <q-input
          v-if="props.col.editable"
          v-model.number="props.row[props.col.name]"
          input-class="text-center"
          :type="props.col.type ?? 'text'"
          dense
          borderless
          class="bg-grey-2"
        />

        <div v-else-if="props.col.type === 'number'" :style="{ maxWidth: '250px' }">
          {{ formatQuantity(props.row[props.col.name]) }}
        </div>

        <div v-else :style="{ maxWidth: '250px' }">
          {{ props.row[props.col.name] }}
        </div>
      </q-td>
    </template>
  </q-table>

  <q-dialog v-model="showAddRowDialog" persistent>
    <q-card class="my-card">
      <q-card-section>
        <div class="text-h5">Agregar nuevo registro de consumo</div>

        <div class="q-mt-sm">
          Ingrese los datos del consumo realizado
        </div>
      </q-card-section>

      <q-card-section>
        <q-form @submit="handleAddRow">
          <div class="column gap-sm">
            <q-select
              v-model="newRegisterData.article"
              :options="productLines?.map((i) => i.insumo)"
              outlined
              :rules="[(val) => !!val || 'Campo requerido']"
              label="Producto"
              behavior="dialog"
              :disable="isCreatingSnapshot"
            />

            <q-input
              v-model="newRegisterData.batch"
              outlined
              label="Lote"
              :rules="[(val) => !!val || 'Campo requerido']"
              :disable="isCreatingSnapshot"
            />

            <q-input
              :model-value="formatQuantity(newRegisterData.initialWeight)"
              @update:model-value="newRegisterData.initialWeight = parseQuantityInput($event)"
              outlined
              inputmode="decimal"
              label="Cantidad inicial"
              hint="Cantidad disponible al iniciar el uso del lote"
              :rules="[
                () => newRegisterData.initialWeight !== null || 'Campo requerido',
              ]"
              :disable="isCreatingSnapshot"
            />

            <q-input
              :model-value="formatQuantity(newRegisterData.finalWeight)"
              @update:model-value="newRegisterData.finalWeight = parseQuantityInput($event)"
              outlined
              inputmode="decimal"
              label="Cantidad final"
              hint="Cantidad que quedó después del consumo"
              :rules="[
                () => newRegisterData.finalWeight !== null || 'Campo requerido',
                () =>
                  (
                    newRegisterData.initialWeight !== null &&
                    newRegisterData.finalWeight !== null &&
                    newRegisterData.finalWeight <= newRegisterData.initialWeight
                  ) ||
                  'La cantidad final debe ser menor o igual a la inicial',
              ]"
              :disable="isCreatingSnapshot"
            />

            <div class="row justify-between">
              <q-btn
                no-caps
                flat
                label="Cerrar"
                @click="showAddRowDialog = false"
                :disable="isCreatingSnapshot"
              />

              <q-btn
                no-caps
                unelevated
                label="Agregar"
                type="submit"
                color="primary"
                :style="{ minWidth: '160px' }"
                :loading="isCreatingSnapshot"
              />
            </div>
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { MACHINE_STATE } from 'src/queries/models/machines.model';
import { useProcessStore } from 'src/stores/process.store';
import { useCreateSnapshot } from 'src/queries/create-snapshot-query';

const processStore = useProcessStore();
const { createSnapshot, isCreatingSnapshot } = useCreateSnapshot();

/*
 * Clave visual independiente para cada objeto de registro.
 *
 * Dos cargas con el mismo artículo y lote conservan sus
 * propias filas. No se agrupan ni se eliminan duplicados.
 *
 * Estas claves no se agregan al store ni a los snapshots.
 */
const realConsumptionRowKeys = new WeakMap<object, string>();
let realConsumptionRowSequence = 0;

const getRealConsumptionRowKey = (row: object): string => {
  const existingKey = realConsumptionRowKeys.get(row);

  if (existingKey !== undefined) {
    return existingKey;
  }

  realConsumptionRowSequence += 1;

  const newKey = `consumo-real-${realConsumptionRowSequence}`;

  realConsumptionRowKeys.set(row, newKey);

  return newKey;
};

const productLines = computed(() =>
  processStore.selectedOrder?.consumo_insumos.filter(
    (i) => i.linea === processStore.selectedMachinePlanification?.linea_new,
  ),
);

const normalizeText = (value: string | number | null | undefined) =>
  String(value ?? '').trim().toLowerCase();

const toQuantityNumber = (value: string | number | null | undefined) => {
  if (value === null || value === undefined || value === '') return 0;

  const text = String(value).trim().replace(/\s/g, '');

  let normalized = text;

  if (text.includes(',') && text.includes('.')) {
    normalized = text.replace(/\./g, '').replace(',', '.');
  } else if (text.includes(',')) {
    normalized = text.replace(',', '.');
  }

  const number = Number(normalized.replace(/[^0-9.-]/g, ''));

  return Number.isFinite(number) ? number : 0;
};

const parseQuantityInput = (value: string | number | null | undefined) => {
  if (value === null || value === undefined || String(value).trim() === '') {
    return null;
  }

  return toQuantityNumber(value);
};

const formatQuantity = (value: string | number | null | undefined) => {
  if (value === null || value === undefined || value === '') return '';

  return new Intl.NumberFormat('es-PY', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(toQuantityNumber(value));
};

const roundQuantity = (value: number) =>
  Math.round((value + Number.EPSILON) * 1000000) / 1000000;

const consumptionCheckpointKey = computed(() =>
  processStore.selectedMachine?.id
    ? `consumption-checkpoint-${processStore.selectedMachine.id}`
    : '',
);

const consumptionCheckpoint = computed(() => {
  if (!consumptionCheckpointKey.value) return 0;

  return Number(localStorage.getItem(consumptionCheckpointKey.value) ?? 0);
});

/*
 * Este subconjunto se usa únicamente para verificar
 * los artículos pendientes del turno actual.
 *
 * La tabla muestra selectedMachineInputRows completo,
 * no currentTurnRows.
 */
const currentTurnRows = computed(() =>
  processStore.selectedMachineInputRows.slice(consumptionCheckpoint.value),
);

const missingProductLines = computed(() =>
  (productLines.value ?? []).filter(
    (item) =>
      !currentTurnRows.value.some(
        (row) => normalizeText(row.article) === normalizeText(item.insumo),
      ),
  ),
);

const showAddRowDialog = ref(false);

type NewRegisterData = {
  article: string;
  batch: string;
  initialWeight: number | null;
  finalWeight: number | null;
};

const newRegisterData = reactive<NewRegisterData>({
  article: '',
  batch: '',
  initialWeight: null,
  finalWeight: null,
});

/**
 * Autocompleta el lote recibido desde CRM al seleccionar un producto.
 *
 * Reglas:
 * - Si el insumo tiene lote cargado en la OT, lo completa automáticamente.
 * - Si el insumo no tiene lote, deja el campo vacío.
 * - El usuario siempre puede editar el lote manualmente después.
 */
watch(
  () => newRegisterData.article,
  (article) => {
    if (!article) {
      newRegisterData.batch = '';
      return;
    }

    const selectedProduct = (productLines.value ?? []).find(
      (item) =>
        normalizeText(item.insumo) === normalizeText(article),
    );

    const loteCRM = String(
      selectedProduct?.lote ?? '',
    ).trim();

    newRegisterData.batch = loteCRM;
  },
);

const columns = [
  {
    name: 'article',
    label: 'Artículo',
    field: 'article',
    align: 'left' as const,
  },
  {
    name: 'batch',
    label: 'Lote',
    field: 'batch',
    align: 'center' as const,
  },
  {
    name: 'initialWeight',
    label: 'Cantidad inicial',
    field: 'initialWeight',
    align: 'center' as const,
    type: 'number',
  },
  {
    name: 'finalWeight',
    label: 'Cantidad final',
    field: 'finalWeight',
    align: 'center' as const,
    type: 'number',
  },
  {
    name: 'consumed',
    label: 'Consumo real',
    field: 'consumed',
    align: 'center' as const,
    type: 'number',
  },
];

const handleAddRow = async () => {
  if (
    newRegisterData.initialWeight === null ||
    newRegisterData.finalWeight === null
  ) {
    return;
  }

  if (newRegisterData.finalWeight > newRegisterData.initialWeight) {
    return;
  }

  const consumed = roundQuantity(
    newRegisterData.initialWeight - newRegisterData.finalWeight,
  );

  processStore.addSelectedMachineInputRow({
    article: newRegisterData.article,
    batch: newRegisterData.batch,
    initialWeight: newRegisterData.initialWeight,
    finalWeight: newRegisterData.finalWeight,
    consumed,
  });

  await createSnapshot('input-added');

  newRegisterData.article = '';
  newRegisterData.batch = '';
  newRegisterData.initialWeight = null;
  newRegisterData.finalWeight = null;

  showAddRowDialog.value = false;
};
</script>