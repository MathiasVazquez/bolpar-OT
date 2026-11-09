import { useMutation, useQueryClient } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { MACHINE_STATE } from './models/machines.model';
import { useUserStore } from 'src/stores/user.store';

type FinishMachineProductionParams = {
  machineId: number;
  machineData?: object;
};

export const useFinishMachineQuery = () => {
  const queryClient = useQueryClient();
  const userStore = useUserStore();

  const handleFinishMachine = async ({
    machineId,
    machineData,
  }: FinishMachineProductionParams) => {
    await api.patch('inventario/machines/' + machineId + '/', {
      data_json: machineData,
    });

    await api.post('inventario/machine-status-logs/', {
      machine: machineId,
      estado: MACHINE_STATE.Finished,
      fecha_hora: new Date().toISOString(),
      motivo: '',
      performed_by: userStore.username || 'unknown',
    });
  };

  const { mutateAsync, isPending } = useMutation<
    void,
    AxiosError,
    FinishMachineProductionParams
  >({
    mutationFn: handleFinishMachine,

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] === 'orders',
      });
    },
  });

  return {
    finishMachineProduction: mutateAsync,
    isLoadingFinishMachineProduction: isPending,
  };
};