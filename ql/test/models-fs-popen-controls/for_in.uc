import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
for (let key, popen in { a: function(x) { return 'shadow'; } }) probe('loop', popen("probe-link"));
probe('after', popen("probe-link"));
