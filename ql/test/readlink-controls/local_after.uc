import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ probe('before', readlink("probe-link")); let readlink = function(x) { return 'shadow'; }; probe('after', readlink("probe-link")); }
