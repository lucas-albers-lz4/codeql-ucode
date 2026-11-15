import { open } from 'fs';
function unused(open) { return open; }
printf('native=%s\n', type(open("fixtures/native.txt")));
