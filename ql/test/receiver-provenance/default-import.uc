import popen from 'fs';
function default_import() {
  const fd = popen('printf harmless');
  fd.read('all');
  fd.close();
}
