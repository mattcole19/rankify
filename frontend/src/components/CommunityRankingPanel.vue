<script setup lang="ts">
type CategoryVersionSummary = {
  version_number: number
  submission_count: number
}

type CommunityItem = {
  item_id: number
  item_name: string
  average_rank: number | null
  vote_count: number
}

type CommunityRanking = {
  category_version_number: number
  total_submissions: number
  items: CommunityItem[]
}

defineProps<{
  communityRanking: CommunityRanking
  categoryName: string | undefined
  categoryVersions: CategoryVersionSummary[]
  selectedCommunityVersion: number | null
  communityVersionDiffSummary: string | null
  isCommunityNewItem: (itemName: string) => boolean
  getCommunityScorePercent: (averageRank: number | null) => number
  getVoteLabel: (voteCount: number) => string
}>()

const emit = defineEmits<{
  (e: 'select-version', version: number): void
}>()
</script>

<template>
  <section class="panel" aria-live="polite">
    <p class="panel-label">community ranking</p>
    <h2>{{ categoryName }} <span class="version-pill">v{{ communityRanking.category_version_number }}</span></h2>
    <p class="panel-detail">{{ communityRanking.total_submissions }} total submissions</p>
    <div class="version-controls" v-if="categoryVersions.length > 1">
      <label class="field-label" for="community-version-select">Version</label>
      <select
        id="community-version-select"
        class="select"
        :value="selectedCommunityVersion ?? communityRanking.category_version_number"
        @change="emit('select-version', Number(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="entry in categoryVersions" :key="`community-v-${entry.version_number}`" :value="entry.version_number">
          v{{ entry.version_number }} ({{ entry.submission_count }} submissions)
        </option>
      </select>
      <p v-if="communityVersionDiffSummary" class="version-diff-note">{{ communityVersionDiffSummary }}</p>
    </div>
    <ol class="community-list">
      <li v-for="entry in communityRanking.items" :key="entry.item_id">
        <div class="community-item-top">
          <span class="community-item-name"
            >{{ entry.item_name }}
            <span v-if="isCommunityNewItem(entry.item_name)" class="new-item-pill">New</span></span
          >
          <span v-if="entry.average_rank" class="community-item-metric"
            >avg #{{ entry.average_rank.toFixed(2) }}</span
          >
          <span v-else class="community-item-metric">not ranked yet</span>
        </div>
        <div class="community-item-bottom">
          <div class="community-score-track" aria-hidden="true">
            <span class="community-score-fill" :style="{ width: `${getCommunityScorePercent(entry.average_rank)}%` }" />
          </div>
          <span class="community-vote-count">{{ getVoteLabel(entry.vote_count) }}</span>
        </div>
      </li>
    </ol>
  </section>
</template>
