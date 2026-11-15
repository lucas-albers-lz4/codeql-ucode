import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('wrapped', (0, popen)("probe-link"));
