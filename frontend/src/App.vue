<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createClient, type AuthChangeEvent, type Session } from '@supabase/supabase-js'
import AdminPanel from './components/AdminPanel.vue'
import CommunityRankingPanel from './components/CommunityRankingPanel.vue'
import PublicRankingSection from './components/PublicRankingSection.vue'

type CategorySummary = {
  id: number
  slug: string
  name: string
  version_number: number
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
  version_number: number
  description: string | null
  submission_count: number
  items: CategoryItem[]
}

type CategoryVersionSummary = {
  category_id: number
  version_number: number
  status: string
  item_count: number
  submission_count: number
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
  category_version_number: number
  total_submissions: number
  items: CommunityItem[]
}

type AdminCategoryListItem = {
  id: number
  slug: string
  name: string
  version_number: number
  status: string
  item_count: number
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const initialAdminSecret = import.meta.env.VITE_ADMIN_SECRET ?? ''
const repeatSubmissionOverride = import.meta.env.VITE_ALLOW_REPEAT_SUBMISSIONS
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const supabaseClient =
  supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null
const anonStorageKey = 'rankify_anon_id'
const submittedCategoriesStorageKey = 'rankify_submitted_categories'
const isAdminView = window.location.pathname.startsWith('/admin')
const allowRepeatSubmissions =
  typeof repeatSubmissionOverride === 'string'
    ? ['1', 'true', 'yes', 'on'].includes(repeatSubmissionOverride.toLowerCase())
    : import.meta.env.MODE === 'development'
const loading = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
const categories = ref<CategorySummary[]>([])
const selectedSlug = ref<string | null>(null)
const category = ref<CategoryDetail | null>(null)
const rankingItems = ref<CategoryItem[]>([])
const communityRanking = ref<CommunityRanking | null>(null)
const categoryVersions = ref<CategoryVersionSummary[]>([])
const selectedCommunityVersion = ref<number | null>(null)
const communityVersionNewItems = ref<Set<string>>(new Set())
const communityVersionDiffSummary = ref<string | null>(null)
const categoryVersionItemsCache = ref<Record<string, string[]>>({})
const draggedIndex = ref<number | null>(null)
const adminSecret = ref(initialAdminSecret)
const adminError = ref<string | null>(null)
const adminMessage = ref<string | null>(null)
const creatingCategory = ref(false)
const loadingAdminCategories = ref(false)
const creatingVersion = ref(false)
const newCategoryName = ref('')
const newCategorySlug = ref('')
const newCategoryDescription = ref('')
const newCategoryItems = ref<string[]>(['', ''])
const adminCategories = ref<AdminCategoryListItem[]>([])
const managedCategorySlug = ref<string>('')
const managedCategoryDetail = ref<CategoryDetail | null>(null)
const managedBaseItems = ref<string[]>([])
const managedEditedItems = ref<string[]>([])
const managedNewItem = ref('')
const adminSession = ref<Session | null>(null)
const adminAuthLoading = ref(false)
const anonId = ref<string>('')
const submittedCategoryIds = ref<Set<number>>(new Set())

const hasSubmittedCurrentCategory = computed(() => {
  if (allowRepeatSubmissions) {
    return false
  }
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
const adminLatestCategories = computed(() => {
  const latestBySlug = new Map<string, AdminCategoryListItem>()
  for (const entry of adminCategories.value) {
    const existing = latestBySlug.get(entry.slug)
    if (!existing || entry.version_number > existing.version_number) {
      latestBySlug.set(entry.slug, entry)
    }
  }
  return [...latestBySlug.values()].sort((a, b) => a.name.localeCompare(b.name))
})
const hasManagedChanges = computed(() => {
  return JSON.stringify(managedBaseItems.value) !== JSON.stringify(managedEditedItems.value)
})

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
  if (allowRepeatSubmissions) {
    submittedCategoryIds.value = new Set()
    return
  }

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
  if (allowRepeatSubmissions) {
    return
  }

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
    if (firstCategory) {
      await selectCategory(firstCategory.slug)
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    loading.value = false
  }
}

const fetchCategoryVersions = async (slug: string) => {
  const response = await fetch(`${apiBase}/categories/${slug}/versions`)
  if (!response.ok) {
    categoryVersions.value = []
    return
  }
  categoryVersions.value = (await response.json()) as CategoryVersionSummary[]
}

const fetchCategoryDetail = async (slug: string, version?: number): Promise<CategoryDetail | null> => {
  const versionQuery = version ? `?version=${version}` : ''
  const response = await fetch(`${apiBase}/categories/${slug}${versionQuery}`)
  if (!response.ok) {
    return null
  }
  return (await response.json()) as CategoryDetail
}

const getCategoryItemsForVersion = async (slug: string, version: number): Promise<string[]> => {
  const cacheKey = `${slug}:${version}`
  const cached = categoryVersionItemsCache.value[cacheKey]
  if (cached) {
    return cached
  }
  const detail = await fetchCategoryDetail(slug, version)
  const itemNames = detail ? detail.items.map((item) => item.name) : []
  categoryVersionItemsCache.value = {
    ...categoryVersionItemsCache.value,
    [cacheKey]: itemNames,
  }
  return itemNames
}

const isCommunityNewItem = (itemName: string): boolean => communityVersionNewItems.value.has(itemName)

const updateCommunityVersionDiff = async () => {
  if (!selectedSlug.value || selectedCommunityVersion.value === null) {
    communityVersionNewItems.value = new Set()
    communityVersionDiffSummary.value = null
    return
  }

  const currentVersion = selectedCommunityVersion.value
  const previousVersion = categoryVersions.value
    .map((entry) => entry.version_number)
    .filter((entryVersion) => entryVersion < currentVersion)
    .sort((a, b) => b - a)[0]

  if (!previousVersion) {
    communityVersionNewItems.value = new Set()
    communityVersionDiffSummary.value = null
    return
  }

  const currentItems = await getCategoryItemsForVersion(selectedSlug.value, currentVersion)
  const previousItems = await getCategoryItemsForVersion(selectedSlug.value, previousVersion)
  const previousLower = new Set(previousItems.map((item) => item.toLowerCase()))
  const newItems = currentItems.filter((item) => !previousLower.has(item.toLowerCase()))

  communityVersionNewItems.value = new Set(newItems)
  if (newItems.length > 0) {
    communityVersionDiffSummary.value = `New in v${currentVersion}: ${newItems.join(', ')}`
  } else {
    communityVersionDiffSummary.value = `No new items compared with v${previousVersion}`
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
  supabaseClient.auth.onAuthStateChange(async (_event: AuthChangeEvent, sessionState: Session | null) => {
    adminSession.value = sessionState
    try {
      await fetchAdminCategories()
    } catch (err) {
      adminError.value = err instanceof Error ? err.message : 'Unknown error'
    }
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

const fetchAdminCategories = async () => {
  if (!isAdminView || !hasAdminAccess.value) {
    adminCategories.value = []
    managedCategorySlug.value = ''
    managedCategoryDetail.value = null
    managedBaseItems.value = []
    managedEditedItems.value = []
    return
  }

  loadingAdminCategories.value = true
  try {
    const response = await fetch(`${apiBase}/admin/categories`, {
      headers: getAdminHeaders(),
    })
    const payload = (await response.json()) as AdminCategoryListItem[] | { detail?: unknown }
    if (!response.ok) {
      throw new Error(formatApiError(payload, `Could not load admin categories (${response.status})`))
    }

    adminCategories.value = payload as AdminCategoryListItem[]
    const currentSlug = managedCategorySlug.value
    const stillExists = currentSlug
      ? adminLatestCategories.value.some((entry) => entry.slug === currentSlug)
      : false
    const fallback = adminLatestCategories.value[0]
    managedCategorySlug.value = stillExists ? currentSlug : fallback?.slug ?? ''

    if (managedCategorySlug.value) {
      await loadManagedCategory(managedCategorySlug.value)
    } else {
      managedCategoryDetail.value = null
      managedBaseItems.value = []
      managedEditedItems.value = []
    }
  } finally {
    loadingAdminCategories.value = false
  }
}

const loadManagedCategory = async (slug: string) => {
  const detail = await fetchCategoryDetail(slug)
  if (!detail) {
    throw new Error('Could not load selected category')
  }

  managedCategorySlug.value = slug
  managedCategoryDetail.value = detail
  const itemNames = detail.items
    .slice()
    .sort((a, b) => a.display_order - b.display_order)
    .map((item) => item.name)
  managedBaseItems.value = itemNames
  managedEditedItems.value = [...itemNames]
}

const createCategory = async () => {
  const name = newCategoryName.value.trim()
  const slug = newCategorySlug.value.trim()
  const description = newCategoryDescription.value.trim()
  const items = newCategoryItems.value.map((item) => item.trim()).filter((item) => item.length > 0)
  if (!name || !slug) {
    adminError.value = 'Category name and slug are required'
    return
  }
  if (items.length < 2) {
    adminError.value = 'Enter at least two items'
    return
  }
  if (new Set(items.map((item) => item.toLowerCase())).size !== items.length) {
    adminError.value = 'Items must be unique'
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
        items,
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
    newCategoryItems.value = ['', '']
    await fetchCategories()
    await fetchAdminCategories()

    if (payload.slug) {
      await selectCategory(payload.slug)
    }
    if (payload.slug) {
      await loadManagedCategory(payload.slug)
    }
  } catch (err) {
    adminError.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    creatingCategory.value = false
  }
}

const addItemField = () => {
  newCategoryItems.value = [...newCategoryItems.value, '']
}

const removeItemField = (index: number) => {
  if (newCategoryItems.value.length <= 2) {
    return
  }
  newCategoryItems.value = newCategoryItems.value.filter((_, itemIndex) => itemIndex !== index)
}

const onManagedCategoryChange = async () => {
  if (!managedCategorySlug.value) {
    managedCategoryDetail.value = null
    managedBaseItems.value = []
    managedEditedItems.value = []
    return
  }
  try {
    adminError.value = null
    await loadManagedCategory(managedCategorySlug.value)
  } catch (err) {
    adminError.value = err instanceof Error ? err.message : 'Unknown error'
  }
}

const addManagedItem = () => {
  const itemName = managedNewItem.value.trim()
  if (!itemName) {
    adminError.value = 'Enter an item name'
    return
  }
  const existing = new Set(managedEditedItems.value.map((item) => item.toLowerCase()))
  if (existing.has(itemName.toLowerCase())) {
    adminError.value = 'Item already exists in this version'
    return
  }
  managedEditedItems.value = [...managedEditedItems.value, itemName]
  managedNewItem.value = ''
  adminError.value = null
}

const removeManagedItem = (index: number) => {
  managedEditedItems.value = managedEditedItems.value.filter((_, itemIndex) => itemIndex !== index)
}

const publishManagedVersion = async () => {
  if (!managedCategoryDetail.value) {
    adminError.value = 'Choose a category first'
    return
  }
  if (managedEditedItems.value.length < 2) {
    adminError.value = 'A category version needs at least two items'
    return
  }
  if (!hasManagedChanges.value) {
    adminError.value = 'No item changes to publish'
    return
  }

  creatingVersion.value = true
  adminError.value = null
  adminMessage.value = null
  try {
    const response = await fetch(`${apiBase}/admin/categories/${managedCategoryDetail.value.slug}/versions`, {
      method: 'POST',
      headers: getAdminHeaders(),
      body: JSON.stringify({
        items: managedEditedItems.value,
        description: managedCategoryDetail.value.description,
      }),
    })
    const payload = (await response.json()) as { detail?: unknown; version_number?: number }
    if (!response.ok) {
      throw new Error(formatApiError(payload, `Could not publish new version (${response.status})`))
    }

    adminMessage.value = `Published ${managedCategoryDetail.value.slug} v${payload.version_number ?? '?'}`
    await fetchCategories()
    await fetchAdminCategories()
    if (selectedSlug.value === managedCategoryDetail.value.slug) {
      await selectCategory(managedCategoryDetail.value.slug)
    }
  } catch (err) {
    adminError.value = err instanceof Error ? err.message : 'Unknown error'
  } finally {
    creatingVersion.value = false
  }
}

const selectCategory = async (slug: string, version?: number) => {
  selectedSlug.value = slug
  communityRanking.value = null
  communityVersionNewItems.value = new Set()
  communityVersionDiffSummary.value = null
  error.value = null

  const payload = await fetchCategoryDetail(slug, version)
  if (!payload) {
    error.value = 'Unable to load category'
    return
  }

  category.value = payload
  if (version === undefined) {
    await fetchCategoryVersions(slug)
    categoryVersionItemsCache.value = {}
  }
  selectedCommunityVersion.value = payload.version_number
  const canonicalOrder = [...payload.items].sort((a, b) => a.display_order - b.display_order)
  rankingItems.value = shuffleItems(canonicalOrder)

  if (submittedCategoryIds.value.has(payload.id)) {
    await loadCommunityRanking(payload.version_number)
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

const loadCommunityRanking = async (version?: number) => {
  if (!selectedSlug.value) {
    return
  }
  const targetVersion = version ?? selectedCommunityVersion.value
  const versionQuery = targetVersion ? `?version=${targetVersion}` : ''
  const response = await fetch(`${apiBase}/categories/${selectedSlug.value}/community-ranking${versionQuery}`)
  if (!response.ok) {
    error.value = `Unable to load community ranking (${response.status})`
    return
  }

  communityRanking.value = (await response.json()) as CommunityRanking
  selectedCommunityVersion.value = communityRanking.value.category_version_number
  await updateCommunityVersionDiff()
}

const getCommunityScorePercent = (averageRank: number | null): number => {
  if (averageRank === null || !communityRanking.value) {
    return 0
  }
  const totalItems = communityRanking.value.items.length
  if (totalItems <= 0) {
    return 0
  }

  const clampedRank = Math.min(Math.max(averageRank, 1), totalItems)
  return ((totalItems - clampedRank + 1) / totalItems) * 100
}

const getVoteLabel = (voteCount: number): string => {
  return `${voteCount} vote${voteCount === 1 ? '' : 's'}`
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
      await loadCommunityRanking(category.value.version_number)
      return
    }

    if (!response.ok) {
      const payload = await response.json()
      throw new Error(formatApiError(payload, `Could not submit ranking (${response.status})`))
    }

    markCategorySubmitted(category.value.id)
    error.value = null
    await loadCommunityRanking(category.value.version_number)
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
  if (isAdminView) {
    try {
      await fetchAdminCategories()
    } catch (err) {
      adminError.value = err instanceof Error ? err.message : 'Unknown error'
    }
  }
})
</script>

<template>
  <main class="shell">
    <nav v-if="isAdminView" class="top-nav" aria-label="Primary">
      <a class="nav-link" href="/">Home</a>
    </nav>

    <PublicRankingSection
      v-if="!isAdminView"
      :loading="loading"
      :categories="categories"
      :selected-slug="selectedSlug"
      :error="error"
      :ranking-items="rankingItems"
      :dragged-index="draggedIndex"
      :can-submit="canSubmit"
      :submitting="submitting"
      :submit-button-label="submitButtonLabel"
      :has-submitted-current-category="hasSubmittedCurrentCategory"
      @select-category="selectCategory"
      @drag-start="handleDragStart"
      @drop="handleDrop"
      @drag-end="handleDragEnd"
      @move-item="moveItem($event.index, $event.direction)"
      @submit-ranking="submitRanking"
    />

    <CommunityRankingPanel
      v-if="communityRanking && !isAdminView"
      :community-ranking="communityRanking"
      :category-name="category?.name"
      :category-versions="categoryVersions"
      :selected-community-version="selectedCommunityVersion"
      :community-version-diff-summary="communityVersionDiffSummary"
      :is-community-new-item="isCommunityNewItem"
      :get-community-score-percent="getCommunityScorePercent"
      :get-vote-label="getVoteLabel"
      @select-version="loadCommunityRanking"
    />

    <AdminPanel
      v-if="isAdminView"
      :admin-auth-loading="adminAuthLoading"
      :has-admin-token="hasAdminToken"
      :admin-session="adminSession"
      :admin-secret="adminSecret"
      :has-admin-access="hasAdminAccess"
      :creating-category="creatingCategory"
      :new-category-name="newCategoryName"
      :new-category-slug="newCategorySlug"
      :new-category-description="newCategoryDescription"
      :new-category-items="newCategoryItems"
      :loading-admin-categories="loadingAdminCategories"
      :admin-latest-categories="adminLatestCategories"
      :managed-category-slug="managedCategorySlug"
      :managed-category-detail="managedCategoryDetail"
      :managed-new-item="managedNewItem"
      :managed-edited-items="managedEditedItems"
      :has-managed-changes="hasManagedChanges"
      :creating-version="creatingVersion"
      :admin-error="adminError"
      :admin-message="adminMessage"
      @sign-in-google="signInWithGoogle"
      @sign-out-admin="signOutAdmin"
      @update-admin-secret="adminSecret = $event"
      @update-new-category-name="newCategoryName = $event"
      @update-new-category-slug="newCategorySlug = $event"
      @update-new-category-description="newCategoryDescription = $event"
      @update-new-category-item="newCategoryItems[$event.index] = $event.value"
      @remove-item-field="removeItemField"
      @add-item-field="addItemField"
      @create-category="createCategory"
      @refresh-admin-categories="fetchAdminCategories"
      @update-managed-category-slug="managedCategorySlug = $event"
      @managed-category-change="onManagedCategoryChange"
      @update-managed-new-item="managedNewItem = $event"
      @add-managed-item="addManagedItem"
      @remove-managed-item="removeManagedItem"
      @publish-managed-version="publishManagedVersion"
    />
  </main>
</template>
