export const MACHINE_STATE = {
  Started: 'STARTED',
  Produccion: 'PRODUCCION',
  Paused: 'PAUSED',
  Finished: 'FINISHED',
};

export type MachineName = string;

export type MachineProcessStatus = {
  id: number;
  machine: number;
  estado: string;
  fecha_hora: string;
  motivo: string;
};

export type MachineProcess = {
  id: number;
  sales_order: number;
  nombre: MachineName;
  numero: number;
  data_json: object;
  status_logs: MachineProcessStatus[];
};