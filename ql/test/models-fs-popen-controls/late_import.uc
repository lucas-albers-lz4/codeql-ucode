let prior=1;
function probe(label, value) { printf('%s=%s\n', label, value); }
import { popen } from 'fs';
probe('late', popen("probe-link"));
