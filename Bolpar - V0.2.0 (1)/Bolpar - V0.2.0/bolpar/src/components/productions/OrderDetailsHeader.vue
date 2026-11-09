<template>
  <div class="row items-center gap-sm">
    <q-btn
      flat
      dense
      rounded
      no-caps
      icon="chevron_left"
      label="Volver"
      align="left"
      class="bg-grey-3 q-pr-md"
      @click="$router.go(-1)"
    />

    <div>
      <div class="text-grey-8">Máquina actual</div>
      <div class="text-weight-medium text-h5">
        {{ processStore.selectedMachinePlanification?.linea_new }}
      </div>
    </div>

    <q-space />

    <EmployeeSelector
      :employees="employees"
      :disable="
        processStore.selectedMachineStatus?.estado === MACHINE_STATE.Finished || !isEditable
      "
    />
  </div>

  <q-dialog v-model="showFinishMachineDialog" persistent>
    <q-card>
      <q-form @submit.prevent="onFinishProductionForm">
        <q-card-section style="max-width: 320px">
          <div class="text-h6">
            Finalizar {{ processStore.selectedMachinePlanification?.linea_new }}
          </div>
          <div class="text-grey-8">
            Ingrese los campos requeridos para finalizar la máquina actual
          </div>
        </q-card-section>

        <q-separator />

        <q-card-section class="column gap-sm bg-grey-1">
          <div v-for="(field, index) of currentMachineFinishInfoOptions?.fields" :key="index">
            <q-input
              outlined
              clearable
              :model-value="
                formatMoney(
                  processStore.getSelectedMachineFinishInputValues(field.value),
                ).toFormatedString()
              "
              @update:model-value="
                processStore.setSelectedMachineFinishInputValues(
                  field.value,
                  formatMoney($event?.toString() ?? '')
                    .toNumber()
                    .toString(),
                )
              "
              :label="field.label"
              :rules="[(val) => !!val || '']"
              :disable="isLoadingFinishMachine"
            />
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions>
          <div class="row justify-between full-width">
            <q-btn no-caps flat label="Cerrar" @click="showFinishMachineDialog = false" />
            <q-btn
              no-caps
              label="Confirmar"
              type="submit"
              color="primary"
              :loading="isFinishingProduction"
              :disable="isFinishingProduction"
            />
          </div>
        </q-card-actions>
      </q-form>
    </q-card>
  </q-dialog>

  <q-dialog v-model="showShiftChangeDialog" persistent>
    <q-card>
      <q-card-section class="row items-center">
        <q-form
          @submit.prevent="handleConfirmShiftChange"
          class="column gap-sm"
          :style="{ minWidth: '340px' }"
        >
          <div class="text-h6">Cambio de turno</div>

          <div class="q-mb-sm">Debe especificar el motivo del cambio de turno.</div>

          <q-select
            v-model="shiftChangeReason"
            :options="pauseReasons"
            label="Motivo"
            outlined
            behavior="dialog"
            :rules="[(val) => !!val || 'Seleccione un motivo']"
          />

          <q-input
            v-if="shiftChangeReason.startsWith('Otro')"
            v-model="shiftChangeReasonDescription"
            type="text"
            label="Especifique el motivo"
            outlined
            :rules="[(val) => !!val || 'Campo requerido']"
          />

          <div class="row justify-between q-mt-md">
            <q-btn no-caps flat label="Cerrar" @click="showShiftChangeDialog = false" />

            <q-btn no-caps label="Confirmar" type="submit" color="primary" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>

  <q-dialog v-model="showProductionPauseDialog" persistent>
    <q-card>
      <q-card-section class="row items-center">
        <q-form
          @submit.prevent="handleConfirmProductionPause"
          class="column gap-sm"
          :style="{ minWidth: '340px' }"
        >
          <div class="text-h6">Pausar producción</div>

          <div class="q-mb-sm">Debe especificar la causa de la pausa.</div>

          <q-select
            v-model="productionPauseReason"
            :options="pauseReasons"
            label="Motivo"
            outlined
            behavior="dialog"
            :rules="[(val) => !!val || 'Seleccione un motivo']"
          />

          <q-input
            v-if="productionPauseReason.startsWith('Otro')"
            v-model="productionPauseReasonDescription"
            type="text"
            label="Especifique el motivo"
            outlined
            :rules="[(val) => !!val || 'Campo requerido']"
          />

          <div class="row justify-between q-mt-md">
            <q-btn no-caps flat label="Cerrar" @click="showProductionPauseDialog = false" />

            <q-btn no-caps label="Confirmar pausa" type="submit" color="orange-9" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>

  <q-dialog v-model="showPauseTimerDialog" persistent>
    <q-card style="min-width: 380px; max-width: 92vw">
      <q-card-section class="text-center q-pa-lg">
        <q-icon name="pause_circle" size="64px" color="orange-9" />

        <div class="text-h5 text-weight-bold q-mt-md">Producción en pausa</div>

        <div class="text-grey-8 q-mt-sm">
          {{ processStore.selectedMachine?.nombre ?? 'Máquina' }}
        </div>

        <div class="q-mt-md">
          <div class="text-caption text-grey-7">Motivo</div>

          <div class="text-body1 text-weight-medium">
            {{ currentPauseReason || 'Sin motivo especificado' }}
          </div>
        </div>

        <div class="q-mt-lg">
          <div class="text-caption text-grey-7">Tiempo transcurrido</div>

          <div class="pause-timer">
            {{ formatDuration(activePauseSeconds) }}
          </div>
        </div>
      </q-card-section>

      <q-separator />

      <q-card-actions align="center" class="q-pa-md">
        <q-btn
          unelevated
          no-caps
          icon="play_arrow"
          color="blue-9"
          label="Reanudar producción"
          class="text-weight-bold"
          :loading="isResumingProduction"
          :disable="isResumingProduction"
          @click="handleStartMachineProduction"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <div v-if="showEmployeeWarning" class="employee-warning">
    No puedes iniciar producción, asigne un empleado antes
  </div>

  <q-footer class="bg-grey-2">
    <q-separator />

    <div class="row justify-between">
      <div class="row justify-between text-black q-ml-sm">
        <div v-if="preStartDateTime" class="q-px-sm q-py-xs">
          <div class="text-caption" style="opacity: 0.7">Fecha de preparación</div>
          <div class="text-weight-medium">{{ new Date(preStartDateTime).toLocaleString() }}</div>
        </div>

        <q-separator v-if="startDateTime" inset vertical spaced />

        <div v-if="startDateTime" class="q-px-sm q-py-xs">
  <div class="text-caption" style="opacity: 0.7">
    Fecha de producción
  </div>

  <div class="text-weight-medium">
    {{ new Date(startDateTime).toLocaleString() }}
  </div>
