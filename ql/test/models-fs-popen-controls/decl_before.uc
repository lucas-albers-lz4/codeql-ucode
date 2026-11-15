import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ function popen(x) { return 'decl'; } probe('decl', popen("probe-link")); }
