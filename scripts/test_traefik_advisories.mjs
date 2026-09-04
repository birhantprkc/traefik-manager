import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = readFileSync(join(root, 'static', 'js', 'settings.js'), 'utf8');

const listSrc = src.split('const TRAEFIK_ADVISORIES = ')[1]?.split('\n];')[0];
if (!listSrc) {
    console.error('could not find TRAEFIK_ADVISORIES in static/js/settings.js');
    process.exit(1);
}
const ADVISORIES = eval(listSrc + '\n]');

const parts = v => {
    const m = String(v || '').match(/(\d+)\.(\d+)\.(\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
};
const shown = v => {
    const hit = ADVISORIES.find(a => a.affected(parts(v)));
    return hit ? hit.id : null;
};

const GHSA = 'GHSA-rf44-j88r-hh8c';
const CVE  = 'CVE-2026-39858';

const cases = [
    ['2.11.55', GHSA, 'last affected 2.x'],
    ['2.11.56', null, 'patched 2.x'],
    ['3.7.11',  GHSA, 'last affected 3.x'],
    ['3.7.12',  null, 'patched 3.x'],
    ['3.8.0',   null, 'later minor is clean'],
    ['4.0.0',   null, 'later major is clean'],
    ['3.6.14',  GHSA, 'past the older CVE, still hit by this one'],
    ['3.5.0',   CVE,  'High outranks Moderate'],
    ['3.6.13',  CVE,  'High outranks Moderate'],
];

let failed = 0;
for (const [version, want, why] of cases) {
    const got = shown(version);
    if (got !== want) {
        console.error(`FAIL v${version} (${why}): expected ${want || 'no advisory'}, got ${got || 'no advisory'}`);
        failed++;
    }
}

const ghsa = ADVISORIES.find(a => a.id === GHSA);
if (!ghsa) { console.error(`FAIL ${GHSA} is missing`); failed++; }
else {
    if (!ghsa.forwardAuthRelated) { console.error('FAIL the advisory must be flagged forwardAuthRelated'); failed++; }
    if (!/3\.7\.12/.test(ghsa.fixedIn || '')) { console.error('FAIL fixedIn must name v3.7.12'); failed++; }
    if (!/^https:\/\/github\.com\/traefik\/traefik\/security\/advisories\//.test(ghsa.url || '')) {
        console.error('FAIL advisory url must point at the GitHub advisory'); failed++;
    }
}

for (const a of ADVISORIES) {
    if (!/v\d+\.\d+\.\d+/.test(a.fixedIn || '')) {
        console.error(`FAIL ${a.id} has no fixedIn, so the UI cannot say which release to move to`);
        failed++;
    }
}

if (failed) { console.error(`${failed} advisory check(s) failed`); process.exit(1); }
console.log(`ok - ${cases.length} version boundaries and 4 field checks`);
