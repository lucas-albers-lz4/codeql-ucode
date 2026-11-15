import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (let i=0; i<1; i++) function readlink(x) { if (x) return readlink(false); return 'inner'; }
probe('after', readlink("probe-link"));
