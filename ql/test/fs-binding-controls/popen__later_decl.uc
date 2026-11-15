import { popen } from 'fs';
printf('native=%s\n', type(popen('printf fs-native')));
let popen = function(x) { return 'shadow'; };
printf('local=%s\n', popen('printf fs-native'));
