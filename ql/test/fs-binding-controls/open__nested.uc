import { open } from 'fs';
function outer() { printf('native=%s\n', type(open("fixtures/native.txt")));
 }
outer();
