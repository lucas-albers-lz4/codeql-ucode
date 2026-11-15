import { readlink } from 'fs';
function local(readlink) { printf('local=%s\n', readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link"));
 }
local(function(x) { return 'shadow'; });
