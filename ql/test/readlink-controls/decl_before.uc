import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ function readlink(x) { return 'decl'; } probe('decl', readlink("probe-link")); }
