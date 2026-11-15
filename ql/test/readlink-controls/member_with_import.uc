import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let obj={ readlink: function(x) { return 'shadow'; } }; probe('member', obj.readlink("probe-link"));
