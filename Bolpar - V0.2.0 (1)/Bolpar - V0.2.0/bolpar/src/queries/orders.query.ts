import { useQuery } from '@tanstack/vue-query';
import type { AxiosError } from 'axios';
import { api } from 'src/boot/axios';
import { computed } from 'vue';
import type { Order, ProductionPlanification } from './models/order.model';
import { MACHINE_STATE, type MachineProcess } from './models/machines.model';
import { useUserStore } from 'src/stores/user.store';

type MachineAuthorization = {
  code: string;
  aliases: string[];
};

const normalizeText = (value: string | number | null | undefined) =>
  String(value ?? '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

const machineAuthorizations: MachineAuthorization[] = [
  { code: '11', aliases: ['imp1', 'imp101', 'imp102', 'impresora1', 'impresora 1'] },
  { code: '12', aliases: ['imp2', 'imp201', 'imp202', 'impresora2', 'impresora 2'] },
  { code: '21', aliases: ['tbr1', 'tbr101', 'tbr102', 'tubera1', 'tubera 1'] },
  { code: '22', aliases: ['tbr2', 'tbr201', 'tbr202', 'tubera2', 'tubera 2'] },
  { code: '31', aliases: ['fnd1', 'fnd101', 'fnd102', 'fdra1', 'fdra101', 'fdra102', 'fondera1', 'fondera 1'] },
  { code: '32', aliases: ['fnd2', 'fnd201', 'fnd202', 'fdra2', 'fdra201', 'fdra202', 'fondera2', 'fondera 2'] },
  { code: '43', aliases: ['lin3', 'lin301', 'lin302', 'linea3', 'linea 3'] },
  { code: '44', aliases: ['lin4', 'lin401', 'lin402', 'linea4', 'linea 4'] },
  { code: '51', aliases: ['lam', 'lam101', 'lam102', 'laminadora', 'refilador', 'refiladora'] },
  { code: '61', aliases: ['cot', 'cot101', 'cot102', 'coteadora', 'coteadora1', 'coteadora 1'] },
  { code: '71', aliases: ['rep1', 'rep101', 'rep102', 'reparadas1', 'reparadas 1', 't1', 't2'] },
  { code: '74', aliases: ['rep4', 'rep401', 'rep402', 'reparadas4', 'reparadas 4', 'f1', 'f2', 'l3', 'l4', 'c'] },
  { code: '81', aliases: ['cor', 'cor101', 'cor102', 'cortadora', 'cortadora1', 'cortadora 1'] },
  { code: '91', aliases: ['reb', 'reb101', 'reb102', 'rebobinadora', 'rebobinadora1', 'rebobinadora 1'] },
  { code: '95', aliases: ['com', 'com101', 'com102', 'compresor', 'compresores'] },
];

const getUserMachineCodes = (username?: string, machineTurn?: string) => {
  const values = [username, machineTurn].map(normalizeText).filter(Boolean);

  return machineAuthorizations
    .filter((authorization) =>
      values.some(
        (value) =>
          value.startsWith(authorization.code) ||
          authorization.aliases.some((alias) => value.startsWith(normalizeText(alias))),
      ),
    )
    .map((authorization) => authorization.code);
};

const getMachineCode = (value?: string) => {
  const normalizedValue = normalizeText(value);
  const match = normalizedValue.match(/^(\d+)/);

  return match?.[1] ?? '';
};

const planMatchesMachineCodes = (plan: ProductionPlanification, machineCodes: string[]) => {
  const planCode = getMachineCode(plan.linea_new || plan.linea);

  return machineCodes.includes(planCode);
};

const machineMatchesPlan = (machine: MachineProcess, plan: ProductionPlanification) => {
  const machineCode = getMachineCode(machine.nombre);
  const planCode = getMachineCode(plan.linea_new || plan.linea);

  if (machineCode && planCode) return machineCode === planCode;

  return normalizeText(machine.nombre) === normalizeText(plan.linea_new || plan.linea);
};

const getLastMachineStatus = (machine?: MachineProcess) => {
  return machine?.status_logs?.toSorted(
    (a, b) => new Date(b.fecha_hora).getTime() - new Date(a.fecha_hora).getTime(),
  )[0]?.estado;
};

const hasFinishedPlanMachine = (machines: MachineProcess[], plan?: ProductionPlanification) => {
  if (!plan) return true;

  return machines.some(
    (machine) =>
      machineMatchesPlan(machine, plan) &&
      getLastMachineStatus(machine) === MACHINE_STATE.Finished,
  );
};

const hasCreatedPlanMachine = (machines: MachineProcess[], plan?: ProductionPlanification) => {
  if (!plan) return false;

  return machines.some((machine) => machineMatchesPlan(machine, plan));
};

export function useGetOrders() {
  const userStore = useUserStore();

  const { data, isLoading, error, isError } = useQuery<Order[], AxiosError>({
    queryKey: ['orders', userStore.username, userStore.userAuthorization],
    queryFn: async () => {
      const ordersResponse = await api.get<Order[]>('inventario/orders/');
      const allOrders = ordersResponse.data;

      const userMachineCodes = getUserMachineCodes(
        userStore.username,
        userStore.userAuthorization,
      );

      if (userMachineCodes.length === 0) return [];

      const ordersWithFlow = await Promise.all(
        allOrders.map(async (order): Promise<Order> => {
          const currentPlanIndex = order.planificacion_produccion.findIndex((plan) =>
            planMatchesMachineCodes(plan, userMachineCodes),
          );

          if (currentPlanIndex === -1) {
            return {
              ...order,
              machine_flow_status: 'hidden',
              authorized_machine_index: -1,
            };
          }

          const currentPlanification = order.planificacion_produccion[
            currentPlanIndex
          ] as ProductionPlanification;

          const previousPlanification = order.planificacion_produccion[currentPlanIndex - 1];

          const machinesResponse = await api.get<MachineProcess[]>(
            'inventario/machines/?ot=' + order.id.toString(),
          );

          const machines = machinesResponse.data;

          const previousIsFinished = hasFinishedPlanMachine(machines, previousPlanification);
          const currentIsFinished = hasFinishedPlanMachine(machines, currentPlanification);
          const currentWasCreated = hasCreatedPlanMachine(machines, currentPlanification);

          let machineFlowStatus: 'pending' | 'finished' | 'hidden' = 'hidden';

          if (currentIsFinished) {
            machineFlowStatus = 'finished';
          } else if (previousIsFinished || currentWasCreated) {
            machineFlowStatus = 'pending';
          }

          const currentPlanificationWithPreviousProduct: ProductionPlanification = {
  ...currentPlanification,

  producto_medio_anterior:
    previousPlanification?.producto_medio?.trim() ?? '',
};

return {
  ...order,
  machine_flow_status: machineFlowStatus,
  authorized_machine_index: currentPlanIndex,
  planificacion_produccion: [
    currentPlanificationWithPreviousProduct
  ],
};
        }),
      );

      return ordersWithFlow.filter((order) => order.machine_flow_status !== 'hidden');
    },
  });

  return {
    orders: computed(() => data.value ?? []),
    ordersError: computed(() => error.value?.response?.data),
    isGettingOrders: isLoading,
    isGettingOrdersError: isError,
  };
}