<template>
  <q-table
    v-if="rows.length > 0"
    flat
    bordered
    title="Plan de consumo"
    :rows="rows"
    :columns="columns"
    :pagination="{ page: 1, rowsPerPage: 0 }"
    :rows-per-page-options="[0]"
    row-key="reasonKey"
    class="full-width"
  >
    <template #body-cell="props">
      <q-td :props="props" :style="{ whiteSpace: 'normal' }">
        <OverpassReasonSelector
          v-if="props.col.name === 'reason' && props.row.requiresCurrentTurnJustification"
          :model-value="processStore.overpassReasons[props.row.reasonKey]"
          @update:model-value="(value) => handleUpdateReason(props.row.reasonKey, value)"
        />

        <div
          v-else-if="props.col.name === 'reason' && props.row.previousReason"
          class="text-positive text-weight-medium"
          :style="{ maxWidth: '360px' }"
        >
          {{ props.row.previousReason }}
        </div>

        <div
          v-else-if="props.col.name === 'reason' && props.row.totalOverpass"
          class="text-grey-7"
          :style="{ maxWidth: '320px' }"
        >
          Justificado en turno anterior
        </div>

        <div v-else-if="props.col.type === 'number'" :style="{ maxWidth: '250px' }">
          {{ formatQuantity(props.row[props.col.name]) }}
        </div>

        <div v-else :style="{ maxWidth: '250px' }">
          {{ props.row[props.col.name] }}
        </div>
      </q-td>
    </template>

    <template #bottom>
      <div class="row gap-sm">
        <div class="text-right q-px-sm q-py-xs">Cantidad de artículos</div>

        <div class="text-right bg-grey-3 q-px-sm q-py-xs text-subtitle2 rounded-borders-xs">
          Total: {{ rows.length }}
        </div>

        <div class="text-right bg-red-3 q-px-sm q-py-xs text-subtitle2 rounded-borders-xs">
          Sobrepasado: {{ overpassQuantity }}
        </div>
      </div>
    </template>
  </q-table>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useProcessStore } from 'src/stores/process.store';
import OverpassReasonSelector from './OverpassReasonSelector.vue';
import { useCreateSnapshot } from 'src/queries/create-snapshot-query';

const processStore = useProcessStore();
const { createSnapshot } = useCreateSnapshot();

const normalizeText = (value: string | number | null | undefined) =>
  String(value ?? '').trim().toLowerCase();

const formatQuantity = (value: string | number | null | undefined) => {
  const numberValue = Number(value ?? 0);

  if (!Number.isFinite(numberValue)) {
    return '0';
  }

  return new Intl.NumberFormat('es-PY', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 6,
  }).format(numberValue);
};

const consumptionCheckpointKey = computed(() =>
  processStore.selectedMachine?.id
    ? `consumption-checkpoint-${processStore.selectedMachine.id}`
    : '',
);

const consumptionCheckpoint = computed(() => {
  /*
   * localStorage no es reactivo.
   * Estas dependencias obligan a releer el checkpoint cuando:
   * - cambia el estado de la máquina (por ejemplo, cambio de turno);
   * - cambia la cantidad de registros de consumo.
   */
  void processStore.selectedMachineStatus?.fecha_hora;
  void processStore.selectedMachineInputRows.length;

  if (!consumptionCheckpointKey.value) return 0;

  const storedCheckpoint = Number(
    localStorage.getItem(consumptionCheckpointKey.value) ?? 0,
  );

  if (!Number.isFinite(storedCheckpoint) || storedCheckpoint < 0) {
    return 0;
  }

  return Math.min(
    storedCheckpoint,
    processStore.selectedMachineInputRows.length,
  );
});

const currentTurnRows = computed(() =>
  processStore.selectedMachineInputRows.slice(consumptionCheckpoint.value),
);

const makeArticleKey = (article: string | number | null | undefined) => {
  const machineName = processStore.selectedMachinePlanification?.linea_new ?? '';
  return `${normalizeText(machineName)}__${normalizeText(article)}`;
};

const makeReasonKey = (article: string | number | null | undefined) => {
  const machineId = processStore.selectedMachine?.id ?? 'no-machine';
  const turnStart = consumptionCheckpoint.value;
  const articleKey = makeArticleKey(article);

  return `overpass__machine-${machineId}__turn-${turnStart}__${articleKey}`;
};

const toCleanText = (value: unknown) => {
  if (value == null) return '';

  if (typeof value === 'string') {
    return value.trim();
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value).trim();
  }

  return '';
};

