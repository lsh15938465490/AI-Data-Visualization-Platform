<template>
  <p class="thinking" role="status">
    think<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
  </p>
</template>

<style scoped>
.thinking {
  margin: 4px 0 10px;
  color: #64748b;
  font-size: 13px;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  letter-spacing: 0.04em;
}
.dot {
  display: inline-block;
  animation: think-bounce 1.1s ease-in-out infinite;
  opacity: 0.25;
}
.dot:nth-child(1) {
  animation-delay: 0s;
}
.dot:nth-child(2) {
  animation-delay: 0.18s;
}
.dot:nth-child(3) {
  animation-delay: 0.36s;
}
@keyframes think-bounce {
  0%,
  80%,
  100% {
    opacity: 0.2;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}
</style>
