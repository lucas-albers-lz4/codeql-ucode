import { access } from 'fs';
function outer() { printf('native=%s\n', type(access("fixtures/native.txt")));
 }
outer();
