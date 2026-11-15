import { popen } from 'fs';
{ let popen = function(x) { return 'shadow'; }; printf('local=%s\n', popen('printf fs-native'));
}
