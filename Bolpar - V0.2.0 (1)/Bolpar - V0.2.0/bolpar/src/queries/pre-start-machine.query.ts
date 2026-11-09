import { useMutation } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { MACHINE_STATE } from './models/machines.model';
import { useUserStore } from 'src/stores/user.store';

type CreateMachineProcessResponse = {
  id: number;
  sales_order: number;
  nombre: string;
  numero: number;
  data_json: object;
};

type PreStartMachineParams = {
  orderId: number;
  machineName: string;
  machineNumber: number;
  data?: object;
};

export const usePreStartMachineQuery = () => {
  const userStore = useUserStore();

  const handlePreStartMachine = async ({
    orderId,
    machineName,
    machineNumber,
    data,
  }: PreStartMachineParams) => {
    const { data: createMachineProcessData } =
      await api.post<CreateMachineProcessResponse>(
        'inventario/machines/',
        {
          sales_order: orderId,
          nombre: machineName,
          numero: machineNumber,
          data_json: data ?? {},
        },
      );

    await api.post('inventario/machine-status-logs/', {
      machine: createMachineProcessData.id,
      estado: MACHINE_STATE.Started,
      fecha_hora: new Date().toISOString(),
      motivo: '',
      performed_by: userStore.username || 'unknown',
    });

    return createMachineProcessData;
  };

  const { mutateAsync, isPending } = useMutation<
    CreateMachineProcessResponse,
    AxiosError,
    PreStartMachineParams
  >({
    mutationFn: handlePreStartMachine,
  });

  return {
    preStartMachine: mutateAsync,
    isLoadingPreStartMachine: isPending,
  };
};