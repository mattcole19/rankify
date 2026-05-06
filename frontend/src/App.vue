<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createClient, type AuthChangeEvent, type Session } from '@supabase/supabase-js'

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
const initialAdminSecret = import.meta.env.VITE_ADMIN_SECRET ?? ''
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const supabaseClient =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null
const anonStorageKey = 'rankify_anon_id'
const submittedCategoriesStorageKey = 'rankify_submitted_categories'
const isAdminView = window.location.pathname.startsWith('/admin')
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const categories = ref<CategorySummary[]>([])
const selectedSlug = ref<string | null>(null)
const category = ref<CategoryDetail | null>(null)
const rankingItems = ref<CategoryItem[]>([])
const communityRanking = ref<CommunityRanking | null>(null)
const draggedIndex = ref<number | null>(null)
const adminSecret = ref(initialAdminSecret)
const adminError = ref<string | null>(null)
const adminMessage = ref<string | null>(null)
const creatingCategory = ref(false)
const addingItems = ref(false)
const newCategoryName = ref('')
const newCategorySlug = ref('')
const newCategoryDescription = ref('')
const itemCategoryId = ref<number | null>(null)
const newItemsText = ref('')
const adminSession = ref<Session | null>(null)
const adminAuthLoading = ref(false)
const anonId = ref<string>('')
const submittedCategoryIds = ref<Set<number>>(new Set())

const hasSubmittedCurrentCategory = computed(() => {
  const categoryId = category.value?.id
  if (!categoryId) {
    return false
  }
  return submittedCategoryIds.value.has(categoryId)
})
const canSubmit = computed(
  () => category.value !== null && rankingItems.value.length > 1 && !hasSubmittedCurrentCategory.value,
)
const submitButtonLabel = computed(() => {
  if (submitting.value) {
    return 'Submitting…'
  }
  if (hasSubmittedCurrentCategory.value) {
    return 'Already Submitted'
  }
  return 'Submit Ranking'
})
const hasAdminToken = computed(() => Boolean(adminSession.value?.access_token))
const hasAdminAccess = computed(
  () => hasAdminToken.value || adminSecret.value.trim().length > 0,
)

const shuffleItems = (items: CategoryItem[]) => {
  const shuffled = [...items]
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const current = shuffled[i]
    const swapTarget = shuffled[j]
    if (!current || !swapTarget) {
      continue
    }
    shuffled[i] = swapTarget
    shuffled[j] = current
  }
  return shuffled
}

const formatApiError = (payload: unknown, fallback: string): string => {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail?: unknown }).detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (typeof entry === 'string') {
            return entry
          }
          if (entry && typeof entry === 'object' && 'msg' in entry) {
            const msg = (entry as { msg?: unknown }).msg
            return typeof msg === 'string' ? msg : JSON.stringify(entry)
          }
          return JSON.stringify(entry)
        })
        .join(', ')
    }
    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail)
    }
  }
  return fallback
}

const createAnonId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `anon-${Math.random().toString(36).slice(2)}-${Date.now()}`
}

const getLocalStorage = (): Storage | null => {
  if (typeof window === 'undefined') {
    return null
  }
  const storage = window.localStorage
  if (!storage) {
    return null
  }
  if (typeof storage.getItem !== 'function' || typeof storage.setItem !== 'function') {
    return null
  }
  return storage
}

const getOrCreateAnonId = (): string => {
  const storage = getLocalStorage()
  if (!storage) {
    return createAnonId()
  }
  const existing = storage.getItem(anonStorageKey)
  if (existing) {
    return existing
  }
  const generated = createAnonId()
  storage.setItem(anonStorageKey, generated)
  return generated
}

const loadSubmittedCategoryIds = () => {
  const storage = getLocalStorage()
  if (!storage) {
    submittedCategoryIds.value = new Set()
    return
  }
  const raw = storage.getItem(submittedCategoriesStorageKey)
  if (!raw) {
    submittedCategoryIds.value = new Set()
    return
  }

  try {
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) {
      submittedCategoryIds.value = new Set()
      return
    }
    const ids = parsed
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0)
    submittedCategoryIds.value = new Set(ids)
  } catch {
    submittedCategoryIds.value = new Set()
  }
}

