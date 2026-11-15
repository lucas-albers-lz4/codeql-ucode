import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let once=true; while(once && (once=false, true)) function readlink(x) { return 'while-decl'; }
probe('after', readlink("probe-link"));
