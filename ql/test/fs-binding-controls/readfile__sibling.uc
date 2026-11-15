import { readfile } from 'fs';
function unused(readfile) { return readfile; }
printf('native=%s\n', type(readfile("fixtures/native.txt")));
