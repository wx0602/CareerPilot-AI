<script setup>
defineProps({ name: { type: String, default: 'grid' } });
const paths = {
  grid: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  practice: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h4',
  plan: 'M5 5h14v15H5zM8 3v4M16 3v4M8 11h8M8 15h5',
  report: 'M5 20V10h3v10M11 20V4h3v16M17 20v-7h3v7',
  star: 'm12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.8L6 20l1-6.1-4.4-4.3 6.1-.9z',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 12h2M18 12h2M12 4v2M12 18v2',
  logout: 'M10 5H5v14h5M14 8l4 4-4 4M9 12h9',
  upload: 'M12 16V4m0 0L7 9m5-5 5 5M5 17v3h14v-3',
  arrow: 'm9 5 7 7-7 7',
  back: 'm15 5-7 7 7 7',
  check: 'm5 12 4 4L19 6',
  clock: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16m0 4v5l3 2',
  download: 'M12 4v11m0 0-4-4m4 4 4-4M5 19h14',
  share: 'M8 12l8-5M8 12l8 5M6 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6M18 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4M18 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4'
};
</script>

<template><svg viewBox="0 0 24 24" aria-hidden="true"><path :d="paths[name] || paths.grid" /></svg></template>
