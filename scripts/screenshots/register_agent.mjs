import fs from 'fs';
import puppeteer from 'puppeteer';

const BASE = 'http://tmshot-app:5000';
const browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] });
const page = await browser.newPage();
await page.goto(BASE + '/', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForFunction('typeof _csrfHeaders === "function"', { timeout: 30000 });

page.on('pageerror', e => console.log('PAGE ERROR:', e.message));

const out = await page.evaluate(async () => {
    const res = await fetch('/api/agents', {
        method: 'POST',
        headers: { ..._csrfHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: 'edge-vps',
            url: 'http://tmshot-agent:8090',
            config_path: '/app/config/dynamic.yml',
            static_config_path: '/app/config/traefik-static.yml',
        }),
    });
    const text = await res.text();
    let d = null;
    try { d = JSON.parse(text); } catch {}
    return { status: res.status, key: d?.agent?.api_key_raw || '', body: text.slice(0, 400) };
});

const key = out.key;
if (!key) {
    console.log('HTTP', out.status);
    console.log('BODY', out.body);
    throw new Error('manager did not mint an agent key');
}
fs.writeFileSync('/out/agent-key', key);
console.log('agent registered');
await browser.close();
