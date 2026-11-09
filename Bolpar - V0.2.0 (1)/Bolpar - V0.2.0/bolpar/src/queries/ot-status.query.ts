import { useQuery } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { computed } from 'vue';
import type { Order } from './models/order.model';

export function useGetOtStatusOrders() {
  const { data, isLoading, error, isError, refetch } = useQuery<Order[], AxiosError>({
    queryKey: ['ot-status-orders'],

    queryFn: async () => {
      const response = await api.get<Order[]>('inventario/orders/');
      return response.data;
    },

    staleTime: 30000,
  });

  const statusOrders = computed(() =>
    [...(data.value ?? [])].sort((a, b) => Number(b.id) - Number(a.id)),
  );

  return {
    statusOrders,
    isGettingStatusOrders: isLoading,
    statusOrdersError: computed(() => error.value?.response?.data),
    isGettingStatusOrdersError: isError,
    refetchStatusOrders: refetch,
  };
}
