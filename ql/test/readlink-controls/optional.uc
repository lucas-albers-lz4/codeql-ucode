import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('optional', readlink?.("probe-link"));
