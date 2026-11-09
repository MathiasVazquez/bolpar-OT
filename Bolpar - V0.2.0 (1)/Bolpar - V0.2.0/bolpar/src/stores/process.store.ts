import { defineStore, acceptHMRUpdate } from 'pinia';
import { type MachineProcess } from 'src/queries/models/machines.model';
import type { Order } from 'src/queries/models/order.model';
import { computed, ref } from 'vue';

export type MachineLoadedData = {
  selectedEmployeesId: string[];
};

export type MachineInputRow = {
  article: string;
  batch: string;
  initialWeight: number;
  finalWeight: number;
  consumed: number;
};

export const useProcessStore = defineStore('process', () => {
  const selectedOrder = ref<Order | null>(null);
  const machines = ref<MachineProcess[]>([]);
  const selectedMachineIndex = ref<number>(0);
  const machinesLoadedData = ref<MachineLoadedData[]>([]);
  const machinesInputRows = ref<MachineInputRow[][]>([]);
  const finishMachineInfoOptionsInputValues = ref<Record<string, string>[]>([]);
  const overpassReasons = ref<Record<string, string>>({});

  const getMachineByIndex = (index: number) => machines.value[index];

  const getMachineStatusByIndex = (index: number) => {
    const sortedLogs =
      machines.value[index]?.status_logs.toSorted(
        (a, b) => new Date(b.fecha_hora).getTime() - new Date(a.fecha_hora).getTime(),
      ) ?? [];

    return sortedLogs[0];
  };

  const getMachinePlanificationByIndex = (index: number) => {
    return selectedOrder.value?.planificacion_produccion[index];
  };

  const selectedMachine = computed(() => getMachineByIndex(selectedMachineIndex.value ?? 0));

  const selectedMachineStatus = computed(() => getMachineStatusByIndex(selectedMachineIndex.value));

  const selectedMachinePlanification = computed(() =>
    getMachinePlanificationByIndex(selectedMachineIndex.value ?? 0),
  );

  const selectedMachineLoadedData = computed(
    () => machinesLoadedData.value[selectedMachineIndex.value],
  );

  const selectedMachineInputRows = computed(
    () => machinesInputRows.value[selectedMachineIndex.value] ?? [],
  );

  const addSelectedMachineInputRowByIndex = (index: number, row: MachineInputRow) => {
    machinesInputRows.value[index] = [...(machinesInputRows.value[index] ?? []), row];
  };

  const selectOrder = (order: Order, orderMachines: MachineProcess[]) => {
    const currentSelectedMachineId = selectedMachine.value?.id;

    selectedOrder.value = order;
    machines.value = orderMachines;

    const nextSelectedIndex = orderMachines.findIndex(
      (machine) => machine.id === currentSelectedMachineId,
    );

    selectedMachineIndex.value = nextSelectedIndex >= 0 ? nextSelectedIndex : 0;

    const totalProcessSteps = Math.max(
      order.planificacion_produccion?.length ?? 0,
      orderMachines.length,
      1,
    );

    Array.from({ length: totalProcessSteps }).forEach((_, index) => {
      const machineDataJson = orderMachines[index]?.data_json as
        | { selectedEmployeesId?: Array<string | number> }
        | null
        | undefined;

      if (!machinesLoadedData.value[index]) {
        machinesLoadedData.value[index] = {
          selectedEmployeesId: (machineDataJson?.selectedEmployeesId ?? []).map(String),
        };
      }

      if (!machinesInputRows.value[index]) {
        machinesInputRows.value[index] = [];
      }

      if (!finishMachineInfoOptionsInputValues.value[index]) {
        finishMachineInfoOptionsInputValues.value[index] = {};
      }
    });
  };

  return {
    selectedOrder: computed(() => selectedOrder.value),
    machines,
    overpassReasons,
    selectedMachine,
    selectedMachineStatus,
    selectedMachineIndex,
    selectedMachinePlanification,
    selectedMachineLoadedData,
    selectedMachineInputRows,

    selectedMachineFinishInputValues: computed(
      () => finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0] ?? {},
    ),

    setSelectedMachineOverpassReasons: (data: Record<string, string>) => {
      overpassReasons.value = data;
    },

    setSelectedMachineInputRows: (rows: MachineInputRow[]) => {
      machinesInputRows.value[selectedMachineIndex.value] = rows;
    },

    getSelectedMachineFinishInputValues: (field: string) => {
      if (!finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0]) {
        finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0] = {};
      }

      return finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0]![field];
    },

    setSelectedMachineFinishInputValues: (field: string, value: string) => {
      if (!finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0]) {
        finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0] = {};
      }

      finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0]![field] = value;
    },

    replaceSelectedMachineFinishInputValues: (values: Record<string, string>) => {
      finishMachineInfoOptionsInputValues.value[selectedMachineIndex.value ?? 0] = values;
    },

    getMachinePlanificationByIndex,
    getMachineStatusByIndex,
    getMachineByIndex,

    selectMachine: (index: number) => {
      selectedMachineIndex.value = index;
    },

    selectOrder,

    removeSelectedOrder: () => {
      selectedOrder.value = null;
      machines.value = [];
      selectedMachineIndex.value = 0;
      machinesLoadedData.value = [];
      machinesInputRows.value = [];
      finishMachineInfoOptionsInputValues.value = [];
      overpassReasons.value = {};
    },

    setSelectedMachineEmployees: (employeesId: string[]) => {
      if (!machinesLoadedData.value[selectedMachineIndex.value]) {
        machinesLoadedData.value[selectedMachineIndex.value] = {
          selectedEmployeesId: [],
        };
      }

      machinesLoadedData.value[selectedMachineIndex.value] = {
        ...machinesLoadedData.value[selectedMachineIndex.value],
        selectedEmployeesId: employeesId,
      };

      const machine = machines.value[selectedMachineIndex.value];

      if (machine) {
        machine.data_json = {
          ...(machine.data_json ?? {}),
          selectedEmployeesId: employeesId,
        };
      }
    },

    setSelectedMachineLoadedData: (data: MachineLoadedData) => {
      machinesLoadedData.value[selectedMachineIndex.value] = data;
    },

    addSelectedMachineInputRow: (row: MachineInputRow) => {
      addSelectedMachineInputRowByIndex(selectedMachineIndex.value, row);
    },

    addSelectedMachineInputRowByIndex,

    selectedMachineStatusIsOneOf: (status: string[]) =>
      status.includes(selectedMachineStatus.value?.estado ?? ''),
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useProcessStore, import.meta.hot));
}