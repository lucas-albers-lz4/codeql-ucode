import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ const popen = function(x) { return 'shadow'; }; probe('const', popen("probe-link")); }
