import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = function popen(x) { if (x) return popen(false); return 'self'; };
probe('named', local(true));
