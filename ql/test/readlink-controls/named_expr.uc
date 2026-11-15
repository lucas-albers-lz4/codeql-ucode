import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let local = function readlink(x) { if (x) return readlink(false); return 'self'; };
probe('named', local(true));
