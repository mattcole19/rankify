<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

type HealthState = 'idle' | 'loading' | 'online' | 'error'

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const status = ref<HealthState>('idle')
const lastChecked = ref<string>('not yet')
const details = ref<string>('Waiting to contact the API…')

const statusCopy = computed(() => {
  switch (status.value) {
    case 'online':
      return 'API is online'
    case 'error':
      return 'Cannot reach API'
    case 'loading':
      return 'Checking API health…'
    default:
      return 'Idle'
  }
})

const fetchHealth = async () => {
  status.value = 'loading'
  details.value = 'Checking…'
  try {
    const response = await fetch(`${apiBase}/health`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    const payload = await response.json()
    status.value = 'online'
    details.value = payload.status ?? 'ok'
  } catch (error) {
    status.value = 'error'
    details.value = error instanceof Error ? error.message : 'Unknown error'
  } finally {
    lastChecked.value = new Date().toLocaleTimeString()
  }
}

onMounted(fetchHealth)
</script>

<template>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Rankify · rank everything</p>
      <h1>Collect ranked opinions without the noise.</h1>
      <p class="lede">
        Drop in, reorder items, and instantly see how your instincts stack up to the community. No
        feeds, no doomscrolling—just structured rankings.
      </p>
      <div class="cta-row">
        <button class="cta" type="button">Coming soon</button>
        <button class="secondary" type="button" @click="fetchHealth">Check API</button>
      </div>
    </section>

    <section class="panel" aria-live="polite">
      <p class="panel-label">local stack</p>
      <h2>{{ statusCopy }}</h2>
      <p class="panel-detail">{{ details }}</p>
      <p class="panel-meta">
        Last checked at <span>{{ lastChecked }}</span> against
        <code>{{ apiBase }}/health</code>
      </p>
    </section>
  </main>
</template>
