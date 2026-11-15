import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ const readlink = function(x) { return 'shadow'; }; probe('const', readlink("probe-link")); }
