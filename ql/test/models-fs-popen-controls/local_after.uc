import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ probe('before', popen("probe-link")); let popen = function(x) { return 'shadow'; }; probe('after', popen("probe-link")); }
