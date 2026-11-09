const machineContainsName = (name: string) => (value: string) =>
  value.split(' ').some((word) => word.trim().toUpperCase() === name.toUpperCase());

export const finishMachineInfoOptions = [
  {
    isName: machineContainsName('IMPRESORA'),
    fields: [
      {
        value: 'shavingsWaste',
        label: 'Desperdicio de desponche [kg]',
      },
      {
        value: 'registerWaste',
        label: 'Desperdicio de registro [kg]',
      },
      {
        value: 'finalWeightOfThePrintedReel',
        label: 'Peso final de la bobina impresa [kg]',
        representsMidiumProductValue: true,
      },
    ],
  },
  {
    isName: machineContainsName('LINEA'),
    fields: [
      {
        value: 'shavingsWaste',
        label: 'Desperdicio de desponche [kg]',
      },
      {
        value: 'wasteOfJoints',
        label: 'Desperdicio de canutos [kg]',
      },
      {
        value: 'bagWasteKg',
        label: 'Desperdicio de bolsas [kg]',
      },
      {
        value: 'bagWasteUnits',
        label: 'Desperdicio de bolsas [Unidades]',
      },
      {
        value: 'bagsToRepair',
        label: 'Bolsas a reparar',
      },
      {
        value: 'finalQuantityOfBags',
        label: 'Cantidad final bolsas',
        representsMidiumProductValue: true,
      },
    ],
  },
  {
    isName: machineContainsName('TUBERA'),
    fields: [
      {
        value: 'shavingsWaste',
        label: 'Desperdicio de desponche [kg]',
      },
      {
        value: 'wasteOfJoints',
        label: 'Desperdicio de canutos [kg]',
      },
      {
        value: 'wasteOfTubesKg',
        label: 'Desperdicio de tubos [kg]',
      },
      {
        value: 'tubesToRepair',
        label: 'Tubos a reparar',
      },
      {
        value: 'finalQuantityOfTubes',
        label: 'Cantidad final de tubos',
        representsMidiumProductValue: true,
      },
    ],
  },
  {
    isName: machineContainsName('FONDERA'),
    fields: [
      {
        value: 'shavingsWaste',
        label: 'Desperdicio de desponche [kg]',
      },
      {
        value: 'wasteOfJoints',
        label: 'Desperdicio de canutos [kg]',
      },
      {
        value: 'bagWasteKg',
        label: 'Desperdicio de bolsas [kg]',
      },
      {
        value: 'bagWasteUnits',
        label: 'Desperdicio de bolsas [Unidades]',
      },
      {
        value: 'bagsToRepair',
        label: 'Bolsas a reparar',
      },
      {
        value: 'finalQuantityOfBags',
        label: 'Cantidad final bolsas',
        representsMidiumProductValue: true,
      },
    ],
  },
  {
    // isName: (value: string) =>
    //   ['51- LAMINADORA- REFILADORA 1', '52- LAMINADORA- REFILADORA 2'].includes(value),
    isName: machineContainsName('LAMINADORA'),
    fields: [
      {
        value: 'shavingsWaste',
        label: 'Desperdicio de desponche [kg]',
      },
    ],
  },
];
