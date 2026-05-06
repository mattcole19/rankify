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

app.mount('#app')
