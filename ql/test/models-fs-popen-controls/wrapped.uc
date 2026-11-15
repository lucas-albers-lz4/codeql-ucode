import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('wrapped', (popen)("probe-link"));
