import { readfile } from 'fs';
function local(readfile) { printf('local=%s\n', readfile("fixtures/native.txt"));
 }
local(function(x) { return 'shadow'; });
