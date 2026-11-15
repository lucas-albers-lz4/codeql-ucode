import { basename } from 'fs';
function outer() { printf('native=%s\n', type(basename('/a/fs-native')));
 }
outer();
