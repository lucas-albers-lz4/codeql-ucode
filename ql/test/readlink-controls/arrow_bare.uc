import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = readlink => readlink("probe-link");
probe('arrow', local(function(x) { return 'shadow'; }));
