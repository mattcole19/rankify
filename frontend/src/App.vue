<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

type CategorySummary = {
  id: number
  slug: string
  name: string
  item_count: number
}

type CategoryItem = {
  id: number
  name: string
  display_order: number
}

type CategoryDetail = {
  id: number
  slug: string
  name: string
  description: string | null
  submission_count: number
  items: CategoryItem[]
}

type CommunityItem = {
  item_id: number
  item_name: string
  average_rank: number | null
  vote_count: number
}

type CommunityRanking = {
  category_id: number
  category_slug: string
  total_submissions: number
  items: CommunityItem[]
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const categories = ref<CategorySummary[]>([])
const selectedSlug = ref<string | null>(null)
const category = ref<CategoryDetail | null>(null)
const rankingItems = ref<CategoryItem[]>([])
const communityRanking = ref<CommunityRanking | null>(null)

const canSubmit = computed(() => category.value !== null && rankingItems.value.length > 1)

const fetchCategories = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`${apiBase}/categories`)
    if (!response.ok) {
      throw new Error(`Unable to load categories (${response.status})`)
    }
    const payload = (await response.json()) as CategorySummary[]
    categories.value = payload

    if (payload.length > 0) {
      await selectCategory(payload[0].slug)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const selectCategory = async (slug: string) => {
  selectedSlug.value = slug
  communityRanking.value = null
  error.value = null

  const response = await fetch(`${apiBase}/categories/${slug}`)
  if (!response.ok) {
    error.value = `Unable to load category (${response.status})`
    return
  }

  const payload = (await response.json()) as CategoryDetail
  category.value = payload
  rankingItems.value = [...payload.items].sort((a, b) => a.display_order - b.display_order)
}

const moveItem = (index: number, direction: -1 | 1) => {
  const nextIndex = index + direction
  if (nextIndex < 0 || nextIndex >= rankingItems.value.length) {
    return
  }

  const cloned = [...rankingItems.value]
  const [target] = cloned.splice(index, 1)
  cloned.splice(nextIndex, 0, target)
  rankingItems.value = cloned
}

const loadCommunityRanking = async () => {
  if (!selectedSlug.value) {
    return
  }
  const response = await fetch(`${apiBase}/categories/${selectedSlug.value}/community-ranking`)
  if (!response.ok) {
    error.value = `Unable to load community ranking (${response.status})`
    return
  }

  communityRanking.value = (await response.json()) as CommunityRanking
}

const submitRanking = async () => {
  if (!category.value) {
    return
  }

  submitting.value = true
  error.value = null
  try {
    const response = await fetch(`${apiBase}/rankings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category_id: category.value.id,
        ordered_item_ids: rankingItems.value.map((item) => item.id),
      }),
    })

    if (!response.ok) {
      throw new Error(`Could not submit ranking (${response.status})`)
    }

    await loadCommunityRanking()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    submitting.value = false
  }
}

onMounted(fetchCategories)
</script>

<template>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">Rankify MVP</p>
      <h1>Rank fast. Compare with everyone.</h1>
      <p class="lede">Choose a category, reorder items, submit, and instantly view the community ranking.</p>

      <label class="field-label" for="category-select">Category</label>
      <select
        id="category-select"
        class="select"
        :disabled="loading || categories.length === 0"
        :value="selectedSlug ?? ''"
        @change="selectCategory(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="entry in categories" :key="entry.slug" :value="entry.slug">
          {{ entry.name }} ({{ entry.item_count }} items)
        </option>
      </select>

      <p v-if="error" class="error">{{ error }}</p>

      <div v-if="rankingItems.length > 0" class="rank-list">
        <article v-for="(item, index) in rankingItems" :key="item.id" class="rank-item">
          <p class="rank-position">#{{ index + 1 }}</p>
          <p class="rank-name">{{ item.name }}</p>
          <div class="rank-actions">
            <button class="secondary small" :disabled="index === 0" @click="moveItem(index, -1)">Up</button>
            <button
              class="secondary small"
              :disabled="index === rankingItems.length - 1"
              @click="moveItem(index, 1)"
            >
              Down
            </button>
          </div>
        </article>
      </div>

      <div class="cta-row">
        <button class="cta" type="button" :disabled="!canSubmit || submitting" @click="submitRanking">
          {{ submitting ? 'Submitting…' : 'Submit Ranking' }}
        </button>
      </div>
    </section>

    <section class="panel" aria-live="polite" v-if="communityRanking">
      <p class="panel-label">community ranking</p>
      <h2>{{ category?.name }}</h2>
      <p class="panel-detail">{{ communityRanking.total_submissions }} total submissions</p>
      <ol class="community-list">
        <li v-for="entry in communityRanking.items" :key="entry.item_id">
          <span>{{ entry.item_name }}</span>
          <span v-if="entry.average_rank">avg #{{ entry.average_rank.toFixed(2) }}</span>
          <span v-else>not ranked yet</span>
        </li>
      </ol>
    </section>
  </main>
</template>
