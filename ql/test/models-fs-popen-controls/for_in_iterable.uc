import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
try { for (let popen in [popen("probe-link")]) print('unreachable'); } catch(e) { print('iterable=shadowed-before-object\n'); }
probe('after', popen("probe-link"));
