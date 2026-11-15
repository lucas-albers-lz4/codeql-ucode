import { basename } from 'fs';
function unused(basename) { return basename; }
printf('native=%s\n', type(basename('/a/fs-native')));
