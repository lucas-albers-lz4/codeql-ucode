import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = function(readlink) { return readlink("probe-link"); };
probe('formal', local(function(x) { return 'shadow'; }));
