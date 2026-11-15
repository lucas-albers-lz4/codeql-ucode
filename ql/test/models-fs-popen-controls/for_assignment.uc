import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (popen in { a: true }) popen("probe-link");
