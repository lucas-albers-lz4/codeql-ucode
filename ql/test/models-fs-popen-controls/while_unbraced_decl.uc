import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let once=true; while(once && (once=false, true)) function popen(x) { return 'while-decl'; }
probe('after', popen("probe-link"));
