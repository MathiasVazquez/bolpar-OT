<template>
  <div style="border: solid 1px #e0e0e0; border-radius: 4px">
    <q-btn flat no-caps @click="showDialog = true" icon-right="keyboard_arrow_down">
      <div class="row items-center gap-md q-ml-xs">
        {{ selectedEmployeesId.length }}
        {{ selectedEmployeesId.length === 1 ? 'empleado' : 'empleados' }}
      </div>
    </q-btn>
  </div>

  <q-dialog v-model="showDialog" persistent>
    <q-card style="min-width: 380px">
      <q-card-section>
        <div class="text-body1 text-weight-bold q-mb-sm">Seleccionar empleados</div>
        <q-input dense outlined v-model="searchText" type="text" label="Buscar empleados" />
      </q-card-section>

      <q-separator />

      <q-card-section class="column no-wrap scroll" style="height: 50vh">
        <q-checkbox
          v-for="employee of filteredEmployees"
          :key="employee.id"
          class="full-width"
          v-model="temporalSelectedEmployeesId"
          :val="employee.id.toString()"
          :label="employee.name"
          :disable="isLoading || disable"
        />
      </q-card-section>

      <q-separator />

      <q-card-actions align="between">
        <q-btn flat no-caps label="Cerrar" @click="showDialog = false" :disable="isLoading" />

        <q-btn
          v-if="!disable"
          unelevated
          no-caps
          color="primary"
          icon="check"
          label="Confirmar"
          @click="handleConfirmSelection"
          :loading="isLoading"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { useQuasar } from 'quasar';
import { useCreateSnapshot } from 'src/queries/create-snapshot-query';
import type { Employee } from 'src/queries/get-employees-query';
import { useSetMachineAssignedEmployees } from 'src/queries/set-machine-assigned-employees';
import { useProcessStore } from 'src/stores/process.store';
import { useUserStore } from 'src/stores/user.store';
import { computed, ref, watch } from 'vue';

type EmployeeSelectorProps = {
  employees: Employee[];
  disable?: boolean;
};

const props = defineProps<EmployeeSelectorProps>();

const quasar = useQuasar();
const userStore = useUserStore();
const processStore = useProcessStore();

const { isLoadingSetMachineAssignedEmployees, setMachineAssignedEmployees } =
  useSetMachineAssignedEmployees();

const { createSnapshot, isCreatingSnapshot } = useCreateSnapshot();

const showDialog = ref(false);
const searchText = ref('');
const temporalSelectedEmployeesId = ref<string[]>([]);

const selectedEmployeesId = computed<string[]>(() => {
  return processStore.selectedMachineLoadedData?.selectedEmployeesId ?? [];
});

const filteredEmployees = computed(() => {
  const text = searchText.value.trim().toLowerCase();

  if (!text) return props.employees;

  return props.employees.filter((employee) => employee.name.toLowerCase().includes(text));
});

const isLoading = computed(() => {
  return isLoadingSetMachineAssignedEmployees.value || isCreatingSnapshot.value;
});

const handleConfirmSelection = async () => {
  if (props.disable) return;

  const selectedIds = [...temporalSelectedEmployeesId.value];

  if (selectedIds.length === 0) {
    quasar.notify({
      type: 'negative',
      message: 'Seleccione al menos un empleado.',
    });

    return;
  }

  processStore.setSelectedMachineEmployees(selectedIds);

  if (!processStore.selectedMachine?.id) {
    quasar.notify({
      type: 'positive',
      message: 'Empleados seleccionados. Se guardarán al iniciar la producción.',
    });

    showDialog.value = false;
    return;
  }

  try {
    await setMachineAssignedEmployees({
      machineId: processStore.selectedMachine.id,
      employeesIds: selectedIds.map((id) => Number(id)),
      assignedBy: userStore.username || 'unknown',
    });

    await createSnapshot('employees-assigned');

    quasar.notify({
      type: 'positive',
      message: 'Empleados asignados correctamente.',
    });

    showDialog.value = false;
  } catch (error) {
    console.error(error);

    quasar.notify({
      type: 'negative',
      message: 'No se pudo guardar la asignación de empleados. Revisá el backend o la consola.',
    });
  }
};

watch(showDialog, (value) => {
  if (value) {
    temporalSelectedEmployeesId.value = [...selectedEmployeesId.value];
  }
});
</script>