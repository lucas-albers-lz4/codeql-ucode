import { readfile } from 'fs';
function outer() { printf('native=%s\n', type(readfile("fixtures/native.txt")));
 }
outer();
