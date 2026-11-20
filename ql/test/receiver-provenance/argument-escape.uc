import { popen } from 'fs';
function argument_escape() {
  const fd = popen('printf harmless');
  consume(fd);
  fd.read('all');
  fd.close();
}
