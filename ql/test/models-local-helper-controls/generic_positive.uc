import { popen } from 'fs';
function localHelper(pkg) { popen('true'); }
localHelper('value');
return {};
