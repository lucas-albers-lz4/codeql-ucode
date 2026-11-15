import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ probe('before', popen("probe-link")); function popen(x) { return 'decl'; } probe('after', popen("probe-link")); }
