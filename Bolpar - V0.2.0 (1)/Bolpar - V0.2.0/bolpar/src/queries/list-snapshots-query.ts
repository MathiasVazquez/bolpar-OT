import { useQuery } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { type MachineSnapShot } from './create-snapshot-query';
import { computed, toValue, type MaybeRefOrGetter } from 'vue';

export const useListSnapshots = (machineId: MaybeRefOrGetter<string | number | undefined>) => {
  const machineIdValue = computed(() => toValue(machineId));

  const handleGetSnapshots = async () => {
    if (!machineIdValue.value) return [];

    const response = await api.get(`inventario/machines/${machineIdValue.value}/snapshots/`);

    return response.data.results.map((s: object) => Reflect.get(s, 'data_json'));
  };

  const { data, isLoading, refetch } = useQuery<unknown, AxiosError, MachineSnapShot[]>({
    queryKey: ['snapshots', machineIdValue],
    queryFn: handleGetSnapshots,
    enabled: computed(() => !!machineIdValue.value),
  });

  const lastSnapshot = computed(
    () => data.value?.toSorted((a, b) => b.datetime - a.datetime)[0] ?? null,
  );

  const getSumOfFinalComsumption = (name: string) => {
    return (
      data.value
        ?.filter((s) => s.actionType === 'final-consumption-added')
        .reduce((acc, s) => acc + Number(s.data.finalConsumption[name]), 0) ?? 0
    );
  };

  return {
    lastSnapshot,
    snapshots: computed(() => data.value ?? []),
    isGettingSnapshots: isLoading,
    refetchSnapshots: refetch,
    getSumOfFinalComsumption,
  };
};