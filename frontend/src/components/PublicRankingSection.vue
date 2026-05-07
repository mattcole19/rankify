<script setup lang="ts">
type CategorySummary = {
  slug: string
  name: string
  item_count: number
}

type CategoryItem = {
  id: number
  name: string
}

defineProps<{
  loading: boolean
  categories: CategorySummary[]
  selectedSlug: string | null
  error: string | null
  rankingItems: CategoryItem[]
  draggedIndex: number | null
  canSubmit: boolean
  submitting: boolean
  submitButtonLabel: string
  hasSubmittedCurrentCategory: boolean
}>()

const emit = defineEmits<{
  (e: 'select-category', slug: string): void
  (e: 'drag-start', index: number): void
  (e: 'drop', index: number): void
  (e: 'drag-end'): void
  (e: 'move-item', payload: { index: number; direction: -1 | 1 }): void
  (e: 'submit-ranking'): void
}>()
</script>

<template>
  <section class="hero">
    <p class="eyebrow">Rankify</p>
    <h1>Rank fast. Compare with everyone.</h1>
    <p class="lede">Choose a category, reorder items, submit, and instantly view the community ranking.</p>

    <label class="field-label" for="category-select">Category</label>
    <select
      id="category-select"
      class="select"
      :disabled="loading || categories.length === 0"
      :value="selectedSlug ?? ''"
      @change="emit('select-category', ($event.target as HTMLSelectElement).value)"
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
        @dragstart="emit('drag-start', index)"
        @dragover.prevent
        @drop="emit('drop', index)"
        @dragend="emit('drag-end')"
      >
        <p class="rank-position">#{{ index + 1 }}</p>
        <p class="rank-name">{{ item.name }}</p>
        <div class="rank-actions">
          <button class="secondary small" :disabled="index === 0" @click="emit('move-item', { index, direction: -1 })">
            Up
          </button>
          <button
            class="secondary small"
            :disabled="index === rankingItems.length - 1"
            @click="emit('move-item', { index, direction: 1 })"
          >
            Down
          </button>
        </div>
      </article>
    </div>

    <div class="cta-row">
      <button class="cta" type="button" :disabled="!canSubmit || submitting" @click="emit('submit-ranking')">
        {{ submitButtonLabel }}
      </button>
    </div>

    <p v-if="hasSubmittedCurrentCategory" class="submission-note">
      You already submitted this category.
    </p>
  </section>
</template>
