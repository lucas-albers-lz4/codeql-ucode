import { readfile } from 'fs';
function f(...readfile) { return readfile("fixtures/native.txt"); }
f(function(x) { return 'shadow'; });
