import { readfile } from 'fs';
function local(readfile) { printf('local=%s\n', readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
 }
local(function(x) { return 'shadow'; });
