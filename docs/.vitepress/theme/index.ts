import { h, onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import { enhanceAppWithTabs } from 'vitepress-plugin-tabs/client'
import mediumZoom from 'medium-zoom'
import GitHubStars from './components/GitHubStars.vue'
import MobileRelease from './components/MobileRelease.vue'
import UnraidCAStatus from './components/UnraidCAStatus.vue'
import ComposeUpgrader from './components/ComposeUpgrader.vue'
import ShowcaseMockup from './components/ShowcaseMockup.vue'
import InstallSection from './components/InstallSection.vue'
import FeaturesSection from './components/FeaturesSection.vue'
import KoFiButton from './components/KoFiButton.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute()
    let zoom: ReturnType<typeof mediumZoom> | null = null

    const initZoom = () => {
      if (zoom) zoom.detach()
      zoom = mediumZoom('.screenshot', {
        margin: 32,
        background: 'rgba(0,0,0,0.85)',
      })
    }

    onMounted(() => nextTick(() => initZoom()))
    watch(() => route.path, () => nextTick(() => initZoom()))
  },
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => [h(KoFiButton), h(GitHubStars)],
      'home-features-before': () => [h(InstallSection), h(ShowcaseMockup)],
      'home-features-after': () => h(FeaturesSection),
    })
  },
  enhanceApp({ app }: { app: any }) {
    enhanceAppWithTabs(app)
    app.component('MobileRelease', MobileRelease)
    app.component('UnraidCAStatus', UnraidCAStatus)
    app.component('ComposeUpgrader', ComposeUpgrader)
    app.component('ShowcaseMockup', ShowcaseMockup)
    app.component('InstallSection', InstallSection)
    app.component('FeaturesSection', FeaturesSection)
  },
}
