import { readlink } from 'fs';
function local(readlink) { printf('local=%s\n', readlink("fixtures/native-link"));
 }
local(function(x) { return 'shadow'; });
