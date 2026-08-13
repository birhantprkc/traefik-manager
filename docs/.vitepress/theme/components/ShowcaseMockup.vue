<script setup>
import { withBase } from 'vitepress'
</script>

<template>
  <div class="showcase-wrap">
    <div class="showcase-inner">
      <div class="browser">
        <div class="browser-bar">
          <div class="browser-dots">
            <span /><span /><span />
          </div>
          <div class="browser-url">manager.example.com</div>
        </div>
        <div class="browser-content">
          <img :src="withBase('/images/light-routes-cards.png')" alt="Traefik Manager routes tab" class="browser-img shot-light" />
          <img :src="withBase('/images/dark-routes-cards.png')" alt="Traefik Manager routes tab" class="browser-img shot-dark" />
        </div>

        <div class="tablet">
          <div class="tablet-screen">
            <img :src="withBase('/images/light-tablet-overview.png')" alt="Traefik Manager on a tablet" class="tablet-img shot-light" />
            <img :src="withBase('/images/dark-tablet-overview.png')" alt="Traefik Manager on a tablet" class="tablet-img shot-dark" />
          </div>
        </div>

        <div class="phone">
          <div class="phone-screen">
            <img :src="withBase('/images/light-mobile-overview.png')" alt="Traefik Manager mobile app" class="phone-img shot-light" />
            <img :src="withBase('/images/dark-mobile-overview.png')" alt="Traefik Manager mobile app" class="phone-img shot-dark" />
            <div class="phone-punch" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.showcase-wrap {
  padding: 32px 24px 120px;
  width: 100%;
}

.showcase-inner {
  max-width: 880px;
  margin: 0 auto;
}

.browser {
  position: relative;
  border-radius: 10px;
  overflow: visible;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
  background: #e8eaed;
  border: 1px solid #d0d7de;
}


.browser-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
  height: 36px;
  border-bottom: 1px solid #d0d7de;
}


.browser-dots {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.browser-dots span {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d0d7de;
}


.browser-dots span:nth-child(1) { background: #ff5f57; }
.browser-dots span:nth-child(2) { background: #febc2e; }
.browser-dots span:nth-child(3) { background: #28c840; }

.browser-url {
  flex: 1;
  background: #ffffff;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  font-size: 11px;
  color: #636c76;
  font-family: system-ui, sans-serif;
  max-width: 280px;
  margin: 0 auto;
  padding: 0 8px;
}


.browser-content {
  height: 400px;
  overflow: hidden;
  border-radius: 0 0 10px 10px;
}

.browser-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top left;
  display: block;
}

.tablet {
  position: absolute;
  bottom: -58px;
  left: -30px;
  width: 232px;
  border-radius: 14px;
  background: #1c1f23;
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.26);
  padding: 6px;
  z-index: 9;
}

.tablet-screen {
  width: 100%;
  aspect-ratio: 1660 / 1721;
  border-radius: 9px;
  overflow: hidden;
  position: relative;
}

.tablet-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top left;
  display: block;
}

.phone {
  position: absolute;
  bottom: -78px;
  right: -26px;
  width: 152px;
  border-radius: 28px;
  background: #1c1f23;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.26);
  padding: 4px;
  z-index: 10;
}

.phone-screen {
  width: 100%;
  aspect-ratio: 864 / 1891;
  border-radius: 24px;
  overflow: hidden;
  position: relative;
}

.phone-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top;
  display: block;
}

.phone-punch {
  position: absolute;
  top: 9px;
  left: 50%;
  transform: translateX(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0b0d10;
  z-index: 2;
}


@media (max-width: 640px) {
  .browser-img {
    object-position: top center;
  }
  .tablet {
    display: none;
  }
  .phone {
    width: 80px;
    right: -8px;
    bottom: -38px;
    border-radius: 16px;
    padding: 2px;
  }
  .phone-screen {
    border-radius: 14px;
  }
  .phone-punch {
    width: 5px;
    height: 5px;
    top: 5px;
  }
}
</style>
