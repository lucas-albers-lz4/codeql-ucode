import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
readlink = function(x) { return 'shadow'; };
probe('assigned', readlink("probe-link"));
