import { popen } from 'fs';
function escaped_receiver() {
  const fd = popen('printf harmless');
  const alias = fd;
  fd.read('all');
  fd.close();
}
