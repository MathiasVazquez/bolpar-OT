import { useMutation } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';

type SetMachineAssignedEmployeesParams = {
  machineId: number;
  employeesIds: number[] | string[];
  assignedBy: string;
};

export const useSetMachineAssignedEmployees = () => {
  const handleSetMachineAssignedEmployees = async ({
    employeesIds,
    assignedBy,
    machineId,
  }: SetMachineAssignedEmployeesParams) => {
    await api.post(`inventario/machines/${machineId}/set-employees/`, {
      employee_ids: employeesIds,
      assigned_by: assignedBy,
      mode: 'replace',
    });
  };

  const { mutateAsync, isPending } = useMutation<
    void,
    AxiosError,
    SetMachineAssignedEmployeesParams
  >({
    mutationFn: handleSetMachineAssignedEmployees,
  });

  return {
    setMachineAssignedEmployees: mutateAsync,
    isLoadingSetMachineAssignedEmployees: isPending,
  };
};
