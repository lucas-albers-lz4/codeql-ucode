import { popen } from 'fs\x2fother';
function escaped_import() {
  const fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}
