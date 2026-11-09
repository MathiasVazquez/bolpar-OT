export const formatMoney = (money?: number | string) => {
  const toFormatedString = () => {
    if (!money && money !== 0) return '';
    // Remove all non-numeric characters form money (keep ',')
    const _money = money.toString().replace(/[^0-9,.]/g, '');
    const [integer, decimal] = _money.split('.');
    const integerPart = integer?.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    return `${integerPart}${decimal ? `,${decimal}` : ''}`.replace(',00', '');
  };

  const toNumber = () => {
    if (!money) return 0;
    const _money = money.toString().replace(/[^0-9,.]/g, '');
    const [integer, decimal] = _money.split(',');
    return Number(`${integer?.replaceAll('.', '')}${decimal ? `.${decimal}` : ''}`);
  };

  return {
    toFormatedString,
    toNumber,
  };
};
