import { basename } from 'fs';
function local(basename) { printf('local=%s\n', basename('/a/fs-native'));
 }
local(function(x) { return 'shadow'; });
