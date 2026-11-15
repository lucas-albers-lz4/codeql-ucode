import { readfile } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
{ let readfile = function(x) { return 'shadow'; }; probe('existing', readfile('unused')); }