const markCategorySubmitted = (categoryId: number) => {
  submittedCategoryIds.value = new Set([...submittedCategoryIds.value, categoryId])
  const storage = getLocalStorage()
  if (!storage) {
    return
  }
  storage.setItem(submittedCategoriesStorageKey, JSON.stringify([...submittedCategoryIds.value]))
}

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

    const firstCategory = payload[0]
    if (firstCategory && itemCategoryId.value === null) {
      itemCategoryId.value = firstCategory.id
    }
    if (firstCategory) {
      await selectCategory(firstCategory.slug)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const initializeAdminSession = async () => {
  if (!supabaseClient || !isAdminView) {
    return
  }
  adminAuthLoading.value = true
  const {
    data: { session },
  } = await supabaseClient.auth.getSession()
  adminSession.value = session
  supabaseClient.auth.onAuthStateChange((_event: AuthChangeEvent, sessionState: Session | null) => {
    adminSession.value = sessionState
  })
  adminAuthLoading.value = false
}

const signInWithGoogle = async () => {
  if (!supabaseClient) {
    adminError.value = 'Supabase auth is not configured in frontend environment'
    return
  }
  adminError.value = null
  await supabaseClient.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/admin`,
    },
  })
}

const signOutAdmin = async () => {
  if (!supabaseClient) {
    return
  }
  await supabaseClient.auth.signOut()
}

const getAdminHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = adminSession.value?.access_token
  if (token) {
    headers.Authorization = `Bearer ${token}`
    return headers
  }

  const secret = adminSecret.value.trim()
  if (secret) {
    headers['X-Admin-Secret'] = secret
    return headers
  }

  throw new Error('Sign in with Google or provide an admin secret')
}

const createCategory = async () => {
  const name = newCategoryName.value.trim()
  const slug = newCategorySlug.value.trim()
  const description = newCategoryDescription.value.trim()
  if (!name || !slug) {
    adminError.value = 'Category name and slug are required'
    return
  }

  creatingCategory.value = true
  adminError.value = null
  adminMessage.value = null
  try {
    const response = await fetch(`${apiBase}/admin/categories`, {
      method: 'POST',
      headers: getAdminHeaders(),
      body: JSON.stringify({
        name,
        slug,
        description: description.length > 0 ? description : null,
      }),
    })

    const payload = (await response.json()) as { id?: number; slug?: string; detail?: unknown }
    if (!response.ok) {
      throw new Error(formatApiError(payload, `Could not create category (${response.status})`))
    }

    adminMessage.value = `Created category: ${payload.slug}`
    newCategoryName.value = ''
    newCategorySlug.value = ''
    newCategoryDescription.value = ''
    await fetchCategories()

    if (payload.slug) {
      await selectCategory(payload.slug)
    }
    if (payload.id) {
      itemCategoryId.value = payload.id
    }
  } catch (err) {
    adminError.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    creatingCategory.value = false
  }
}

const addItemsToCategory = async () => {
  if (!itemCategoryId.value) {
    adminError.value = 'Choose a category first'
    return
  }

  const items = newItemsText.value
    .split(/\n|,/) 
    .map((item) => item.trim())
    .filter((item) => item.length > 0)

  if (items.length === 0) {
    adminError.value = 'Enter at least one item'
    return
  }

  addingItems.value = true
  adminError.value = null
  adminMessage.value = null
  try {
    const response = await fetch(`${apiBase}/admin/categories/${itemCategoryId.value}/items`, {
      method: 'POST',
      headers: getAdminHeaders(),
      body: JSON.stringify({ items }),
    })

    const payload = (await response.json()) as
      | { detail?: unknown }
      | Array<{ id: number; name: string }>
    if (!response.ok) {
      throw new Error(formatApiError(payload, `Could not add items (${response.status})`))
    }

    adminMessage.value = `Added ${items.length} item${items.length === 1 ? '' : 's'}`
    newItemsText.value = ''
    await fetchCategories()

    if (category.value && category.value.id === itemCategoryId.value && selectedSlug.value) {
      await selectCategory(selectedSlug.value)
    }
  } catch (err) {
    adminError.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    addingItems.value = false
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
  const canonicalOrder = [...payload.items].sort((a, b) => a.display_order - b.display_order)
  rankingItems.value = shuffleItems(canonicalOrder)

  if (submittedCategoryIds.value.has(payload.id)) {
    await loadCommunityRanking()
  }
}

const moveItem = (index: number, direction: -1 | 1) => {
  const nextIndex = index + direction
  if (nextIndex < 0 || nextIndex >= rankingItems.value.length) {
    return
  }

  const cloned = [...rankingItems.value]
  const [target] = cloned.splice(index, 1)
  if (!target) {
    return
  }
  cloned.splice(nextIndex, 0, target)
  rankingItems.value = cloned
}

const handleDragStart = (index: number) => {
  draggedIndex.value = index
}

const handleDrop = (targetIndex: number) => {
  const sourceIndex = draggedIndex.value
  draggedIndex.value = null

  if (sourceIndex === null || sourceIndex === targetIndex) {
    return
  }

  const cloned = [...rankingItems.value]
  const [moved] = cloned.splice(sourceIndex, 1)
  if (!moved) {
    return
  }
  cloned.splice(targetIndex, 0, moved)
  rankingItems.value = cloned
}

const handleDragEnd = () => {
  draggedIndex.value = null
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
        anon_id: anonId.value,
      }),
    })

    if (response.status === 409 && category.value) {
      markCategorySubmitted(category.value.id)
      error.value = null
      await loadCommunityRanking()
      return
    }

    if (!response.ok) {
      const payload = await response.json()
      throw new Error(formatApiError(payload, `Could not submit ranking (${response.status})`))
    }

    markCategorySubmitted(category.value.id)
    error.value = null
    await loadCommunityRanking()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  anonId.value = getOrCreateAnonId()
  loadSubmittedCategoryIds()
  await Promise.all([fetchCategories(), initializeAdminSession()])
})
</script>

<template>
  <main class="shell">
    <nav v-if="isAdminView" class="top-nav" aria-label="Primary">
      <a class="nav-link" href="/">Home</a>
    </nav>

    <section class="hero" v-if="!isAdminView">
      <p class="eyebrow">Rankify</p>
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
        <article
          v-for="(item, index) in rankingItems"
          :key="item.id"
          class="rank-item"
          :class="{ dragging: draggedIndex === index }"
          draggable="true"
          @dragstart="handleDragStart(index)"
          @dragover.prevent
          @drop="handleDrop(index)"
          @dragend="handleDragEnd"
        >
          <p class="rank-position">#{{ index + 1 }}</p>
          <p class="rank-name">{{ item.name }}</p>
          <div class="rank-actions">
            <button class="secondary small" :disabled="index === 0" @click="moveItem(index, -1)">
              Up
            </button>
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
          {{ submitButtonLabel }}
        </button>
      </div>

      <p v-if="hasSubmittedCurrentCategory" class="submission-note">
        You already submitted this category.
      </p>
    </section>

    <section class="panel" aria-live="polite" v-if="communityRanking && !isAdminView">
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

    <section class="panel admin-panel" aria-live="polite" v-if="isAdminView">
      <p class="panel-label">admin tools</p>
      <h2>Create Categories and Items</h2>
      <p class="panel-detail">Sign in with Google to manage categories and items.</p>

      <div class="admin-auth-row">
        <button class="cta" type="button" :disabled="adminAuthLoading || hasAdminToken" @click="signInWithGoogle">
          {{ hasAdminToken ? 'Signed in with Google' : 'Sign in with Google' }}
        </button>
        <button class="secondary" type="button" :disabled="!hasAdminToken" @click="signOutAdmin">
          Sign out
        </button>
      </div>

      <p class="panel-detail" v-if="hasAdminToken">Authenticated as {{ adminSession?.user?.email }}</p>
      <p class="panel-detail">Fallback local-only option:</p>

      <label class="field-label" for="admin-secret">Admin Secret</label>
      <input id="admin-secret" v-model="adminSecret" class="text-input" type="password" />

      <div class="admin-grid">
        <article class="admin-card">
          <h3>Create Category</h3>
          <label class="field-label" for="new-category-name">Name</label>
          <input id="new-category-name" v-model="newCategoryName" class="text-input" type="text" />

          <label class="field-label" for="new-category-slug">Slug</label>
          <input id="new-category-slug" v-model="newCategorySlug" class="text-input" type="text" />

          <label class="field-label" for="new-category-description">Description</label>
          <textarea
            id="new-category-description"
            v-model="newCategoryDescription"
            class="text-input"
            rows="3"
          />

          <button class="secondary" :disabled="creatingCategory || !hasAdminAccess" @click="createCategory">
            {{ creatingCategory ? 'Creating…' : 'Create Category' }}
          </button>
        </article>

        <article class="admin-card">
          <h3>Add Items</h3>
          <label class="field-label" for="item-category-select">Category</label>
          <select id="item-category-select" v-model.number="itemCategoryId" class="select">
            <option v-for="entry in categories" :key="entry.id" :value="entry.id">
              {{ entry.name }}
            </option>
          </select>

          <label class="field-label" for="new-items">Items (comma or newline separated)</label>
          <textarea id="new-items" v-model="newItemsText" class="text-input" rows="5" />

          <button class="secondary" :disabled="addingItems || !hasAdminAccess" @click="addItemsToCategory">
            {{ addingItems ? 'Adding…' : 'Add Items' }}
          </button>
        </article>
      </div>

      <p v-if="adminError" class="error">{{ adminError }}</p>
      <p v-if="adminMessage" class="admin-success">{{ adminMessage }}</p>
    </section>
  </main>
</template>
