import { popen as popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('alias', popen("probe-link"));
