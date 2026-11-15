import { access } from 'fs';
function local(access) { printf('local=%s\n', access("fixtures/native.txt"));
 }
local(function(x) { return 'shadow'; });
