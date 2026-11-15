import { readfile } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (let key, readfile in { a: function(x) { return 'shadow'; } }) probe('loop', readfile("probe-link"));
probe('after', readfile("probe-link"));
