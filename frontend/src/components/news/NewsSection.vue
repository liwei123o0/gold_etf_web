<script setup lang="ts">
import type { NewsItem } from '@/services/stockService'

defineProps<{
  news: NewsItem[]
  title?: string
}>()
</script>

<template>
  <div class="news-section">
    <h2 class="section-title">{{ title || '📰 黄金国际新闻' }}</h2>
    <div class="news-grid">
      <template v-if="news.length > 0">
        <a
          v-for="(item, index) in news"
          :key="index"
          :href="item.url"
          target="_blank"
          class="news-card"
        >
          <h3 class="news-title">{{ item.title }}</h3>
          <div class="news-meta">
            <span class="news-source">{{ item.source }}</span>
            <span class="news-time">{{ item.time }}</span>
          </div>
        </a>
      </template>
      <div v-else class="no-news">暂无新闻</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.news-section {
  margin-top: 20px;
}

.section-title {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.news-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.news-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  text-decoration: none;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-purple);
    transform: translateY(-2px);
  }
}

.news-title {
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 10px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
}

.news-source {
  color: var(--accent-purple);
}

.no-news {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
</style>
