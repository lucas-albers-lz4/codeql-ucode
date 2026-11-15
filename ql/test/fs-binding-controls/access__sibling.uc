import { access } from 'fs';
function unused(access) { return access; }
printf('native=%s\n', type(access("fixtures/native.txt")));
