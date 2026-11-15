import { readlink } from 'fs';
function unused(readlink) { return readlink; }
printf('native=%s\n', type(readlink("fixtures/native-link")));
