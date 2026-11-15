function probe(label, value) { printf('%s=%s\n', label, value); }
function local() { import { popen } from 'fs'; return popen("probe-link"); }
probe('nested', local());
