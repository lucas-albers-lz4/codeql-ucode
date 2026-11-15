import { open } from 'fs';
function local(open) { printf('local=%s\n', open("fixtures/native.txt"));
 }
local(function(x) { return 'shadow'; });
