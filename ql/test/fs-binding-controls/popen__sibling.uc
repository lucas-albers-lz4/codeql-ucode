import { popen } from 'fs';
function unused(popen) { return popen; }
printf('native=%s\n', type(popen('printf fs-native')));
