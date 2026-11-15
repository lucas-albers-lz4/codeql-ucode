import { readlink } from 'fs';
function probe(label, value) { printf('%s=%s\n', label, value); }
function outer() { return function() { return readlink("probe-link"); }; }
probe('nested', outer()());
