<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { stockService, type SimSettings } from '@/services/stockService'
import { useGlobalSettings } from '@/composables/useGlobalSettings'

const defaultSettings = ref<SimSettings>({
  commission_rate: 0.0003,
  min_commission: 5.0,
  stamp_tax_rate: 0.001,
  transfer_fee_rate: 0.00002,
})
const isSavingDefault = ref(false)
const defaultMsg = ref('')

const { settings: globalSettings, updateSetting } = useGlobalSettings()
const intervalMsg = ref('')

const intervalOptions = [
  { label: '5秒', value: 5000 },
  { label: '10秒', value: 10000 },
  { label: '30秒', value: 30000 },
  { label: '1分钟', value: 60000 },
  { label: '5分钟', value: 300000 },
]

function onIntervalChange(key: 'realtimeInterval' | 'simRealtimeInterval' | 'autoTradeInterval', event: Event) {
  const target = event.target as HTMLSelectElement
  updateSetting(key, Number(target.value))
  intervalMsg.value = 'success'
  setTimeout(() => { intervalMsg.value = '' }, 3000)
}

interface SymbolSetting extends SimSettings { symbol: string }
const symbolList = ref<SymbolSetting[]>([])
const isLoadingSymbols = ref(false)

const newSymbol = ref('')
const newSymbolSettings = ref<Partial<SimSettings>>({})
const isAddingSymbol = ref(false)
const addMsg = ref('')

const editingSymbol = ref<string | null>(null)
const editSettings = ref<Partial<SimSettings>>({})

onMounted(async () => {
  try { defaultSettings.value = await stockService.getSettings() } catch (e) { console.error(e) }
  await loadSymbolList()
})

async function loadSymbolList() {
  isLoadingSymbols.value = true
  try { symbolList.value = await stockService.getAllSymbolSettings() }
  catch (e) { console.error(e) }
  finally { isLoadingSymbols.value = false }
}

async function saveDefaultSettings() {
  isSavingDefault.value = true
  defaultMsg.value = ''
  try {
    defaultSettings.value = await stockService.updateSettings(defaultSettings.value)
    defaultMsg.value = 'success'
    setTimeout(() => { defaultMsg.value = '' }, 3000)
  } catch { defaultMsg.value = 'failed' }
  finally { isSavingDefault.value = false }
}

async function addSymbolSetting() {
  if (!newSymbol.value.trim()) return
  isAddingSymbol.value = true
  addMsg.value = ''
  try {
    const sym = newSymbol.value.trim().toLowerCase()
    await stockService.upsertSymbolSettings(sym, newSymbolSettings.value)
    newSymbol.value = ''
    newSymbolSettings.value = {}
    await loadSymbolList()
    addMsg.value = 'success'
    setTimeout(() => { addMsg.value = '' }, 3000)
  } catch { addMsg.value = 'failed' }
  finally { isAddingSymbol.value = false }
}

async function deleteSymbolSetting(symbol: string) {
  try { await stockService.deleteSymbolSettings(symbol); await loadSymbolList() }
  catch (e) { console.error(e) }
}

function startEdit(symbol: string) {
  editingSymbol.value = symbol
  const existing = symbolList.value.find(s => s.symbol === symbol)
  if (existing) {
    editSettings.value = {
      commission_rate: existing.commission_rate,
      min_commission: existing.min_commission,
      stamp_tax_rate: existing.stamp_tax_rate,
      transfer_fee_rate: existing.transfer_fee_rate,
    }
  }
}

async function saveEdit() {
  if (!editingSymbol.value) return
  try {
    await stockService.upsertSymbolSettings(editingSymbol.value, editSettings.value)
    editingSymbol.value = null
    await loadSymbolList()
  } catch (e) { console.error(e) }
}

function cancelEdit() {
  editingSymbol.value = null
  editSettings.value = {}
}

function formatRate(rate: number | undefined, defaultRate: number): string {
  if (rate === undefined || rate === null) return '默认'
  return (rate * 100).toFixed(4) + '%'
}
</script>

