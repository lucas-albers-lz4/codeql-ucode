import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function local(popen) { return popen("probe-link"); }
probe('formal', local(function(x) { return 'shadow'; }));
