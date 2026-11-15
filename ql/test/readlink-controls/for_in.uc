import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (let key, readlink in { a: function(x) { return 'shadow'; } }) probe('loop', readlink("probe-link"));
probe('after', readlink("probe-link"));
