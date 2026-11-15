import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (readlink in { a: true }) readlink("probe-link");
