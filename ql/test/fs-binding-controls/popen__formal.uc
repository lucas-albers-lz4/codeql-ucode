import { popen } from 'fs';
function local(popen) { printf('local=%s\n', popen('printf fs-native'));
 }
local(function(x) { return 'shadow'; });
