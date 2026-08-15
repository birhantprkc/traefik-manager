<script setup>
import { ref } from 'vue'
import { withBase } from 'vitepress'

const copied = ref(false)
const cmd = 'curl -fsSL https://get-traefik.xyzlab.dev | bash'

function copy() {
  navigator.clipboard.writeText(cmd)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}
</script>

<template>
  <section class="cta-wrap">
    <div class="cta-box">
      <h2 class="cta-title">Give your Traefik the UI it deserves</h2>
      <p class="cta-sub">One command installs Traefik and Traefik Manager together.</p>
      <div class="cta-install">
        <code class="cta-cmd">{{ cmd }}</code>
        <button class="cta-copy" @click="copy" :aria-label="copied ? 'Copied' : 'Copy'">
          <svg v-if="!copied" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"/></svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
        </button>
      </div>
      <p class="cta-support">Free and open source. If it saves you time, a star or a coffee goes a long way.</p>
      <div class="cta-actions">
        <a class="cta-btn cta-btn-primary" href="https://github.com/chr0nzz/traefik-manager" target="_blank" rel="noopener noreferrer">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 16 16" fill="currentColor"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/></svg>
          Star on GitHub
        </a>
        <a class="cta-btn" href="https://ko-fi.com/chr0nzz" target="_blank" rel="noopener noreferrer">
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M23.881 8.948c-.773-4.085-4.859-4.593-4.859-4.593H.723c-.604 0-.679.798-.679.798s-.082 7.324-.022 11.822c.164 2.424 2.586 2.672 2.586 2.672s8.267-.023 11.966-.049c2.438-.426 2.683-2.566 2.658-3.734 4.352.24 7.422-2.831 6.649-6.916zm-11.062 3.511c-1.246 1.453-4.011 3.976-4.011 3.976s-.121.119-.31.023c-.076-.057-.108-.09-.108-.09-.443-.441-3.368-3.049-4.034-3.954-.709-.965-1.041-2.7-.091-3.71.951-1.01 3.005-1.086 4.363.407 0 0 1.565-1.782 3.468-.963 1.904.82 1.832 3.011.723 4.311zm6.173.478c-.928.116-1.682.028-1.682.028V7.284h1.77s1.971.551 1.971 2.638c0 1.913-.985 2.667-2.059 3.015z"/></svg>
          Support on Ko-fi
        </a>
        <a class="cta-btn" :href="withBase('/guide')">Get Started</a>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cta-wrap {
  max-width: 1152px;
  margin: 0 auto;
  padding: 8px 24px 48px;
}

.cta-box {
  position: relative;
  overflow: hidden;
  text-align: center;
  border: 1px solid var(--vp-c-divider);
  border-radius: 16px;
  padding: 48px 32px;
  background:
    radial-gradient(ellipse 60% 120% at 20% 0%, rgba(124, 58, 237, 0.08), transparent),
    radial-gradient(ellipse 60% 120% at 80% 100%, rgba(13, 148, 136, 0.08), transparent),
    var(--vp-c-bg-soft);
}

.dark .cta-box {
  background:
    radial-gradient(ellipse 60% 120% at 20% 0%, rgba(124, 58, 237, 0.16), transparent),
    radial-gradient(ellipse 60% 120% at 80% 100%, rgba(13, 148, 136, 0.16), transparent),
    var(--vp-c-bg-soft);
}

.cta-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--vp-c-text-1);
  margin: 0 0 10px;
  border: none;
  padding: 0;
}

.cta-sub {
  font-size: 15px;
  color: var(--vp-c-text-2);
  margin: 0 0 20px;
}

.cta-install {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 12px 16px;
  max-width: 100%;
  box-sizing: border-box;
  margin: 0 0 24px;
}

.cta-cmd {
  font-family: var(--vp-font-family-mono, monospace);
  font-size: 13px;
  color: var(--vp-c-text-1);
  white-space: nowrap;
  overflow-x: auto;
  min-width: 0;
}

.cta-copy {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--vp-c-text-2);
  padding: 0;
  display: flex;
  align-items: center;
  transition: color 0.15s;
  flex-shrink: 0;
}

.cta-copy:hover {
  color: var(--vp-c-brand-1);
}

.cta-support {
  font-size: 13px;
  color: var(--vp-c-text-2);
  margin: 0 0 18px;
}

.cta-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 22px;
  border-radius: 22px;
  border: 1px solid var(--vp-c-divider);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  color: var(--vp-c-text-1);
  background: var(--vp-c-bg);
  transition: border-color 0.2s, opacity 0.2s;
}

.cta-btn:hover {
  border-color: var(--vp-c-brand-1);
}

.cta-btn-primary {
  background: var(--vp-c-brand-1);
  border-color: var(--vp-c-brand-1);
  color: #ffffff;
}

.cta-btn-primary:hover {
  opacity: 0.88;
}
</style>
