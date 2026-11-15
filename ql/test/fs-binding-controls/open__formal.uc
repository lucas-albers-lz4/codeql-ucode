import { open } from 'fs';
function local(open) { printf('local=%s\n', open("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
 }
local(function(x) { return 'shadow'; });
