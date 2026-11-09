export interface Order {
  id: number;
  items: Item[];
  planificacion_produccion: ProductionPlanification[];
  consumo_insumos: ConsumoInsumo[];
  tag: string;
  so_number: number;
  subject: string;
  ajuste: string;
  ancho_util: string;
  cantidad_kilogramos: string;
  cantidad_metros: string;
  cilindro: string;
  shipping_city: string;
  billing_city: string;
  shipping_code: string;
  billing_code: string;
  shipping_street: string;
  billing_street: string;
  shipping_state: string;
  billing_state: string;
  sales_commission: string;
  created_by: string;
  description: string;
  discount: string;
  distancia_tacas: string;
  status: string;
  due_date: string;
  fondo_util: string;
  fuerte_util: string;
  tax: string;
  excise_duty: string;
  largo_util: string;
  modified_by: string;
  currency: string;
  customer_no: string;
  account_name: string;
  deal_name: string;
  contact_name: string;
  quote_name: string;
  purchase_order: string;
  shipping_country: string;
  billing_country: string;
  pending: null;
  owner: string;
  exchange_rate: string;
  campo_de_agregacion_1: null;
  sub_total: string;
  grand_total: string;
  total1: null;
  terms_and_conditions: string;
  
    machine_flow_status?: 'pending' | 'finished' | 'hidden';
  authorized_machine_index?: number;
}

export interface Item {
  quantity: string;
  created_by: string;
  description: string;
  discount: string;
  estado_op: string;
  tax: null;
  product_name: string;
  list_price: string;
}

export interface ProductionPlanification {
  cant: string;
  created_by: string;
  fecha: string;
  linea: string;
  linea_new: string;
  observacion: string;
  producto: string;
  producto_medio: string;

  // Se calcula en la app.
  // Es el producto_medio generado por la máquina anterior.
  producto_medio_anterior?: string;
}

export interface ConsumoInsumo {
  cantidad: number;
  created_by: string;
  insumo: string;
  linea: string;
  lote: string;
  unidad: string;
}
