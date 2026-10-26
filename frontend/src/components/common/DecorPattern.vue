<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'pulse' },
  tone: { type: String, default: 'blue' },
})

const palettes = {
  blue: ['#2563eb', '#22d3ee'],
  teal: ['#0d9488', '#38bdf8'],
  amber: ['#d97706', '#fbbf24'],
  rose: ['#dc2626', '#fb7185'],
  violet: ['#6d28d9', '#38bdf8'],
}

const colors = computed(() => palettes[props.tone] || palettes.blue)
const gradientId = `decor-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
</script>

<template>
  <svg
    class="decor-pattern"
    :class="`is-${variant}`"
    :style="{ color: colors[0] }"
    viewBox="0 0 360 150"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <defs>
      <linearGradient :id="gradientId" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" :stop-color="colors[0]" />
        <stop offset="100%" :stop-color="colors[1]" />
      </linearGradient>
    </defs>

    <g :stroke="`url(#${gradientId})`" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <template v-if="variant === 'pulse'">
        <path class="decor-line" d="M0 92h62l12-11 13 24 17-55 16 73 15-31h68l13-9 12 18 14-26 13 34 12-17h76" />
        <path class="decor-line decor-line-soft" d="M0 116h74l16-8 15 17 18-38 17 50 15-21h205" />
        <circle class="decor-dot" cx="96" cy="105" r="3" />
        <circle class="decor-dot" cx="217" cy="92" r="2.4" />
      </template>

      <template v-else-if="variant === 'cells'">
        <circle cx="44" cy="44" r="24" />
        <circle cx="104" cy="42" r="15" />
        <circle cx="146" cy="82" r="28" />
        <circle cx="212" cy="42" r="20" />
        <circle cx="255" cy="92" r="17" />
        <circle cx="310" cy="48" r="26" />
        <circle cx="66" cy="112" r="13" />
        <circle cx="338" cy="112" r="10" />
        <circle class="decor-fill" cx="181" cy="33" r="5" />
        <circle class="decor-fill" cx="286" cy="118" r="4" />
      </template>

      <template v-else-if="variant === 'cross'">
        <rect x="22" y="22" width="38" height="38" rx="9" />
        <rect x="86" y="58" width="28" height="28" rx="7" />
        <rect x="144" y="18" width="48" height="48" rx="11" />
        <rect x="226" y="50" width="34" height="34" rx="8" />
        <rect x="300" y="20" width="24" height="24" rx="6" />
        <path d="M41 32v18M32 41h18M168 33v18M159 42h18M243 58v18M234 67h18" />
        <path class="decor-line-soft" d="M0 118h360" />
      </template>

      <template v-else>
        <path class="decor-line" d="M0 58c38-34 76-34 114 0s76 34 114 0 76-34 132 0" />
        <path class="decor-line decor-line-soft" d="M0 86c38-34 76-34 114 0s76 34 114 0 76-34 132 0" />
        <path class="decor-line decor-line-soft" d="M0 114c38-34 76-34 114 0s76 34 114 0 76-34 132 0" />
      </template>
    </g>
  </svg>
</template>

<style scoped>
.decor-pattern {
  position: absolute;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.38;
}

.decor-line,
.decor-line-soft,
.decor-dot,
.decor-fill {
  stroke-width: 1.4;
  vector-effect: non-scaling-stroke;
}

.decor-line {
  animation: decor-drift 9s ease-in-out infinite alternate;
}

.decor-line-soft {
  opacity: 0.35;
  animation-duration: 13s;
}

.decor-dot {
  fill: currentColor;
  opacity: 0.45;
  stroke: none;
}

.decor-fill {
  fill: currentColor;
  opacity: 0.22;
  stroke: none;
}

.is-cells,
.is-cross {
  opacity: 0.32;
}

.is-cross rect,
.is-cross path {
  stroke-width: 1.2;
}

@keyframes decor-drift {
  from {
    transform: translateX(-8px);
  }
  to {
    transform: translateX(8px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .decor-line {
    animation: none;
  }
}
</style>