</div>

<q-separator
  v-if="finishDateTime"
  inset
  vertical
  spaced
/>

<div v-if="finishDateTime" class="q-px-sm q-py-xs">
  <div class="text-caption" style="opacity: 0.7">
    Fecha de finalización
  </div>

  <div class="text-weight-medium">
    {{ new Date(finishDateTime).toLocaleString() }}
  </div>
</div>

<q-separator
  v-if="productionStartStatus"
  inset
  vertical
  spaced
/>

        <div v-if="productionStartStatus" class="production-time-summary row items-center">
          <div class="production-time-item">
            <div class="text-caption text-grey-7">Tiempo total</div>

            <div class="text-weight-bold">
              {{ formatDuration(totalProductionSeconds) }}
            </div>
          </div>

          <q-separator inset vertical spaced />

          <div class="production-time-item">
            <div class="text-caption text-grey-7">Tiempo en pausa</div>

            <div class="text-weight-bold text-orange-9">
              {{ formatDuration(totalPausedSeconds) }}
            </div>
          </div>

          <q-separator inset vertical spaced />

          <div class="production-time-item">
            <div class="text-caption text-grey-7">Tiempo efectivo</div>

            <div class="text-weight-bold text-positive">
              {{ formatDuration(effectiveProductionSeconds) }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="isEditable" class="row justify-end gap-sm q-pa-sm">
        <q-btn
          v-if="processStore.selectedMachineStatus?.estado === MACHINE_STATE.Produccion"
          unelevated
          no-caps
          icon="groups"
          color="orange-9"
          label="Cambio de turno"
          class="text-weight-bold"
          @click="handleShiftChange"
          :disable="isLoadingFinishMachine"
        />

        <q-btn
          v-if="processStore.selectedMachineStatus?.estado === MACHINE_STATE.Produccion"
          unelevated
          no-caps
          icon="pause"
          color="amber-9"
          label="Pausa"
          class="text-weight-bold"
          @click="handleProductionPause"
          :disable="isLoadingFinishMachine"
        />

        <q-btn
          v-if="
            !processStore.selectedMachineStatusIsOneOf([
              MACHINE_STATE.Paused,
              MACHINE_STATE.Finished,
            ])
          "
          unelevated
          no-caps
          color="blue-12"
          :label="actionButtonLabel"
          class="text-weight-bold"
          @click="handlePressActionButton"
          :loading="isLoadingFinishMachine"
        />

        <div
          v-else-if="
            processStore.selectedMachineStatus?.estado === MACHINE_STATE.Paused &&
            currentPauseType === 'SHIFT_CHANGE'
          "
          class="row items-center gap-sm"
        >
          <div class="text-grey-7">Cambio de turno</div>

          <q-btn
            unelevated
            no-caps
            icon="play_arrow"
            color="blue-9"
            label="Iniciar nuevo turno"
            class="text-weight-bold"
            :loading="isResumingProduction"
            :disable="isResumingProduction"
            @click="handleStartMachineProduction"
          />
        </div>
      </div>
    </div>
  </q-footer>
</template>

<script setup lang="ts">
import { MACHINE_STATE, type MachineProcess } from 'src/queries/models/machines.model';
import { usePreStartMachineQuery } from 'src/queries/pre-start-machine.query';
import { useQuasar } from 'quasar';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useCreateMachineStatus } from 'src/queries/create-machine-status.query';
import { useFinishMachineQuery } from 'src/queries/finish-machine-production.query';
import { formatMoney } from 'src/utils/money.utils';
import { useGetEmployees } from 'src/queries/get-employees-query';
import EmployeeSelector from 'src/components/employees/EmployeeSelector.vue';
import { useProcessStore } from 'src/stores/process.store';
import { useGetMachinesQuery } from 'src/queries/get-ot-machines.query';
import { useCreateSnapshot } from 'src/queries/create-snapshot-query';
import { finishMachineInfoOptions } from 'src/utils/machine-options';
import { useListSnapshots } from 'src/queries/list-snapshots-query';
import { addActionHistory } from 'src/utils/action/history';
import { useUserStore } from 'src/stores/user.store';
import { useSetMachineAssignedEmployees } from 'src/queries/set-machine-assigned-employees';

