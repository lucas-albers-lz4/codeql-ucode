import { popen } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function outer() { return function() { return popen("probe-link"); }; }
probe('nested', outer()());
