<script setup lang="ts">
defineProps<{ text: string }>();
</script>

<template>
  <span class="info-tip" tabindex="0" :aria-label="text">
    <span aria-hidden="true">?</span>
    <span class="info-bubble" role="tooltip">{{ text }}</span>
  </span>
</template>
