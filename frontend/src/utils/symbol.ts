/**
 * 符号规范化：纯数字 -> 带前缀
 * Examples: '518880' -> 'sh518880', '000300' -> 'sz000300'
 */
export function normalizeSymbol(raw: string): string {
  raw = (raw || '').trim().toLowerCase()
  if (!raw) return 'sh518880'

  // 已是完整代码
  if (raw.startsWith('sh') || raw.startsWith('sz')) return raw

  // 去掉可能的 cn_ 前缀
  if (raw.startsWith('cn_')) raw = raw.slice(3)

  // 6xxxxx -> 上海 (沪市主板 600/601/603 + 科创板 688)
  if (/^6\d{5}$/.test(raw)) return 'sh' + raw

  // 000xxx -> 深圳 (沪深300等指数)
  if (/^000\d{3}$/.test(raw)) return 'sz' + raw

  // 001xxx -> 深圳
  if (/^001\d{3}$/.test(raw)) return 'sz' + raw

  // 002xxx -> 深圳 (中小板)
  if (/^002\d{3}$/.test(raw)) return 'sz' + raw

  // 003xxx -> 深圳
  if (/^003\d{3}$/.test(raw)) return 'sz' + raw

  // 300xxx -> 创业板，深圳
  if (/^300\d{3}$/.test(raw)) return 'sz' + raw

  // 8xxxxx -> 北交所
  if (/^8\d{5}$/.test(raw)) return 'bj' + raw

  // 默认上海
  return 'sh' + raw
}

export function formatDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
