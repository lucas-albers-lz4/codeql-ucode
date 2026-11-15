import { readlink as readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('alias', readlink("probe-link"));
