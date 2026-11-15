import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = (popen) => { return popen("probe-link"); };
probe('arrow', local(function(x) { return 'shadow'; }));
