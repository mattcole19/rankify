import { createApp } from 'vue'
import * as Sentry from '@sentry/vue'
import './style.css'
import App from './App.vue'

const app = createApp(App)

const sentryDsn = import.meta.env.VITE_SENTRY_DSN
const sentryTracesSampleRateRaw = Number(import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? 0)
const sentryTracesSampleRate =
  Number.isFinite(sentryTracesSampleRateRaw) &&
  sentryTracesSampleRateRaw >= 0 &&
  sentryTracesSampleRateRaw <= 1
    ? sentryTracesSampleRateRaw
    : 0

if (sentryDsn) {
  Sentry.init({
    app,
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: sentryTracesSampleRate,
  })
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
const apiTimingEnabled =
  typeof import.meta.env.VITE_OBSERVABILITY_API_TIMINGS === 'string' &&
  ['1', 'true', 'yes', 'on'].includes(import.meta.env.VITE_OBSERVABILITY_API_TIMINGS.toLowerCase())
const slowApiMsRaw = Number(import.meta.env.VITE_OBSERVABILITY_SLOW_API_MS ?? 400)
const slowApiMs = Number.isFinite(slowApiMsRaw) && slowApiMsRaw > 0 ? slowApiMsRaw : 400

if (apiTimingEnabled && typeof window !== 'undefined' && typeof window.fetch === 'function') {
  const originalFetch = window.fetch.bind(window)
  window.fetch = async (...args) => {
    const startedAt = performance.now()
    const url = String(args[0])

    try {
      const response = await originalFetch(...args)
      const durationMs = performance.now() - startedAt
      const isApiCall = apiBaseUrl ? url.startsWith(apiBaseUrl) : url.includes('/categories') || url.includes('/rankings') || url.includes('/admin')

      if (isApiCall) {
        const message = `[api] ${response.status} ${response.url} ${durationMs.toFixed(1)}ms`
        if (durationMs >= slowApiMs) {
          console.warn(message)
        } else {
          console.info(message)
        }
      }

      return response
    } catch (error) {
      const durationMs = performance.now() - startedAt
      const isApiCall = apiBaseUrl ? url.startsWith(apiBaseUrl) : url.includes('/categories') || url.includes('/rankings') || url.includes('/admin')
      if (isApiCall) {
        console.error(`[api] ERROR ${url} ${durationMs.toFixed(1)}ms`, error)
      }
      throw error
    }
  }
}

app.mount('#app')
