import { readlink } from 'fs';
function outer() { printf('native=%s\n', type(readlink("fixtures/native-link")));
 }
outer();
