import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function local(readlink) { return readlink("probe-link"); }
probe('formal', local(function(x) { return 'shadow'; }));
