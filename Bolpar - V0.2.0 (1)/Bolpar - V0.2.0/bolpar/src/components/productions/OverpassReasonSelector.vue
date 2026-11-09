<template>
  <div>
    <q-btn
      flat
      dense
      rounded
      no-caps
      icon-right="keyboard_arrow_down"
      :label="modelValue ?? 'Seleccionar'"
      class="q-pl-sm"
      :class="modelValue ? 'text-weight-regular' : 'bg-grey-3 text-grey-9'"
      style="min-width: 120px"
      @click="showDialog = true"
    />

    <q-dialog v-model="showDialog" persistent>
      <q-card>
        <q-card-section>
          <div class="text-body1 text-weight-bold q-mb-sm">Seleccionar motivo</div>
          <q-input
            dense
            outlined
            v-model="searchText"
            type="text"
            label="Buscar o especificar otro motivo"
            style="min-width: 360px"
          >
            <template #append v-if="searchText">
              <q-btn
                no-caps
                flat
                color="primary"
                style="margin-right: -10px"
                label="Confirmar este motivo"
                @click="handleConfirmSelection(searchText)"
              />
            </template>
          </q-input>
        </q-card-section>
        <q-separator />
        <q-card-section class="column no-wrap scroll gap-md bg-grey-1" style="height: 50vh">
          <div
            class="column gap-md"
            v-for="category of overpassReasonCategories"
            :key="category.title"
          >
            <div
              v-if="category.items.some((i) => i.toLowerCase().includes(searchText.toLowerCase()))"
              class="text-weight-bold"
            >
              {{ category.title }}
            </div>
            <div class="column gap-sm" v-if="showDialog">
              <q-checkbox
                v-for="item of category.items.filter((i) =>
                  i.toLowerCase().includes(searchText.toLowerCase()),
                )"
                :key="item"
                class="full-width"
                :model-value="selectedItem === item"
                :label="item"
                @click="selectedItem = item"
              />
            </div>
          </div>
        </q-card-section>
        <q-separator />
        <q-card-actions align="between">
          <q-btn flat no-caps label="Cerrar" @click="showDialog = false" />
          <q-btn
            :disable="!selectedItem"
            unelevated
            no-caps
            color="primary"
            label="Confirmar"
            @click="handlePressConfirmSelection"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

type OverpassReasonSelectorProps = {
  modelValue: string | undefined;
};

const props = defineProps<OverpassReasonSelectorProps>();

type OverpassReasonSelectorEmits = {
  (e: 'update:modelValue', value: string): void;
};

const emit = defineEmits<OverpassReasonSelectorEmits>();

const showDialog = ref(false);
const searchText = ref('');
const selectedItem = ref(props.modelValue ?? '');

watch(showDialog, () => {
  searchText.value = '';
  selectedItem.value = '';
  selectedItem.value = props.modelValue ?? '';
});

const overpassReasonCategories = [
  {
    title: 'Justificaciones de Bobinas de Papel',
    items: [
      'Ajuste de máquina complejo que aumenta la merma',
      'Bobinas defectuosas o deformadas (lomo, humedad,arrugas)',
      'Roturas de papel durante el proceso',
      'Pérdidas por empalmes continuos',
      'Errores de operación (cortes mal hechos, arranques y paradas constantes)',
    ],
  },
  {
    title: 'Justificaciones de Bobinas de tintas',
    items: [
      'Mal ajuste de viscosidad o mezcla, generando sobreconsumo',
      'Fugas o derrames en máquinas, bombas o tinteros',
      'Corregir tonalidades durante la corrida, requiriendo mayor carga',
    ],
  },
  {
    title: 'Justificaciones de Bobinas de adhesivos',
    items: [
      'Limpieza y purga de líneas, perdiendo adhesivo en el proceso',
      'Desperdicio por obstrucciones o fallas en dosificadores',
      'Absorción mayor del adhesivo por cambio en el papel o sustrato',
    ],
  },
];

const handleConfirmSelection = (reason: string) => {
  emit('update:modelValue', reason);
  showDialog.value = false;
};

const handlePressConfirmSelection = () => {
  handleConfirmSelection(selectedItem.value);
};
</script>
