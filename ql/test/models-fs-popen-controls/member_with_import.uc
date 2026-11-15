import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let obj={ popen: function(x) { return 'shadow'; } }; probe('member', obj.popen("probe-link"));