const $q = useQuasar();

const processStore = useProcessStore();
const userStore = useUserStore();

const showFinishMachineDialog = ref(false);

// Modal de cambio de turno
const showShiftChangeDialog = ref(false);
const shiftChangeReason = ref('');
const shiftChangeReasonDescription = ref('');

// Modal para pedir el motivo de una pausa normal
const showProductionPauseDialog = ref(false);
const productionPauseReason = ref('');
const productionPauseReasonDescription = ref('');

// Modal y estado de reanudación
const showPauseTimerDialog = ref(false);
const isResumingProduction = ref(false);
const currentTimestamp = ref(Date.now());
const pauseStorageVersion = ref(0);

let pauseTimerInterval: ReturnType<typeof setInterval> | null = null;

const showEmployeeWarning = ref(false);
const isFinishingProduction = ref(false);

const { getMachines } = useGetMachinesQuery();
const { preStartMachine } = usePreStartMachineQuery();
const { createMachineStatus } = useCreateMachineStatus();
const { finishMachineProduction, isLoadingFinishMachineProduction } = useFinishMachineQuery();
const { createSnapshot, isCreatingSnapshot } = useCreateSnapshot();
const { setMachineAssignedEmployees, isLoadingSetMachineAssignedEmployees } =
  useSetMachineAssignedEmployees();

const selectedMachineId = computed(() => processStore.selectedMachine?.id);
const { refetchSnapshots } = useListSnapshots(selectedMachineId);
const { employees } = useGetEmployees();

const isLoadingFinishMachine = computed(() => {
  return (
    isLoadingFinishMachineProduction.value ||
    isCreatingSnapshot.value ||
    isLoadingSetMachineAssignedEmployees.value ||
    isFinishingProduction.value
  );
});

const pauseReasons = [
  'Set Up (Del Proceso)',
  'Ajuste Operacional (Del Proceso)',
  'Paradas por Mantenimeinto preventivo (Del Proceso)',
  'Espera de Aprobacion de Impresión (Del Proceso)',
  'Cambio de turnos (Del Proceso)',
  'Paradas por Mantenimeinto Correctivo',
  'Corte de energia electrica',
  'Falta de Personal',
  'Llegadas Tardias del Personal',
  'Falta de Insumos o Materias Primas por defectos',
  'Parada por Reunion',
  'Parada por Accidente',
  'Otro (Ingresar el motivo)',
];

const currentMachineFinishInfoOptions = computed(() =>
  finishMachineInfoOptions.find((option) =>
    option.isName(processStore.selectedMachine?.nombre ?? ''),
  ),
);

const getSelectedEmployees = () => {
  return processStore.selectedMachineLoadedData?.selectedEmployeesId ?? [];
};

const notifyNoEmployees = () => {
  showEmployeeWarning.value = true;

  setTimeout(() => {
    showEmployeeWarning.value = false;
  }, 4000);
};

const validateEmployeesBeforeStart = () => {
  const selectedEmployees = getSelectedEmployees();

  if (selectedEmployees.length === 0) {
    notifyNoEmployees();
    return false;
  }

  return true;
};

/**
 * IMPORTANTE:
 * La lista de órdenes que ve cada módulo contiene únicamente la planificación
 * correspondiente a esa máquina. Por eso NO podemos guardar en el store todas
 * las máquinas de la OT después de un cambio de estado: eso desalineaba
 * selectedMachineIndex con planificacion_produccion y obligaba a salir/entrar
 * de la pantalla para que los botones se actualizaran.
 */
const getMachineCode = (value: string | number | null | undefined) => {
  const match = String(value ?? '').trim().match(/^(\d+)/);
  return match?.[1] ?? '';
};

const findMachineForCurrentPlan = (
  machines: MachineProcess[],
  preferredMachineId?: number,
) => {
  const plan = processStore.selectedOrder?.planificacion_produccion?.[0];
  const planCode = getMachineCode(plan?.linea_new || plan?.linea);

  const candidates = machines.filter((machine) => {
    const machineCode = getMachineCode(machine.nombre);

    if (planCode && machineCode) {
      return planCode === machineCode;
    }

    return normalizeText(machine.nombre) === normalizeText(plan?.linea_new || plan?.linea);
  });

  if (preferredMachineId) {
    const preferred = candidates.find((machine) => machine.id === preferredMachineId);
    if (preferred) return preferred;
  }

  const currentMachineId = processStore.selectedMachine?.id;
  if (currentMachineId) {
    const current = candidates.find((machine) => machine.id === currentMachineId);
    if (current) return current;
  }

  // Si hubiera registros duplicados de una misma máquina, usamos el más nuevo.
  return [...candidates].sort((a, b) => Number(b.id) - Number(a.id))[0];
};

