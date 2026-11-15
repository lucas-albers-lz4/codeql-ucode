import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ let popen = popen("probe-link"); }
