import { popen } from 'f\x2fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('escaped', popen("probe-link"));