<template>
  <div class="settings-page">
    <AppHeader />
    <main class="settings-content">
      <h2 class="page-title">系统设置</h2>

      <div class="settings-card">
        <h3 class="card-title">默认费率设置</h3>
        <p class="card-desc">所有证券默认使用以下费率</p>
        <div class="form-grid">
          <div class="form-item">
            <label>佣金费率</label>
            <div class="input-group">
              <input v-model.number="defaultSettings.commission_rate" type="number" min="0" max="0.01" step="0.0001" />
              <span class="unit">(如 0.0003 = 0.03%)</span>
            </div>
          </div>
          <div class="form-item">
            <label>最低佣金</label>
            <div class="input-group">
              <input v-model.number="defaultSettings.min_commission" type="number" min="0" step="0.1" />
              <span class="unit">元</span>
            </div>
          </div>
          <div class="form-item">
            <label>印花税</label>
            <div class="input-group">
              <input v-model.number="defaultSettings.stamp_tax_rate" type="number" min="0" max="0.01" step="0.0001" />
              <span class="unit">(仅卖出，如 0.001 = 0.1%)</span>
            </div>
          </div>
          <div class="form-item">
            <label>过户费</label>
            <div class="input-group">
              <input v-model.number="defaultSettings.transfer_fee_rate" type="number" min="0" max="0.001" step="0.00001" />
              <span class="unit">(仅沪市，如 0.00002 = 0.002%)</span>
            </div>
          </div>
        </div>
        <div class="form-actions">
          <button class="save-btn" :disabled="isSavingDefault" @click="saveDefaultSettings">
            {{ isSavingDefault ? '保存中...' : '保存默认' }}
          </button>
          <span v-if="defaultMsg" class="message" :class="{ success: defaultMsg === 'success' }">{{ defaultMsg === 'success' ? '保存成功' : '保存失败' }}</span>
        </div>
      </div>

      <div class="settings-card">
        <h3 class="card-title">刷新间隔设置</h3>
        <p class="card-desc">全局数据刷新频率设置，修改后立即生效</p>
        <div class="form-grid">
          <div class="form-item">
            <label>行情刷新</label>
            <div class="input-group">
              <select
                :value="globalSettings.realtimeInterval"
                class="input select"
                @change="onIntervalChange('realtimeInterval', $event)"
              >
                <option v-for="opt in intervalOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <span class="unit">看板行情轮询间隔</span>
            </div>
          </div>
          <div class="form-item">
            <label>模拟交易</label>
            <div class="input-group">
              <select
                :value="globalSettings.simRealtimeInterval"
                class="input select"
                @change="onIntervalChange('simRealtimeInterval', $event)"
              >
                <option v-for="opt in intervalOptions.filter(o => o.value <= 30000)" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <span class="unit">模拟交易行情刷新间隔</span>
            </div>
          </div>
          <div class="form-item">
            <label>自动交易</label>
            <div class="input-group">
              <select
                :value="globalSettings.autoTradeInterval"
                class="input select"
                @change="onIntervalChange('autoTradeInterval', $event)"
              >
                <option v-for="opt in intervalOptions.filter(o => o.value >= 10000)" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
              <span class="unit">自动交易检查间隔</span>
            </div>
          </div>
        </div>
        <span v-if="intervalMsg" class="message" :class="{ success: intervalMsg === 'success' }">{{ intervalMsg === 'success' ? '已保存' : '保存失败' }}</span>
      </div>

      <div class="settings-card">
        <h3 class="card-title">单只证券费率设置</h3>
        <p class="card-desc">为特定证券单独设置费率，留空则使用默认设置</p>
        <div class="add-symbol-form">
          <input v-model="newSymbol" type="text" class="input" placeholder="证券代码，如 sh518880" />
          <div class="symbol-fee-inputs">
            <input v-model.number="newSymbolSettings.commission_rate" type="number" min="0" step="0.0001" placeholder="佣金" title="佣金费率（可选）" />
            <input v-model.number="newSymbolSettings.min_commission" type="number" min="0" step="0.1" placeholder="最低" title="最低佣金（可选）" />
            <input v-model.number="newSymbolSettings.stamp_tax_rate" type="number" min="0" step="0.0001" placeholder="印花" title="印花税（可选）" />
            <input v-model.number="newSymbolSettings.transfer_fee_rate" type="number" min="0" step="0.00001" placeholder="过户" title="过户费（可选）" />
          </div>
          <button class="add-btn" :disabled="isAddingSymbol || !newSymbol.trim()" @click="addSymbolSetting">
            {{ isAddingSymbol ? '添加中...' : '添加' }}
          </button>
          <span v-if="addMsg" class="message" :class="{ success: addMsg === 'success' }">{{ addMsg === 'success' ? '添加成功' : '添加失败' }}</span>
        </div>

        <div v-if="isLoadingSymbols" class="loading">加载中...</div>
        <div v-else-if="symbolList.length === 0" class="empty">暂无单只证券费率设置</div>
        <div v-else class="symbol-table-wrap">
          <table class="symbol-table">
            <thead>
              <tr>
                <th>证券代码</th>
                <th>佣金费率</th>
                <th>最低佣金</th>
                <th>印花税</th>
                <th>过户费</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in symbolList" :key="s.symbol">
                <template v-if="editingSymbol === s.symbol">
                  <td>{{ s.symbol }}</td>
                  <td><input v-model.number="editSettings.commission_rate" type="number" step="0.0001" /></td>
                  <td><input v-model.number="editSettings.min_commission" type="number" step="0.1" /></td>
                  <td><input v-model.number="editSettings.stamp_tax_rate" type="number" step="0.0001" /></td>
                  <td><input v-model.number="editSettings.transfer_fee_rate" type="number" step="0.00001" /></td>
                  <td>
                    <button class="action-btn save" @click="saveEdit">保存</button>
                    <button class="action-btn cancel" @click="cancelEdit">取消</button>
                  </td>
                </template>
                <template v-else>
                  <td>{{ s.symbol }}</td>
                  <td>{{ formatRate(s.commission_rate, defaultSettings.commission_rate) }}</td>
                  <td>{{ s.min_commission !== undefined && s.min_commission !== null ? s.min_commission + ' 元' : '默认' }}</td>
                  <td>{{ formatRate(s.stamp_tax_rate, defaultSettings.stamp_tax_rate) }}</td>
                  <td>{{ formatRate(s.transfer_fee_rate, defaultSettings.transfer_fee_rate) }}</td>
                  <td>
                    <button class="action-btn edit" @click="startEdit(s.symbol)">编辑</button>
                    <button class="action-btn delete" @click="deleteSymbolSetting(s.symbol)">删除</button>
                  </td>
                </template>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.settings-page { min-height: 100vh; background: var(--bg-primary); }
