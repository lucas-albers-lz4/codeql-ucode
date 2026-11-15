import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ probe('before', readlink("probe-link")); function readlink(x) { return 'decl'; } probe('after', readlink("probe-link")); }
