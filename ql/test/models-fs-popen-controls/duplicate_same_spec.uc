import { popen, popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('duplicate', popen("probe-link"));
