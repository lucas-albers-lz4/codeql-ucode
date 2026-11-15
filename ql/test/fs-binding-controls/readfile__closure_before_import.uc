function f() { printf('native=%s\n', type(readfile("fixtures/native.txt")));
 }
import { readfile } from 'fs';
f();
