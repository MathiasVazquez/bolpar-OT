import { useQuery } from '@tanstack/vue-query';
import { computed } from 'vue';
import { api } from 'src/boot/axios';

export type CompletedOrder = {
  id: number;
  so_number: string;
  subject: string;
  status: string;
  machines_count: number;
  plan_count: number;
  finished_at: string;
};

export function useGetCompletedOrders() {
  const { data, isLoading, refetch } = useQuery<CompletedOrder[]>({
    queryKey: ['completed-orders'],
    queryFn: async () => {
      const response = await api.get<CompletedOrder[]>(
        'inventario/orders/completadas-100/',
      );

      return response.data;
    },
  });

  return {
    completedOrders: computed(() => data.value ?? []),
    isGettingCompletedOrders: isLoading,
    refetchCompletedOrders: refetch,
  };
}

export async function downloadCompletedOrderExcel(order: CompletedOrder) {
  const response = await api.get(
    `inventario/orders/${order.id}/export-completo-final/`,
    {
      responseType: 'blob',
    },
  );

  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = `OT_${order.so_number}_registro_completo.xlsx`;

  document.body.appendChild(link);
  link.click();
  link.remove();

  window.URL.revokeObjectURL(url);
}