import { readlink, readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
probe('duplicate', readlink("probe-link"));