.settings-content { max-width: 900px; margin: 0 auto; padding: 24px 16px; }
.page-title { color: var(--text-primary); font-size: 22px; margin: 0 0 20px; }
.settings-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 24px; margin-bottom: 16px; }
.card-title { color: #7986cb; font-size: 16px; margin: 0 0 8px; }
.card-desc { color: var(--text-muted); font-size: 13px; margin: 0 0 20px; }
.form-grid { display: flex; flex-direction: column; gap: 16px; }
.form-item { display: flex; align-items: center; gap: 16px;
  label { width: 80px; color: var(--text-secondary); font-size: 14px; flex-shrink: 0; }
}
.input-group { display: flex; align-items: center; gap: 10px; flex: 1;
  input { width: 140px; padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 14px;
    &:focus { outline: none; border-color: var(--accent-cyan); }
  }
  .unit { color: var(--text-muted); font-size: 12px; }
}
.select { cursor: pointer; }
.form-actions { display: flex; align-items: center; gap: 16px; margin-top: 20px; }
.save-btn { padding: 10px 24px; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)); border: none; border-radius: 8px; color: #fff; font-size: 14px; font-weight: bold; cursor: pointer;
  &:hover:not(:disabled) { opacity: 0.9; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
.message { font-size: 13px; color: #ef5350;
  &.success { color: #26a69a; }
}
.add-symbol-form { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 20px;
  .input { flex: 1; min-width: 160px; padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 14px;
    &:focus { outline: none; border-color: var(--accent-cyan); }
  }
}
.symbol-fee-inputs { display: flex; gap: 6px;
  input { width: 80px; padding: 6px 8px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 12px;
    &:focus { outline: none; border-color: var(--accent-cyan); }
  }
}
.add-btn { padding: 8px 16px; background: var(--accent-cyan); border: none; border-radius: 6px; color: #000; font-size: 13px; font-weight: bold; cursor: pointer;
  &:hover:not(:disabled) { opacity: 0.85; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
.loading, .empty { padding: 24px; text-align: center; color: var(--text-muted); font-size: 14px; }
.symbol-table-wrap { overflow-x: auto; }
.symbol-table { width: 100%; border-collapse: collapse; font-size: 13px;
  th, td { padding: 10px 12px; text-align: center; white-space: nowrap; }
  th { background: var(--bg-hover); color: #7986cb; font-weight: normal; font-size: 12px; }
  tr:not(:last-child) td { border-bottom: 1px solid var(--border-color); }
  td { color: var(--text-primary); }
  input { width: 70px; padding: 4px 6px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 12px; text-align: center;
    &:focus { outline: none; border-color: var(--accent-cyan); }
  }
}
.action-btn { padding: 4px 10px; border: none; border-radius: 4px; font-size: 12px; cursor: pointer; margin: 0 2px;
  &.edit { background: rgba(0,242,255,0.1); color: var(--accent-cyan); }
  &.delete { background: rgba(239,83,80,0.1); color: #ef5350; }
  &.save { background: var(--accent-cyan); color: #000; }
  &.cancel { background: var(--bg-hover); color: var(--text-secondary); }
}
</style>
