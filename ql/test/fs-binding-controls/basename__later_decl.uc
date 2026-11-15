import { basename } from 'fs';
printf('native=%s\n', type(basename('/a/fs-native')));
let basename = function(x) { return 'shadow'; };
printf('local=%s\n', basename('/a/fs-native'));
