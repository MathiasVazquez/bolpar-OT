import { useMutation } from '@tanstack/vue-query';
import { api } from 'src/boot/axios';
import { computed } from 'vue';
import { type MachineProcess } from './models/machines.model';

export const useGetMachinesQuery = () => {
  const handleGetOtMachines = async (otId: number | string | string[]) => {
    const { data } = await api.get<MachineProcess[]>('inventario/machines/?ot=' + otId.toString());
    return data;
  };

  const { mutateAsync, data, isPending } = useMutation({
    mutationFn: handleGetOtMachines,
  });

  return {
    getMachines: mutateAsync,
    machines: computed(() => data.value ?? []),
    isLoadingMachines: isPending,
  };
};
