import { popen } from 'fs';
{ let popen = function(x) { return 'shadow'; }; printf('local=%s\n', popen('printf fs-native'));
}
printf('native=%s\n', type(popen('printf fs-native')));
