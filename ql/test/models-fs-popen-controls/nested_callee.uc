import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let factory=function(){ return popen; }; probe('nested', factory()("probe-link"));
