import { readfile } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function local(readfile) { return readfile('unused'); }
probe('existing', local(function(x) { return 'shadow'; }));
