import { popen } from 'fs';
function positive() {
  const fd = popen('printf harmless');
  if (fd) {
    fd.read('all');
    fd.close();
  }
}
