/** Settings Store：主题、API 地址、字号等 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

type Theme = 'light' | 'dark' | 'cyber'

const SETTINGS_KEY = 'kb-settings'

interface Settings {
  theme: Theme
  apiBase: string
  fontSize: 'small' | 'medium' | 'large'
}

const defaults: Settings = {
  theme: 'light',
  apiBase: 'http://127.0.0.1:8765',
  fontSize: 'medium',
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<Theme>('light')
  const apiBase = ref<string>(defaults.apiBase)
  const fontSize = ref<Settings['fontSize']>('medium')

  const isDark = computed(() => theme.value === 'dark' || theme.value === 'cyber')

  function init() {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY)
      if (raw) {
        const s = JSON.parse(raw) as Partial<Settings>
        if (s.theme) theme.value = s.theme
        if (s.apiBase) apiBase.value = s.apiBase
        if (s.fontSize) fontSize.value = s.fontSize
      }
    } catch (e) {
      console.error('Failed to load settings', e)
    }
    applyTheme()
  }

  function save() {
    const s: Settings = {
      theme: theme.value,
      apiBase: apiBase.value,
      fontSize: fontSize.value,
    }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  }

  function applyTheme() {
    if (theme.value === 'cyber') {
      document.documentElement.setAttribute('data-theme', 'cyber')
    } else if (theme.value === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.removeAttribute('data-theme')
    }
  }

  function setTheme(t: Theme) {
    theme.value = t
    applyTheme()
    save()
  }

  function setApiBase(url: string) {
    apiBase.value = url
    save()
  }

  function setFontSize(s: Settings['fontSize']) {
    fontSize.value = s
    save()
  }

  return {
    theme, apiBase, fontSize, isDark,
    init, setTheme, setApiBase, setFontSize,
  }
})
