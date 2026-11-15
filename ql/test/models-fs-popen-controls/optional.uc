import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('optional', popen?.("probe-link"));
