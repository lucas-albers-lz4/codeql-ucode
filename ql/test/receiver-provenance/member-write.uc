import { popen } from 'fs';
function member_write(other) {
  const fd = popen('printf harmless');
  fd.read = other;
  fd.read('all');
  fd.close();
}
