<script setup lang="ts">
import { computed } from 'vue'
import type { GridSignal } from '@/services/stockService'

const props = defineProps<{
  signals: string[][]
  tradeSignal: string
  gridSignal?: GridSignal
}>()

const filteredSignals = computed(() => {
  return props.signals.filter(s => s[0] !== '网格信号')
})

const signalClass = computed(() => {
  if (props.tradeSignal === '买入') return 'bullish'
  if (props.tradeSignal === '卖出') return 'bearish'
  return 'neutral'
})

function getSignalIcon(status: string): string {
  if (status.includes('✅') || status.includes('📈')) return '📈'
  if (status.includes('⚠️')) return '⚠️'
  return '➡️'
}
</script>

<template>
  <div class="analysis-section">
    <h2 class="section-title">综合分析建议</h2>

    <div class="signal-grid">
      <div
        v-for="(signal, index) in filteredSignals"
        :key="index"
        class="signal-item"
        :class="{ bullish: signal[1].includes('✅') || signal[1].includes('📈') }"
      >
        <span class="signal-icon">{{ getSignalIcon(signal[1]) }}</span>
        <div class="signal-info">
          <h4>{{ signal[0] }}</h4>
          <div class="status">{{ signal[1] }}</div>
          <div class="desc">{{ signal[2] }}</div>
        </div>
      </div>
    </div>

    <div class="final-advice" :class="signalClass">
      <template v-if="tradeSignal === '买入'">
        <h3>📈 综合建议：短期偏多</h3>
        <p>多个指标显示多方占优，但需注意KDJ超买风险。建议逢低布局，控制仓位，设定止损位。</p>
      </template>
      <template v-else-if="tradeSignal === '卖出'">
        <h3>📉 综合建议：短期偏空</h3>
        <p>多个指标显示空方占优，建议谨慎操作。可关注超卖信号出现时的反弹机会，但需快进快出。</p>
      </template>
      <template v-else>
        <h3>➡️ 综合建议：观望</h3>
        <p>多空信号交织，建议观望等待明确趋势。关注关键支撑位和压力位的突破情况。</p>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.analysis-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 18px;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.signal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.signal-item {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  gap: 10px;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-purple);
  }

  &.bullish {
    border-left: 3px solid #26a69a;
  }
}

.signal-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.signal-info {
  flex: 1;
  min-width: 0;

  h4 {
    font-size: 13px;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .status {
    font-size: 12px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .desc {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }
}

.final-advice {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;

  &.bullish {
    border-left: 4px solid #26a69a;
    background: linear-gradient(135deg, rgba(38, 166, 154, 0.1) 0%, var(--bg-card) 100%);
  }

  &.bearish {
    border-left: 4px solid #ef5350;
    background: linear-gradient(135deg, rgba(239, 83, 80, 0.1) 0%, var(--bg-card) 100%);
  }

  &.neutral {
    border-left: 4px solid #FF9800;
    background: linear-gradient(135deg, rgba(255, 152, 0, 0.1) 0%, var(--bg-card) 100%);
  }

  h3 {
    font-size: 16px;
    color: var(--text-primary);
    margin-bottom: 10px;
  }

  p {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
  }
}
</style>
