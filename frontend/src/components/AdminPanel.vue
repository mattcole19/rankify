<script setup lang="ts">
type SessionUser = {
  email?: string
}

type SessionLike = {
  user?: SessionUser | null
}

type AdminCategoryListItem = {
  slug: string
  name: string
  version_number: number
}

type ManagedCategoryDetail = {
  slug: string
  version_number: number
}

defineProps<{
  adminAuthLoading: boolean
  hasAdminToken: boolean
  adminSession: SessionLike | null
  adminSecret: string
  hasAdminAccess: boolean
  creatingCategory: boolean
  newCategoryName: string
  newCategorySlug: string
  newCategoryDescription: string
  newCategoryItems: string[]
  loadingAdminCategories: boolean
  adminLatestCategories: AdminCategoryListItem[]
  managedCategorySlug: string
  managedCategoryDetail: ManagedCategoryDetail | null
  managedNewItem: string
  managedEditedItems: string[]
  hasManagedChanges: boolean
  creatingVersion: boolean
  adminError: string | null
  adminMessage: string | null
}>()

const emit = defineEmits<{
  (e: 'sign-in-google'): void
  (e: 'sign-out-admin'): void
  (e: 'update-admin-secret', value: string): void
  (e: 'update-new-category-name', value: string): void
  (e: 'update-new-category-slug', value: string): void
  (e: 'update-new-category-description', value: string): void
  (e: 'update-new-category-item', payload: { index: number; value: string }): void
  (e: 'remove-item-field', index: number): void
  (e: 'add-item-field'): void
  (e: 'create-category'): void
  (e: 'refresh-admin-categories'): void
  (e: 'update-managed-category-slug', value: string): void
  (e: 'managed-category-change'): void
  (e: 'update-managed-new-item', value: string): void
  (e: 'add-managed-item'): void
  (e: 'remove-managed-item', index: number): void
  (e: 'publish-managed-version'): void
}>()
</script>

<template>
  <section class="panel admin-panel" aria-live="polite">
    <p class="panel-label">admin tools</p>
    <h2>Create Categories and Items</h2>
    <p class="panel-detail">Sign in with Google to manage categories and items.</p>

    <div class="admin-auth-row">
      <button class="cta" type="button" :disabled="adminAuthLoading || hasAdminToken" @click="emit('sign-in-google')">
        {{ hasAdminToken ? 'Signed in with Google' : 'Sign in with Google' }}
      </button>
      <button class="secondary" type="button" :disabled="!hasAdminToken" @click="emit('sign-out-admin')">
        Sign out
      </button>
    </div>

    <p class="panel-detail" v-if="hasAdminToken">Authenticated as {{ adminSession?.user?.email }}</p>
    <p class="panel-detail">Fallback local-only option:</p>

    <label class="field-label" for="admin-secret">Admin Secret</label>
    <input
      id="admin-secret"
      :value="adminSecret"
      class="text-input"
      type="password"
      @input="emit('update-admin-secret', ($event.target as HTMLInputElement).value)"
    />

    <div class="admin-grid">
      <article class="admin-card">
        <h3>Create Category + Items</h3>
        <label class="field-label" for="new-category-name">Name</label>
        <input
          id="new-category-name"
          :value="newCategoryName"
          class="text-input"
          type="text"
          @input="emit('update-new-category-name', ($event.target as HTMLInputElement).value)"
        />

        <label class="field-label" for="new-category-slug">Slug</label>
        <input
          id="new-category-slug"
          :value="newCategorySlug"
          class="text-input"
          type="text"
          @input="emit('update-new-category-slug', ($event.target as HTMLInputElement).value)"
        />

        <label class="field-label" for="new-category-description">Description</label>
        <textarea
          id="new-category-description"
          :value="newCategoryDescription"
          class="text-input"
          rows="3"
          @input="emit('update-new-category-description', ($event.target as HTMLTextAreaElement).value)"
        />

        <label class="field-label">Items</label>
        <div class="admin-stack">
          <div v-for="(itemDraft, index) in newCategoryItems" :key="`new-item-${index}`" class="admin-inline-row">
            <input
              :value="itemDraft"
              class="text-input admin-inline-input"
              type="text"
              :placeholder="`Item ${index + 1}`"
              @input="emit('update-new-category-item', { index, value: ($event.target as HTMLInputElement).value })"
            />
            <button
              class="secondary small"
              type="button"
              :disabled="newCategoryItems.length <= 2"
              @click="emit('remove-item-field', index)"
            >
              Remove
            </button>
          </div>
        </div>
        <button class="secondary small" type="button" @click="emit('add-item-field')">+ Add Item</button>

        <button class="secondary" :disabled="creatingCategory || !hasAdminAccess" @click="emit('create-category')">
          {{ creatingCategory ? 'Creating…' : 'Create Category' }}
        </button>
      </article>

      <article class="admin-card">
        <div class="admin-card-title-row">
          <h3>Edit Items and Publish New Version</h3>
          <button class="secondary small" type="button" :disabled="loadingAdminCategories" @click="emit('refresh-admin-categories')">
            {{ loadingAdminCategories ? 'Refreshing…' : 'Refresh' }}
          </button>
        </div>

        <label class="field-label" for="admin-category-select">Category</label>
        <select
          id="admin-category-select"
          :value="managedCategorySlug"
          class="select"
          :disabled="loadingAdminCategories || adminLatestCategories.length === 0"
          @change="emit('update-managed-category-slug', ($event.target as HTMLSelectElement).value); emit('managed-category-change')"
        >
          <option v-for="entry in adminLatestCategories" :key="entry.slug" :value="entry.slug">
            {{ entry.name }} (latest v{{ entry.version_number }})
          </option>
        </select>

        <template v-if="managedCategoryDetail">
          <p class="panel-detail">
            Editing <strong>{{ managedCategoryDetail.slug }}</strong> from v{{ managedCategoryDetail.version_number }}.
            Changes here are local until you publish.
          </p>

          <label class="field-label" for="admin-new-item">Add Item</label>
          <div class="admin-inline-row">
            <input
              id="admin-new-item"
              :value="managedNewItem"
              class="text-input admin-inline-input"
              type="text"
              @input="emit('update-managed-new-item', ($event.target as HTMLInputElement).value)"
            />
            <button class="secondary" :disabled="!hasAdminAccess" @click="emit('add-managed-item')">
              Add
            </button>
          </div>

          <label class="field-label">Items for Next Version</label>
          <div class="admin-stack">
            <div v-for="(itemName, index) in managedEditedItems" :key="`${managedCategorySlug}-${itemName}-${index}`" class="admin-inline-row">
              <input :value="itemName" class="text-input admin-inline-input" type="text" disabled />
              <button
                class="secondary small danger"
                :disabled="!hasAdminAccess"
                @click="emit('remove-managed-item', index)"
              >
                Delete
              </button>
            </div>
          </div>

          <button class="secondary" :disabled="creatingVersion || !hasAdminAccess || !hasManagedChanges" @click="emit('publish-managed-version')">
            {{ creatingVersion ? 'Publishing…' : 'Publish New Version' }}
          </button>
        </template>

        <p v-else class="panel-detail">No categories yet. Create one first.</p>
      </article>
    </div>

    <p v-if="adminError" class="error">{{ adminError }}</p>
    <p v-if="adminMessage" class="admin-success">{{ adminMessage }}</p>
  </section>
</template>
