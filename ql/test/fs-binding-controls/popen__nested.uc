import { popen } from 'fs';
function outer() { printf('native=%s\n', type(popen('printf fs-native')));
 }
outer();
