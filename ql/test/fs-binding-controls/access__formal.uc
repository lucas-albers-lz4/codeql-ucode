import { access } from 'fs';
function local(access) { printf('local=%s\n', access("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
 }
local(function(x) { return 'shadow'; });
