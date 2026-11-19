import { popen } from 'fs';
function unsupported_callee() {
  const fd = popen('printf harmless');
  fd?.read('all');
}
