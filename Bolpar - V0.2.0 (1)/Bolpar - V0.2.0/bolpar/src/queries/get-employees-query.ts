import { useQuery } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { computed } from 'vue';

export type Employee = {
  id: number;
  zoho_id: string;
  name: string;
  numero_documento: string;
  email: string;
  secondary_email: unknown;
  movil: string;
  fecha_nacimiento: string;
  ciudad_nacimiento: string;
  estado_civil: string;
  grupo_sanguineo: string;
  alergico_a: string;
  direccion: string;
  ciudad: string;
  barrio: string;
  latitud: unknown;
  longitud: unknown;
  sector: string;
  rol: string;
  turno: unknown;
  salario: string;
  acceso_sistema: unknown;
  trasladar_a: string;
  maquina_name: unknown;
  maquina_zoho_id: unknown;
  owner_id: string;
  owner_name: string;
  owner_email: string;
  created_time_zoho: string;
  modified_time_zoho: string;
  last_activity_time: string;
  forms_url: string;
  actualizar: boolean;
  created_at: string;
  updated_at: string;
};

export const useGetEmployees = () => {
  const handleGetEmployees = async () => {
    const response = await api.get<Employee[]>('inventario/funcionarios/');
    return response.data;
  };

  const { data, isLoading, error, isError, refetch } = useQuery<Employee[], AxiosError>({
    queryKey: ['employees'],
    queryFn: handleGetEmployees,
  });

  const getEmployeesByMachineName = (machineName: string) => {
    return data.value?.filter((e) => e.maquina_name === machineName) ?? [];
  };

  return {
    employees: computed(() => data.value ?? []),
    employeesError: computed(() => error.value?.response?.data),
    isGettingEmployees: isLoading,
    isGettingEmployeesError: isError,
    refetchEmployees: refetch,
    getEmployeesByMachineName,
  };
};
