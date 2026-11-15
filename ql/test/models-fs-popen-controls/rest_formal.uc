import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function local(...popen) { return popen("probe-link"); }
try { local(function(x) { return 'shadow'; }); } catch(e) { print('rest=not-callable\n'); }
