import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
readlink += 1; probe('augmented', readlink("probe-link"));
