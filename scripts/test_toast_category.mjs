import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = readFileSync(join(root, 'static', 'js', 'core.js'), 'utf8');

const grab = (name, end) => name + src.split(name)[1].split(end)[0] + end;
const harness = `
${grab('const _TOAST_CATEGORY_BY_PANEL = ', '};')}
${grab('const _TOAST_CATEGORY_BY_TAB = ', '};')}
${'function _toastCategory()' + src.split('function _toastCategory()')[1].split('\n}\n')[0] + '\n}'}
return { pick(panels, tab) {
    _activeTab = tab;
    document.__panels = panels;
    return _toastCategory();
} };
`;
let _activeTab = 'services';
const document = {
    __panels: [],
    querySelectorAll() {
        return this.__panels.map(([id, visible]) =>
            ({ id: 'mpanel-' + id, offsetParent: visible ? {} : null }));
    },
};
const api = new Function('document', 'let _activeTab;' + harness)(document);

let fails = 0;
const check = (label, got, want) => {
    const ok = got === want;
    console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${label}  -> ${got}`);
    if (!ok) fails++;
};

check('no panel, plain tab',            api.pick([], 'services'), 'config');
check('certs tab',                      api.pick([], 'certs'), 'certs');
check('crowdsec tab',                   api.pick([], 'crowdsec'), 'crowdsec');
check('logs tab files under traefik',   api.pick([], 'logs'), 'traefik');
check('agents panel beats the tab',     api.pick([['agents', true]], 'certs'), 'agent');
check('backups panel',                  api.pick([['backups', true]], 'services'), 'backup');
check('auth panel',                     api.pick([['auth', true]], 'services'), 'security');
check('hidden panel is ignored',        api.pick([['agents', false]], 'certs'), 'certs');
check('unmapped panel falls through',   api.pick([['about', true]], 'certs'), 'certs');

if (fails) { console.error(`${fails} toast category check(s) failed`); process.exit(1); }
console.log('ok - 9 toast category checks');
