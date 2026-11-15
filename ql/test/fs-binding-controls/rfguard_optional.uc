import { readfile } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('optional', readfile?.("probe-link"));
