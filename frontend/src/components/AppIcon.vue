<script setup>
defineProps({ name: { type: String, default: 'grid' } });
const paths = {
  grid: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  practice: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h4',
  plan: 'M5 5h14v15H5zM8 3v4M16 3v4M8 11h8M8 15h5',
  report: 'M5 20V10h3v10M11 20V4h3v16M17 20v-7h3v7',
  star: 'm12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.8L6 20l1-6.1-4.4-4.3 6.1-.9z',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M4 12h2M18 12h2M12 4v2M12 18v2',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8M5 21a7 7 0 0 1 14 0',
  briefcase: 'M9 6V4h6v2M4 7h16v12H4zM4 11c5 2 11 2 16 0M11 12h2',
  logout: 'M10 5H5v14h5M14 8l4 4-4 4M9 12h9',
  upload: 'M12 16V4m0 0L7 9m5-5 5 5M5 17v3h14v-3',
  arrow: 'm9 5 7 7-7 7',
  back: 'm15 5-7 7 7 7',
  check: 'm5 12 4 4L19 6',
  clock: 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16m0 4v5l3 2',
  download: 'M12 4v11m0 0-4-4m4 4 4-4M5 19h14',
  share: 'M8 12l8-5M8 12l8 5M6 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6M18 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4M18 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4',
  exam: 'M6 3h12v18H6zM9 7h6M9 11h6M9 15h4',
  chat: 'M4 5h16v11H9l-5 4zM8 9h8M8 12h5',
  users: 'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6M3 20a6 6 0 0 1 12 0M16 11a3 3 0 1 0 0-6M16 14a6 6 0 0 1 5 6',
  bolt: 'm13 2-8 12h6l-1 8 8-12h-6z',
  presentation: 'M4 4h16v12H4zM8 20l4-4 4 4M8 11l3-3 2 2 3-3',
  compass: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18m3 6-2 5-5 2 2-5z'
};
</script>

<template><svg viewBox="0 0 24 24" aria-hidden="true"><path :d="paths[name] || paths.grid" /></svg></template>
