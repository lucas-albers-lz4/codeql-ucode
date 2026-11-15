import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
popen = function(x) { return 'shadow'; };
probe('assigned', popen("probe-link"));
