import { popen } from 'fs';
function formal_shadow() {
  const fd = popen('printf harmless');
  function inner(fd) {
    fd.read('all');
    fd.close();
  }
  fd.read('all');
  fd.close();
}
