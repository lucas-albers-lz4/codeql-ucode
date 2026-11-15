import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
let factory=function(){ return readlink; }; probe('nested', factory()("probe-link"));
