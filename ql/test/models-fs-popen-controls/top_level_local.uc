import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let popen=function(x) { return 'shadow'; }; probe('local', popen("probe-link"));
