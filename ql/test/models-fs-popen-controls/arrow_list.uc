import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = (x, popen) => popen("probe-link");
probe('arrow', local(null, function(x) { return 'shadow'; }));
