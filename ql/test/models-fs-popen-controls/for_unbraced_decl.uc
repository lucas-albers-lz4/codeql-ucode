import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (let i=0; i<1; i++) function popen(x) { if (x) return popen(false); return 'inner'; }
probe('after', popen("probe-link"));