const handleStatusChange = async (preferredMachineId?: number) => {
  if (!processStore.selectedOrder?.id) return;

  const currentOrder = processStore.selectedOrder;
  const allMachines = await getMachines(currentOrder.id);
  const currentMachine = findMachineForCurrentPlan(allMachines, preferredMachineId);

  // El store de esta pantalla debe contener SOLO la máquina del módulo actual.
  processStore.selectOrder(currentOrder, currentMachine ? [currentMachine] : []);
  processStore.selectMachine(0);

  // Garantiza que computed/template vean el nuevo estado antes de continuar.
  await nextTick();
};

const normalizeText = (value: string | number | null | undefined) =>
  String(value ?? '')
    .trim()
    .toLowerCase();

const consumptionCheckpointKey = computed(() =>
  processStore.selectedMachine?.id
    ? `consumption-checkpoint-${processStore.selectedMachine.id}`
    : '',
);

const pauseTypeKey = computed(() =>
  processStore.selectedMachine?.id ? `pause-type-${processStore.selectedMachine.id}` : '',
);

const pauseReasonKey = computed(() =>
  processStore.selectedMachine?.id ? `pause-reason-${processStore.selectedMachine.id}` : '',
);

const getStorageValue = (key: string, storageVersion: number) => {
  void storageVersion;

  if (!key) return '';

  return localStorage.getItem(key) ?? '';
};

const currentPauseType = computed(() =>
  getStorageValue(pauseTypeKey.value, pauseStorageVersion.value),
);

const currentPauseReason = computed(() =>
  getStorageValue(pauseReasonKey.value, pauseStorageVersion.value),
);

const activePauseDateTime = computed(() => {
  if (
    processStore.selectedMachineStatus?.estado !== MACHINE_STATE.Paused ||
    currentPauseType.value !== 'PRODUCTION_PAUSE'
  ) {
    return null;
  }

  return processStore.selectedMachineStatus?.fecha_hora ?? null;
});

const activePauseSeconds = computed(() => {
  if (!activePauseDateTime.value) return 0;

  const pauseStartedAt = new Date(activePauseDateTime.value).getTime();

  if (Number.isNaN(pauseStartedAt)) return 0;

  return Math.max(0, Math.floor((currentTimestamp.value - pauseStartedAt) / 1000));
});

const formatDuration = (totalSeconds: number) => {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));

  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const seconds = safeSeconds % 60;

  return [hours, minutes, seconds].map((value) => value.toString().padStart(2, '0')).join(':');
};

onMounted(() => {
  currentTimestamp.value = Date.now();

  pauseTimerInterval = setInterval(() => {
    currentTimestamp.value = Date.now();
  }, 1000);
});

onBeforeUnmount(() => {
  if (pauseTimerInterval) {
    clearInterval(pauseTimerInterval);
    pauseTimerInterval = null;
  }
});
watch(
  [() => processStore.selectedMachineStatus?.estado, () => currentPauseType.value],
  ([status, pauseType]) => {
    showPauseTimerDialog.value =
      status === MACHINE_STATE.Paused && pauseType === 'PRODUCTION_PAUSE';
  },
  {
    immediate: true,
  },
);

