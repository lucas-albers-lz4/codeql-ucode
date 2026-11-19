import { popen } from 'fs';
function reassigned(other) {
  let fd = popen('printf harmless');
  fd = other;
  fd.read('all');
  fd.close();
}
