<template>
  <div class="tcm-layout">
    <slot />
  </div>
</template>

<script setup>
// 布局组件，为未来扩展预留
</script>

<style scoped>
.tcm-layout {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
