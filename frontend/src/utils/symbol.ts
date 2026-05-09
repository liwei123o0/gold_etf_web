/**
 * 股票代码处理工具
 * 统一股票代码的前缀识别逻辑
 * 页面输入只需要6位数字，前缀通过工具类自动识别
 */

/**
 * 规范化股票代码：纯数字 -> 带前缀
 * 
 * @param raw 股票代码（可以是6位数字或带前缀的完整代码）
 * @returns 带前缀的完整股票代码
 * 
 * Examples:
 *   '518880' -> 'sh518880'
 *   '000300' -> 'sz000300'
 *   '300001' -> 'sz300001'
 *   '688001' -> 'sh688001'
 *   '831010' -> 'bj831010'
 *   'sh518880' -> 'sh518880'
 */
export function normalizeSymbol(raw: string): string {
  raw = (raw || '').trim().toLowerCase()
  if (!raw) return 'sh518880'

  // 已是完整代码（带前缀）
  if (raw.startsWith('sh') || raw.startsWith('sz') || raw.startsWith('bj')) {
    return raw
  }

  // 去掉可能的 cn_ 前缀
  if (raw.startsWith('cn_')) {
    raw = raw.slice(3)
  }

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

  // 301xxx -> 创业板注册制，深圳
  if (/^301\d{3}$/.test(raw)) return 'sz' + raw

  // 8xxxxx -> 北交所
  if (/^8\d{5}$/.test(raw)) return 'bj' + raw

  // 默认上海
  return 'sh' + raw
}

/**
 * 去除股票代码前缀，只保留6位数字
 * 
 * @param symbol 带前缀的股票代码
 * @returns 6位数字股票代码
 * 
 * Examples:
 *   'sh518880' -> '518880'
 *   'sz000300' -> '000300'
 *   'bj831010' -> '831010'
 *   '518880' -> '518880'
 */
export function stripPrefix(symbol: string): string {
  symbol = (symbol || '').trim().toLowerCase()

  // 去掉前缀
  if (symbol.startsWith('sh')) return symbol.slice(2)
  if (symbol.startsWith('sz')) return symbol.slice(2)
  if (symbol.startsWith('bj')) return symbol.slice(2)
  if (symbol.startsWith('cn_')) return symbol.slice(3)

  return symbol
}

/**
 * 验证股票代码是否为有效格式（6位数字）
 * 
 * @param code 股票代码
 * @returns True 如果是有效的6位数字股票代码
 */
export function validateStockCode(code: string): boolean {
  code = (code || '').trim()
  return /^\d{6}$/.test(code)
}

/**
 * 获取股票所属交易所
 * 
 * @param symbol 股票代码（带前缀或不带前缀）
 * @returns 'sh' | 'sz' | 'bj'
 */
export function getExchange(symbol: string): string {
  symbol = (symbol || '').trim().toLowerCase()

  if (symbol.startsWith('sh')) return 'sh'
  if (symbol.startsWith('bj')) return 'bj'
  if (symbol.startsWith('sz')) return 'sz'

  // 根据数字判断
  if (/^6\d{5}$/.test(symbol)) return 'sh'
  if (/^8\d{5}$/.test(symbol)) return 'bj'
  return 'sz'
}

/**
 * 格式化股票代码用于显示（不带前缀）
 * 
 * @param symbol 股票代码
 * @returns 6位数字股票代码
 */
export function formatSymbolForDisplay(symbol: string): string {
  return stripPrefix(symbol)
}

export function formatDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
