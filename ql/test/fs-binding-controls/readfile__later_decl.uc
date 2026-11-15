import { readfile } from 'fs';
printf('native=%s\n', type(readfile("fixtures/native.txt")));
let readfile = function(x) { return 'shadow'; };
printf('local=%s\n', readfile("fixtures/native.txt"));