const consumptionCheckpoint = computed(() => {
  // Fuerza la relectura del checkpoint cuando cambia el estado/turno.
  void pauseStorageVersion.value;
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

const plannedConsumptionArticles = computed(
  () =>
    processStore.selectedOrder?.consumo_insumos.filter(
      (item) => item.linea === processStore.selectedMachinePlanification?.linea_new,
    ) ?? [],
);

/**
 * Producto medio que generó la etapa anterior.
 * No forma parte de D_CONSUMO_DE_INSUMOS: se calcula a partir de
 * PLANIFICACION_PRODUCCION y debe registrarse como consumo real
 * en la máquina actual.
 */
const previousMediumProduct = computed(
  () => processStore.selectedMachinePlanification?.producto_medio_anterior?.trim() ?? '',
);

/**
 * Lista completa de productos obligatorios para el turno actual:
 * - insumos planificados de esta máquina;
 * - producto medio recibido de la etapa anterior, si existe.
 */
const requiredConsumptionNames = computed(() => {
  const names = plannedConsumptionArticles.value
    .map((item) => item.insumo)
    .filter((item) => Boolean(item?.trim()));

  if (
    previousMediumProduct.value &&
    !names.some((item) => normalizeText(item) === normalizeText(previousMediumProduct.value))
  ) {
    names.unshift(previousMediumProduct.value);
  }

  return names.filter(
    (item, index) =>
      names.findIndex((candidate) => normalizeText(candidate) === normalizeText(item)) === index,
  );
});

const missingConsumptionNames = computed(() =>
  requiredConsumptionNames.value.filter(
    (productName) =>
      !currentTurnRows.value.some(
        (row) => normalizeText(row.article) === normalizeText(productName),
      ),
  ),
);

const validateCurrentTurnConsumption = () => {
  if (missingConsumptionNames.value.length > 0) {
    $q.notify({
      type: 'negative',
      message: `Debe cargar un registro de consumo real para todos los artículos. Faltan: ${missingConsumptionNames.value.join(', ')}`,
      timeout: 7000,
    });

    return false;
  }

  return true;
};

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

const validateOverpassJustifications = () => {
  const missingJustifications = plannedConsumptionArticles.value.filter((item) => {
    const planQuantity = Number(item.cantidad ?? 0);

    const currentTurnRealQuantity = currentTurnRows.value
      .filter((row) => normalizeText(row.article) === normalizeText(item.insumo))
      .reduce((acc, row) => acc + Number(row.consumed || 0), 0);

    const reasonKey = makeReasonKey(item.insumo);
    const justification = processStore.overpassReasons?.[reasonKey];

    /*
     * La justificación se evalúa POR TURNO.
     * Lo consumido en turnos anteriores no obliga a justificar nuevamente
     * si el turno actual no supera por sí mismo la cantidad planificada.
     */
    const requiresCurrentTurnJustification =
      currentTurnRealQuantity > planQuantity;

    return requiresCurrentTurnJustification && !String(justification ?? '').trim();
  });

  if (missingJustifications.length > 0) {
    $q.notify({
      type: 'negative',
      message: `No puede finalizar la producción hasta agregar todas las justificaciones requeridas del turno actual. Faltan: ${missingJustifications
        .map((item) => item.insumo)
        .join(', ')}`,
      timeout: 7000,
    });

    return false;
  }

  return true;
};

const handleFinishMachineProduction = () => {
  if (!validateCurrentTurnConsumption()) return;
  if (!validateOverpassJustifications()) return;

  showFinishMachineDialog.value = true;
};

const onFinishProductionForm = async () => {
  if (isFinishingProduction.value) return;

  if (!validateCurrentTurnConsumption()) return;
  if (!validateOverpassJustifications()) return;

  if (
    !processStore.selectedOrder?.id ||
    !processStore.selectedMachinePlanification ||
    !processStore.selectedMachine?.id
  ) {
    return;
  }

  const selectedIndex = processStore.selectedMachineIndex;

  isFinishingProduction.value = true;
  $q.loading.show();

  try {
    await finishMachineProduction({
      machineId: processStore.selectedMachine.id,
      machineData: {
        processData: processStore.selectedMachineFinishInputValues,
        registers: processStore.selectedMachineLoadedData,
        selectedEmployeesId: processStore.selectedMachineLoadedData?.selectedEmployeesId,
      },
    });

    showFinishMachineDialog.value = false;

    await createSnapshot('final-consumption-added');
    await refetchSnapshots();
    await handleStatusChange();

    const nextIndex = selectedIndex + 1;

    if (nextIndex < processStore.machines.length) {
      processStore.selectMachine(nextIndex);
    } else {
      processStore.selectMachine(selectedIndex);
    }

    $q.notify({
      type: 'positive',
      message: 'Producción finalizada correctamente.',
    });
  } catch (error) {
    console.error(error);

    $q.notify({
      type: 'negative',
      message: 'No se pudo finalizar la producción.',
    });
  } finally {
    isFinishingProduction.value = false;
    $q.loading.hide();
  }
};

const handlePressActionButton = async () => {
  const selectedMachineStatus = processStore.selectedMachineStatus;

  if (!selectedMachineStatus) {
    if (!processStore.selectedOrder?.id || !processStore.selectedMachinePlanification) return;
    if (!validateEmployeesBeforeStart()) return;

    const selectedEmployees = getSelectedEmployees().map(String);

    $q.loading.show();

    try {
      const createdMachine = await preStartMachine({
        machineName: processStore.selectedMachinePlanification.linea_new,
        machineNumber:
          (processStore.selectedOrder.authorized_machine_index ?? processStore.machines.length) + 1,
        orderId: processStore.selectedOrder.id,
        data: {
          selectedEmployeesId: selectedEmployees,
        },
      });

      await setMachineAssignedEmployees({
        machineId: createdMachine.id,
        employeesIds: selectedEmployees.map(Number),
        assignedBy: userStore.username || 'unknown',
      });

      await createMachineStatus({
        machineId: createdMachine.id,
        machineStatus: MACHINE_STATE.Produccion,
        reason: '',
      });

      await handleStatusChange(createdMachine.id);
      processStore.setSelectedMachineEmployees(selectedEmployees);

      await createSnapshot('employees-assigned');
      await refetchSnapshots();

      addActionHistory(
        'Inicio de producción',
        `Usuario ${userStore.username || 'Usuario'} inició producción en ${
          processStore.selectedMachinePlanification?.linea_new ?? 'máquina'
        } - OT ${processStore.selectedOrder?.id}`,
        'play_circle',
        'green',
      );
    } catch (error) {
      console.error(error);

      $q.notify({
        type: 'negative',
        message: 'No se pudo iniciar producción.',
      });
    } finally {
      $q.loading.hide();
    }

    return;
  }

  if (selectedMachineStatus.estado === MACHINE_STATE.Finished) {
    await handleReStartMachineProduction();
    return;
  }

  if (selectedMachineStatus.estado === MACHINE_STATE.Started) {
    await handleStartMachineProduction();
    return;
  }

  if (selectedMachineStatus.estado === MACHINE_STATE.Produccion) {
    handleFinishMachineProduction();
  }
};

const handleReStartMachineProduction = async () => {
  if (
    !processStore.selectedOrder?.id ||
    !processStore.selectedMachinePlanification ||
    !processStore.selectedMachine?.id
  ) {
    return;
  }

  if (!validateEmployeesBeforeStart()) return;

  const machineId = processStore.selectedMachine.id;

  $q.loading.show();

  try {
    await createMachineStatus({
      machineId,
      machineStatus: MACHINE_STATE.Started,
      reason: '',
    });

    shiftChangeReason.value = '';
    shiftChangeReasonDescription.value = '';

    addActionHistory(
      'Inicio de nueva producción',
      `Usuario ${userStore.username || 'Usuario'} inició nueva producción en ${
        processStore.selectedMachine?.nombre ?? 'máquina'
      } - OT ${processStore.selectedOrder?.id}`,
      'play_circle',
      'grey',
    );

    await handleStatusChange(machineId);
  } catch (error) {
    console.error(error);

    $q.notify({
      type: 'negative',
      message: 'No se pudo reiniciar producción.',
    });
  } finally {
    $q.loading.hide();
  }
};

const handleStartMachineProduction = async () => {
  if (
    !processStore.selectedOrder?.id ||
    !processStore.selectedMachinePlanification ||
    !processStore.selectedMachine?.id
  ) {
    return;
  }

  const machineId = processStore.selectedMachine.id;

  const isPaused = processStore.selectedMachineStatus?.estado === MACHINE_STATE.Paused;

  const isProductionPause = isPaused && currentPauseType.value === 'PRODUCTION_PAUSE';

  const isShiftChange = isPaused && currentPauseType.value === 'SHIFT_CHANGE';

  /*
   * Una pausa normal conserva los empleados y los consumos.
   * Un cambio de turno requiere seleccionar empleados nuevamente.
   */
  if (!isProductionPause && !validateEmployeesBeforeStart()) return;

  isResumingProduction.value = isPaused;

  $q.loading.show();

  try {
    await createMachineStatus({
      machineId,
      machineStatus: MACHINE_STATE.Produccion,
      reason: isShiftChange
        ? 'Inicio de nuevo turno'
        : isProductionPause
          ? 'Reanudación después de pausa'
          : 'Inicio de producción',
    });

    const historyTitle = isShiftChange
      ? 'Inicio de nuevo turno'
      : isProductionPause
        ? 'Reanudación de producción'
        : 'Inicio de producción';

    const historyAction = isShiftChange
      ? 'inició un nuevo turno'
      : isProductionPause
        ? 'reanudó'
        : 'inició';

    addActionHistory(
      historyTitle,
      `Usuario ${userStore.username || 'Usuario'} ${historyAction} producción en ${
        processStore.selectedMachine?.nombre ?? 'máquina'
      } - OT ${processStore.selectedOrder?.id}`,
      isProductionPause ? 'play_arrow' : 'play_circle',
      'green',
    );

    productionPauseReason.value = '';
    productionPauseReasonDescription.value = '';

    if (pauseTypeKey.value) {
      localStorage.removeItem(pauseTypeKey.value);
    }

    if (pauseReasonKey.value) {
      localStorage.removeItem(pauseReasonKey.value);
    }

    pauseStorageVersion.value += 1;
    showPauseTimerDialog.value = false;

    await handleStatusChange(machineId);
  } catch (error) {
    console.error(error);

    $q.notify({
      type: 'negative',
      message: isProductionPause
        ? 'No se pudo reanudar la producción.'
        : isShiftChange
          ? 'No se pudo iniciar el nuevo turno.'
          : 'No se pudo iniciar producción.',
    });
  } finally {
    isResumingProduction.value = false;
    $q.loading.hide();
  }
};

const handleShiftChange = () => {
  if (!validateCurrentTurnConsumption()) return;
  if (!validateOverpassJustifications()) return;

  shiftChangeReason.value = '';
  shiftChangeReasonDescription.value = '';
  showShiftChangeDialog.value = true;
};

const handleProductionPause = () => {
  productionPauseReason.value = '';
  productionPauseReasonDescription.value = '';
  showProductionPauseDialog.value = true;
};
const handleConfirmProductionPause = async () => {
  if (
    !processStore.selectedOrder?.id ||
    !processStore.selectedMachinePlanification ||
    !processStore.selectedMachine?.id
  ) {
    return;
  }

  const reason = productionPauseReason.value.startsWith('Otro')
    ? productionPauseReasonDescription.value.trim()
    : productionPauseReason.value;

  if (!reason) {
    $q.notify({
      type: 'negative',
      message: 'Debe seleccionar una causa para la pausa.',
    });

    return;
  }

  const machineId = processStore.selectedMachine.id;

  $q.loading.show();

  try {
    await createMachineStatus({
      machineId,
      machineStatus: MACHINE_STATE.Paused,
      reason: `PAUSA DE PRODUCCIÓN: ${reason}`,
    });

    if (pauseTypeKey.value) {
      localStorage.setItem(pauseTypeKey.value, 'PRODUCTION_PAUSE');
    }

    if (pauseReasonKey.value) {
      localStorage.setItem(pauseReasonKey.value, reason);
    }

    pauseStorageVersion.value += 1;
    currentTimestamp.value = Date.now();

    addActionHistory(
      'Pausa de producción',
      `Usuario ${userStore.username || 'Usuario'} pausó la producción en ${
        processStore.selectedMachine?.nombre ?? 'máquina'
      } - OT ${processStore.selectedOrder?.id}. Motivo: ${reason}`,
      'pause_circle',
      'orange',
    );

    productionPauseReason.value = '';
    productionPauseReasonDescription.value = '';
    showProductionPauseDialog.value = false;

    /*
     * Una pausa normal conserva:
     * - empleados;
     * - consumos cargados;
     * - justificaciones;
     * - checkpoint del turno.
     */
    await handleStatusChange(machineId);
    showPauseTimerDialog.value = true;
  } catch (error) {
    console.error(error);

    $q.notify({
      type: 'negative',
      message: 'No se pudo pausar la producción.',
    });
  } finally {
    $q.loading.hide();
  }
};

const handleConfirmShiftChange = async () => {
  if (
    !processStore.selectedOrder?.id ||
    !processStore.selectedMachinePlanification ||
    !processStore.selectedMachine?.id
  ) {
    return;
  }

  const reason = shiftChangeReason.value.startsWith('Otro')
    ? shiftChangeReasonDescription.value.trim()
    : shiftChangeReason.value;

  if (!reason) {
    $q.notify({
      type: 'negative',
      message: 'Debe seleccionar un motivo para el cambio de turno.',
    });

    return;
  }

  const machineId = processStore.selectedMachine.id;

  $q.loading.show();

  try {
    /*
     * Temporalmente PAUSED representa también el cambio de turno.
     * pauseTypeKey permite distinguirlo de una pausa normal.
     */
    await createMachineStatus({
      machineId,
      machineStatus: MACHINE_STATE.Paused,
      reason: `CAMBIO DE TURNO: ${reason}`,
    });

    if (pauseTypeKey.value) {
      localStorage.setItem(pauseTypeKey.value, 'SHIFT_CHANGE');
    }

    if (pauseReasonKey.value) {
      localStorage.removeItem(pauseReasonKey.value);
    }

    /*
     * Todo lo cargado hasta este momento pertenece al turno anterior.
     * Los registros anteriores no contarán para el turno nuevo.
     *
     * IMPORTANTE:
     * primero actualizamos el checkpoint y recién después incrementamos
     * pauseStorageVersion, para que los computed lean el valor NUEVO.
     */
    if (consumptionCheckpointKey.value) {
      localStorage.setItem(
        consumptionCheckpointKey.value,
        processStore.selectedMachineInputRows.length.toString(),
      );
    }

    pauseStorageVersion.value += 1;
    showPauseTimerDialog.value = false;

    /*
     * El cambio de turno sí debe solicitar empleados nuevamente.
     * Se limpia tanto en el backend como en el estado local.
     */
    await setMachineAssignedEmployees({
      machineId,
      employeesIds: [],
      assignedBy: userStore.username || 'unknown',
    });

    processStore.setSelectedMachineEmployees([]);

    addActionHistory(
      'Cambio de turno',
      `Usuario ${userStore.username || 'Usuario'} realizó cambio de turno en ${
        processStore.selectedMachine?.nombre ?? 'máquina'
      } - OT ${processStore.selectedOrder?.id}. Motivo: ${reason}`,
      'groups',
      'orange',
    );

    shiftChangeReason.value = '';
    shiftChangeReasonDescription.value = '';
    showShiftChangeDialog.value = false;

    await handleStatusChange(machineId);
    processStore.setSelectedMachineEmployees([]);
  } catch (error) {
    console.error(error);

    $q.notify({
      type: 'negative',
      message: 'No se pudo realizar el cambio de turno.',
    });
  } finally {
    $q.loading.hide();
  }
};

const actionButtonLabel = computed(() => {
  const labels = {
    _default: 'Iniciar Producción',
    [MACHINE_STATE.Started]: 'Iniciar Producción',
    [MACHINE_STATE.Paused]: 'Reanudar Producción',
    [MACHINE_STATE.Produccion]: 'Finalizar Producción',
    [MACHINE_STATE.Finished]: 'Finalizado',
  } as const;

  return !processStore.selectedMachineStatus
    ? labels._default
    : labels[processStore.selectedMachineStatus.estado];
});

const chronologicalStatus = computed(() => {
  return [...(processStore.selectedMachine?.status_logs ?? [])].sort(
    (a, b) => new Date(a.fecha_hora).getTime() - new Date(b.fecha_hora).getTime(),
  );
});

const getStatusReason = (status: unknown): string => {
  const statusData = status as {
    reason?: string | null;
    motivo?: string | null;
    razon?: string | null;
  };

  return String(statusData.reason ?? statusData.motivo ?? statusData.razon ?? '').trim();
};

/*
 * Primer registro en el que realmente comenzó la producción.
 */
const productionStartStatus = computed(() => {
  return chronologicalStatus.value.find((status) => status.estado === MACHINE_STATE.Produccion);
});

/*
 * Último registro de finalización.
 */
const productionFinishStatus = computed(() => {
  return [...chronologicalStatus.value]
    .reverse()
    .find((status) => status.estado === MACHINE_STATE.Finished);
});

/*
 * Tiempo total:
 * desde el primer inicio de producción hasta finalizar.
 * Si todavía no finalizó, se calcula hasta la hora actual.
 */
const totalProductionSeconds = computed(() => {
  if (!productionStartStatus.value?.fecha_hora) {
    return 0;
  }

  const startTime = new Date(productionStartStatus.value.fecha_hora).getTime();

  const endTime = productionFinishStatus.value?.fecha_hora
    ? new Date(productionFinishStatus.value.fecha_hora).getTime()
    : currentTimestamp.value;

  if (Number.isNaN(startTime) || Number.isNaN(endTime)) {
    return 0;
  }

  return Math.max(0, Math.floor((endTime - startTime) / 1000));
});

/*
 * Suma únicamente las pausas normales.
 *
 * No cuenta los cambios de turno porque esos registros
 * se guardan con el texto "CAMBIO DE TURNO".
 */
const totalPausedSeconds = computed(() => {
  const statusLogs = chronologicalStatus.value;

  let totalMilliseconds = 0;
  let pauseStartedAt: number | null = null;

  for (const status of statusLogs) {
    const statusTime = new Date(status.fecha_hora).getTime();

    if (Number.isNaN(statusTime)) {
      continue;
    }

    const reason = getStatusReason(status).toUpperCase();

    const isNormalProductionPause =
      status.estado === MACHINE_STATE.Paused &&
      (reason.startsWith('PAUSA DE PRODUCCIÓN') || reason.startsWith('PAUSA DE PRODUCCION'));

    if (isNormalProductionPause) {
      /*
       * Evita abrir dos pausas al mismo tiempo
       * si hubiese registros duplicados.
       */
      if (pauseStartedAt === null) {
        pauseStartedAt = statusTime;
      }

      continue;
    }

    /*
     * La pausa termina con el siguiente estado PRODUCCION.
     */
    if (pauseStartedAt !== null && status.estado === MACHINE_STATE.Produccion) {
      totalMilliseconds += Math.max(0, statusTime - pauseStartedAt);

      pauseStartedAt = null;
    }
  }

  /*
   * Si sigue pausado actualmente, cuenta hasta ahora.
   */
  if (pauseStartedAt !== null) {
    totalMilliseconds += Math.max(0, currentTimestamp.value - pauseStartedAt);
  }

  return Math.max(0, Math.floor(totalMilliseconds / 1000));
});

/*
 * Tiempo efectivo:
 * tiempo total menos todas las pausas normales.
 */
const effectiveProductionSeconds = computed(() => {
  return Math.max(0, totalProductionSeconds.value - totalPausedSeconds.value);
});

const sortedStatus = computed(() => {
  return (
    processStore.selectedMachine?.status_logs?.toSorted(
      (a, b) => new Date(b.fecha_hora).getTime() - new Date(a.fecha_hora).getTime(),
    ) ?? []
  );
});

const preStartDateTime = computed(
  () => sortedStatus.value.find((status) => status.estado === MACHINE_STATE.Started)?.fecha_hora,
);

const startDateTime = computed(
  () => sortedStatus.value.find((status) => status.estado === MACHINE_STATE.Produccion)?.fecha_hora,
);

const finishDateTime = computed(
  () =>
    [...sortedStatus.value]
      .find((status) => status.estado === MACHINE_STATE.Finished)
      ?.fecha_hora ?? null,
);

const isEditable = computed(() => {
  return (
    processStore.selectedOrder?.status !== 'completado' &&
    processStore.selectedOrder?.machine_flow_status !== 'finished'
  );
});
</script>

<style scoped>
.production-time-summary {
  padding: 4px 8px;
  gap: 2px;
}

.production-time-item {
  min-width: 110px;
  padding: 2px 8px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.pause-timer {
  margin-top: 8px;
  font-size: clamp(2.5rem, 8vw, 4rem);
  line-height: 1;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 4px;
}

.employee-warning {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 99999;
  background: #c10015;
  color: #fff;
  padding: 12px 18px;
  border-radius: 8px;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
</style>
