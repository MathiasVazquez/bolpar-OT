import { useMutation } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { useUserStore } from 'src/stores/user.store';

type CreateMachineStatusParams = {
  machineId: number;
  machineStatus: string;
  reason?: string | undefined;
};

export const useCreateMachineStatus = () => {
  const userStore = useUserStore();

  const handlePreStartMachine = async ({
    machineId,
    machineStatus,
    reason,
  }: CreateMachineStatusParams) => {
    await api.post('inventario/machine-status-logs/', {
      machine: machineId,
      estado: machineStatus,
      fecha_hora: new Date().toISOString(),
      motivo: reason ?? '',
      performed_by: userStore.username || 'unknown',
    });
  };

  const { mutateAsync, isPending } = useMutation<
    void,
    AxiosError,
    CreateMachineStatusParams
  >({
    mutationFn: handlePreStartMachine,
  });

  return {
    createMachineStatus: mutateAsync,
    isLoadingCreateMachineStatus: isPending,
  };
};