const getReasonText = (value: unknown) => {
  const directValue = toCleanText(value);

  if (directValue) {
    return directValue;
  }

  if (typeof value !== 'object' || Array.isArray(value)) {
    return '';
  }

  const valueAsRecord = value as Record<string, unknown>;

  return (
    toCleanText(valueAsRecord.label) ||
    toCleanText(valueAsRecord.name) ||
    toCleanText(valueAsRecord.value) ||
    toCleanText(valueAsRecord.reason)
  );
};

const findPreviousReason = (
  article: string | number | null | undefined,
  currentKey: string,
  rowIndex: number,
) => {
  const reasons = processStore.overpassReasons ?? {};
  const articleKey = makeArticleKey(article);
  const normalizedArticle = normalizeText(article);
  const legacyIndexKey = String(rowIndex);

  const legacyIndexReason = getReasonText(reasons[legacyIndexKey]);

  if (legacyIndexReason) {
    return legacyIndexReason;
  }

  const previousEntry = Object.entries(reasons)
    .reverse()
    .find(([key, value]) => {
      const reason = getReasonText(value);

      if (!reason) return false;
      if (key === currentKey) return false;

      return (
        key === articleKey ||
        key === legacyIndexKey ||
        key.endsWith(`__${articleKey}`) ||
        key.includes(articleKey) ||
        key.includes(normalizedArticle)
      );
    });

  return previousEntry ? getReasonText(previousEntry[1]) : '';
};

const handleUpdateReason = async (reasonKey: string, value: string) => {
  const updatedReasons = {
    ...processStore.overpassReasons,
    [reasonKey]: value,
  };

  /*
   * Usamos el setter del store para que el estado quede actualizado
   * ANTES de crear el snapshot.
   */
  processStore.setSelectedMachineOverpassReasons(updatedReasons);

  await createSnapshot('justification-added');
};

const rows = computed(
  () =>
    processStore.selectedOrder?.consumo_insumos
      .filter((i) => i.linea === processStore.selectedMachinePlanification?.linea_new)
      .map((i, index) => {
        const planQuantity = Number(i.cantidad ?? 0);

        const totalRealQuantity = processStore.selectedMachineInputRows
          .filter((r) => normalizeText(r.article) === normalizeText(i.insumo))
          .reduce((acc, r) => acc + Number(r.consumed || 0), 0);

        const currentTurnRealQuantity = currentTurnRows.value
          .filter((r) => normalizeText(r.article) === normalizeText(i.insumo))
          .reduce((acc, r) => acc + Number(r.consumed || 0), 0);

        const reasonKey = makeReasonKey(i.insumo);

        /*
         * Regla correcta por turno:
         * la justificación del turno actual se exige únicamente cuando
         * EL CONSUMO DEL TURNO ACTUAL supera la cantidad planificada.
         *
         * El consumo acumulado de turnos anteriores se conserva para historial,
         * pero no obliga a justificar otra vez si este turno no se pasó.
         */
        const currentTurnOverpass = currentTurnRealQuantity > planQuantity;
        const totalOverpass = totalRealQuantity > planQuantity;

        return {
          ...i,
          cantidad: planQuantity,

          // Lo que se muestra en "Consumo real" corresponde al turno actual.
          realQuantity: currentTurnRealQuantity,

          // Se conserva el acumulado por si se necesita para historial/diagnóstico.
          totalRealQuantity,

          currentTurnRealQuantity,
          currentTurnOverpass,
          totalOverpass,
          requiresCurrentTurnJustification: currentTurnOverpass,
          reasonKey,
          previousReason: findPreviousReason(i.insumo, reasonKey, index),
        };
      }) ?? [],
);

const overpassQuantity = computed(
  () => rows.value.filter((r) => r.currentTurnOverpass).length,
);

const columns = [
  {
    name: 'insumo',
    label: 'Artículo',
    field: 'insumo',
    align: 'left' as const,
  },
  {
    name: 'cantidad',
    label: 'Cantidad plan',
    field: 'cantidad',
    align: 'center' as const,
    type: 'number',
  },
  {
    name: 'realQuantity',
    label: 'Consumo real',
    field: 'realQuantity',
    align: 'center' as const,
    type: 'number',
  },
  {
    name: 'unidad',
    label: 'Unidad',
    field: 'unidad',
    align: 'center' as const,
  },
  {
    name: 'reason',
    label: 'Justificación',
    field: 'reason',
    align: 'center' as const,
    editable: true,
  },
];
</script>