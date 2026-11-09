import { useMutation } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import {
  useProcessStore,
  type MachineInputRow,
} from 'src/stores/process.store';
import { useUserStore } from 'src/stores/user.store';

export const actions = {
  'input-added': 'Artículo utilizado',
  'employees-assigned': 'Empleados asignados',
  'justification-added': 'Justificación añadida',
  'final-consumption-added': 'Consumo final añadido',
} as const;

export type MachineSnapShot = {
  machineId: number;

  data: {
    consumptionInputRows: MachineInputRow[];
    assignedEmployees: string[];
    overpassJustifications: Record<string, string>;
    finalConsumption: Record<string, string>;
  };

  actionType: keyof typeof actions;
  datetime: number;
};

export const useCreateSnapshot = () => {
  const processStore = useProcessStore();
  const userStore = useUserStore();

  const handleCreateSnapshot = async (
    actionType: keyof typeof actions,
  ) => {
    const snapshotData: MachineSnapShot['data'] = {
      consumptionInputRows:
        processStore.selectedMachineInputRows,

      assignedEmployees: (
        processStore.selectedMachineLoadedData
          ?.selectedEmployeesId ?? []
      ).map(String),

      overpassJustifications:
        processStore.overpassReasons,

      finalConsumption:
        processStore.selectedMachineFinishInputValues,
    };

    const requestData = {
      actionType,
      datetime: Date.now(),
      machineId: processStore.selectedMachine!.id,
      data: snapshotData,
    };

    await api.post(
      `inventario/machines/${requestData.machineId}/finalize/`,
      {
        data_json: JSON.parse(
          JSON.stringify(requestData),
        ),

        captured_by:
          userStore.username || 'unknown',

        notes: actions[actionType],
      },
    );
  };

  const { mutateAsync, isPending } = useMutation<
    void,
    AxiosError,
    keyof typeof actions
  >({
    mutationFn: handleCreateSnapshot,
  });

  return {
    createSnapshot: mutateAsync,
    isCreatingSnapshot: isPending,
  };
};