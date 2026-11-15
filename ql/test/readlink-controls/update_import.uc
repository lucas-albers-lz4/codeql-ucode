import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
readlink++; probe('updated', readlink("probe-link"));
